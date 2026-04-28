import os


def _bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# LLM settings
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Embedding settings
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "shibing624/text2vec-base-chinese")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FAISS_INDEX_DIR = os.path.join(BASE_DIR, "data", "faiss_index")
DOCS_DIR = os.path.join(BASE_DIR, "data", "docs")

# Retrieval
MOCK_RETRIEVAL = _bool_env("MOCK_RETRIEVAL", "true")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("TOP_K", "5"))

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "rag_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rag_pass")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "rag_customer_service")
MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")
MYSQL_URL = os.getenv(
    "MYSQL_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset={MYSQL_CHARSET}",
)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "rag_cs:")
REDIS_URL = os.getenv(
    "REDIS_URL",
    (
        f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        if REDIS_PASSWORD
        else f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    ),
)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
