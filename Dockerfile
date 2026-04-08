FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (install first for Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY platform/dist/ ./platform/dist/
COPY scripts/create_demo_db.py ./scripts/
COPY demo_docs/ ./demo_docs/

# Runtime directories
RUN mkdir -p data uploads logs chroma_data models/embedding \
    data/conversations data/builds data/settings data/confluence

# Create demo SQLite database
RUN python scripts/create_demo_db.py

# Download embedding model at build time (cached in Docker layer)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
model = SentenceTransformer('BAAI/bge-m3'); \
model.save('./models/embedding'); \
print('Embedding model saved')"

# Pre-index demo documents for RAG
RUN python -c "\
import os; os.environ['LLM_API_BASE']='http://localhost:11434/v1'; \
os.environ['LLM_API_KEY']='skip'; os.environ['LLM_MODEL']='skip'; \
os.environ['CHROMA_PORT']='0'; os.environ['DB_TYPE']='sqlite'; \
os.environ['DB_NAME']='./data/demo.db'; \
from app.core.vector_store import get_vector_store; \
from app.core.document_loader import DocumentLoader; \
import glob; \
vs = get_vector_store(); loader = DocumentLoader(); \
for f in sorted(glob.glob('demo_docs/*.md')): \
    name = os.path.basename(f); \
    chunks = loader.load_and_chunk(f, name); \
    vs.add_documents('demo', chunks, doc_id=name, filename=name); \
    print(f'Indexed {name}: {len(chunks)} chunks'); \
print('Demo docs indexed')"

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
