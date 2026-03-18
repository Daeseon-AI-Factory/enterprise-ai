from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MODE: str = "local"  # "local" or "airgap"

    # LLM — same openai client, different base_url
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = "sk-xxx"
    LLM_MODEL: str = "gpt-4o-mini"

    # Embedding
    EMBEDDING_MODEL_PATH: str = "./models/embedding"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100

    # Database (Text-to-SQL)
    DB_TYPE: str = "oracle"
    DB_HOST: str = "localhost"
    DB_PORT: int = 1521
    DB_NAME: str = "ORCL"
    DB_USER: str = ""
    DB_PASSWORD: str = ""

    # Function Calling
    FUNCTION_CALLING_MODE: str = "auto"  # "native", "prompt", "auto"

    # Auth
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "changeme123!"
    AUTH_SECRET_KEY: str = "enterprise-llm-secret-key-change-this-in-production"
    AUTH_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Confluence
    CONFLUENCE_VERIFY_SSL: bool = True  # False for self-signed certs on internal servers

    # Webhook
    WEBHOOK_SECRET: str = ""
    N8N_BASE_URL: str = "http://n8n:5678"

    # Multi-Modal
    WHISPER_MODEL_PATH: str = "./models/whisper"
    VISION_MODEL: str = ""  # empty = disabled
    OCR_ENGINE: str = "paddleocr"  # "paddleocr" or "tesseract"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
