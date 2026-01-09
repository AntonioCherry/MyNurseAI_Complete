import os
from dotenv import load_dotenv

# Carica .env (serve in locale, innocuo in Docker)
load_dotenv()

# Database
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# Ambiente
ENV = os.getenv("ENV", "development")

if not POSTGRES_URL:
    raise RuntimeError("POSTGRES_URL non è impostata")

if not OLLAMA_BASE_URL:
    raise RuntimeError("OLLAMA_BASE_URL non è impostata")
