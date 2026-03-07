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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
