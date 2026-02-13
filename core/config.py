import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "THY Kurumsal AI")

    # Model Ayarları
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-oss:120b-cloud")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Admin
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    # Varsayılan Sistem Promptu
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        "Sen Türk Hava Yolları (THY) kurumsal asistanısın."
    )

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PDF_SOURCE_DIR: str = os.path.join(BASE_DIR, "data")
    VECTOR_DB_PATH: str = os.path.join(BASE_DIR, "data", "chroma_db")

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TEMPERATURE: float = 0.1


settings = Settings()
