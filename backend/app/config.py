from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PORT: int = 4005
    CORS_ORIGIN: str = "http://localhost:5173"
    INBOX_DIR: str = "../inbox"
    DATA_DIR: str = "../data"
    DB_PATH: str = "../data/app.db"
    MAX_UPLOAD_MB: int = 40
    AUTO_APPROVE_DIGITAL: bool = False
    GEMINI_MAX_PAGES: int = 1
    GEMINI_LONG_EDGE_PX: int = 768
    MAX_HEAVY_WORKERS: int = 2

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_TIMEOUT_SEC: float = 45
    GEMINI_ENABLED: bool = False

    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3.5:0.8b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    RAG_CHUNK: int = 500
    RAG_OVERLAP: int = 80
    RAG_TOP_K: int = 2

    N8N_WEBHOOK_URL: str = ""
    N8N_WEBHOOK_SECRET: str = ""
    N8N_WEBHOOK_HEADER_NAME: str = "X-CuadreIQ-Secret"
    N8N_TIMEOUT_SEC: float = 15
    N8N_DRY_RUN: bool = True

    def _abs(self, p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = (Path(__file__).resolve().parent.parent / path).resolve()
        return path

    @property
    def data_path(self) -> Path:
        p = self._abs(self.DATA_DIR)
        p.mkdir(parents=True, exist_ok=True)
        (p / "originals").mkdir(exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        p = self._abs(self.DB_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def inbox_path(self) -> Path:
        p = self._abs(self.INBOX_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def originals_path(self) -> Path:
        p = self.data_path / "originals"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
