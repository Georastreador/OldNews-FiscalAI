"""
Configurações principais da aplicação FiscalAI
"""
import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
UI_DIR = BASE_DIR / "ui"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CACHE_DIR = BASE_DIR / "cache"

# Configurações de ambiente
ENVIRONMENT = os.getenv("FISCALAI_ENV", "development")
DEBUG = ENVIRONMENT == "development"

# Configurações de API
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Configurações de UI
UI_HOST = os.getenv("UI_HOST", "localhost")
UI_PORT = int(os.getenv("UI_PORT", "8501"))

# Configurações de cache
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hora
MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", "1000"))

# Configurações de segurança
SECURITY_LEVEL = os.getenv("SECURITY_LEVEL", "medium")
AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", "true").lower() == "true"

# Configurações de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configurações de performance
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "300"))

# Configurações de dados
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
SUPPORTED_FORMATS = [".xml", ".csv", ".json"]

# Configurações de modelos
MODEL_CACHE_DIR = BASE_DIR / "model_cache"
MODEL_TIMEOUT = int(os.getenv("MODEL_TIMEOUT", "60"))

# Configurações de validação
VALIDATION_STRICT = os.getenv("VALIDATION_STRICT", "false").lower() == "true"
SCHEMA_VALIDATION = os.getenv("SCHEMA_VALIDATION", "true").lower() == "true"

# Configurações de monitoramento
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
PERFORMANCE_MONITORING = os.getenv("PERFORMANCE_MONITORING", "true").lower() == "true"
