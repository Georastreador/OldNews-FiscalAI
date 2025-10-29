"""
FiscalAI MVP - Logger Seguro e Estruturado
Sistema de logging seguro para produção e desenvolvimento
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
import hashlib
import re
from dataclasses import dataclass, asdict
from enum import Enum

class LogLevel(Enum):
    """Níveis de log"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """Categorias de log"""
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"
    BUSINESS = "BUSINESS"
    API = "API"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    VALIDATION = "VALIDATION"

@dataclass
class LogEntry:
    """Estrutura de entrada de log"""
    timestamp: str
    level: str
    category: str
    message: str
    module: str
    function: str
    line_number: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None
    sanitized: bool = False

class SecureLogger:
    """
    Logger seguro e estruturado
    
    Funcionalidades:
    - Sanitização de dados sensíveis
    - Logs estruturados (JSON)
    - Rotação de arquivos
    - Diferentes níveis de verbosidade
    - Categorização de logs
    - Métricas de performance
    - Segurança em produção
    """
    
    def __init__(self, 
                 name: str = "fiscalai",
                 log_dir: str = "logs",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 production_mode: bool = False):
        """
        Inicializa o logger seguro
        
        Args:
            name: Nome do logger
            log_dir: Diretório para logs
            max_file_size: Tamanho máximo do arquivo de log
            backup_count: Número de backups a manter
            production_mode: Modo de produção (logs mais restritivos)
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.production_mode = production_mode
        
        # Configurar logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Remover handlers existentes
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Configurar handlers
        self._setup_handlers()
        
        # Padrões de dados sensíveis para sanitização
        self.sensitive_patterns = [
            r'(?i)(password|senha|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(api[_-]?key|chave[_-]?api)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(token|access[_-]?token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(secret|secreto)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(cnpj|cpf)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(email|e-mail)\s*[:=]\s*["\']?([^"\'\s@]+@[^"\'\s@]+)["\']?',
            r'(?i)(phone|telefone|celular)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
            r'(?i)(credit[_-]?card|cartao[_-]?credito)\s*[:=]\s*["\']?([^"\'\s]+)["\']?',
        ]
        
        # Campos que sempre devem ser sanitizados
        self.sensitive_fields = [
            'password', 'senha', 'pwd', 'api_key', 'chave_api', 'token',
            'access_token', 'secret', 'secreto', 'cnpj', 'cpf', 'email',
            'telefone', 'phone', 'credit_card', 'cartao_credito'
        ]
    
    def _setup_handlers(self):
        """Configura handlers de log"""
        # Handler para arquivo principal
        main_log_file = self.log_dir / f"{self.name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(self._create_formatter())
        self.logger.addHandler(main_handler)
        
        # Handler para erros
        error_log_file = self.log_dir / f"{self.name}_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._create_formatter())
        self.logger.addHandler(error_handler)
        
        # Handler para segurança
        security_log_file = self.log_dir / f"{self.name}_security.log"
        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        security_handler.setLevel(logging.INFO)
        security_handler.setFormatter(self._create_formatter())
        self.logger.addHandler(security_handler)
        
        # Handler para console (apenas em desenvolvimento)
        if not self.production_mode:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(self._create_console_formatter())
            self.logger.addHandler(console_handler)
    
    def _create_formatter(self) -> logging.Formatter:
        """Cria formatter para arquivos"""
        return logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _create_console_formatter(self) -> logging.Formatter:
        """Cria formatter para console"""
        return logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def _sanitize_data(self, data: Any) -> Any:
        """
        Sanitiza dados sensíveis
        
        Args:
            data: Dados para sanitizar
            
        Returns:
            Dados sanitizados
        """
        if isinstance(data, str):
            # Sanitizar padrões de dados sensíveis
            for pattern in self.sensitive_patterns:
                data = re.sub(pattern, r'\1: [REDACTED]', data, flags=re.IGNORECASE)
            return data
        
        elif isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        
        else:
            return data
    
    def _create_log_entry(self, 
                         level: LogLevel,
                         category: LogCategory,
                         message: str,
                         extra_data: Optional[Dict[str, Any]] = None,
                         user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         request_id: Optional[str] = None,
                         duration_ms: Optional[float] = None) -> LogEntry:
        """
        Cria entrada de log estruturada
        
        Args:
            level: Nível do log
            category: Categoria do log
            message: Mensagem do log
            extra_data: Dados extras
            user_id: ID do usuário
            session_id: ID da sessão
            request_id: ID da requisição
            duration_ms: Duração em milissegundos
            
        Returns:
            Entrada de log estruturada
        """
        # Obter informações do frame de chamada
        frame = sys._getframe(2)
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        
        # Sanitizar dados extras
        sanitized_extra = None
        if extra_data:
            sanitized_extra = self._sanitize_data(extra_data)
        
        return LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            category=category.value,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            duration_ms=duration_ms,
            memory_usage_mb=self._get_memory_usage(),
            cpu_usage_percent=self._get_cpu_usage(),
            extra_data=sanitized_extra,
            sanitized=True
        )
    
    def _get_memory_usage(self) -> Optional[float]:
        """Obtém uso de memória em MB"""
        try:
            import psutil
            process = psutil.Process()
            return round(process.memory_info().rss / 1024 / 1024, 2)
        except ImportError:
            return None
    
    def _get_cpu_usage(self) -> Optional[float]:
        """Obtém uso de CPU em percentual"""
        try:
            import psutil
            return round(psutil.cpu_percent(), 2)
        except ImportError:
            return None
    
    def _log_structured(self, log_entry: LogEntry):
        """Registra log estruturado"""
        # Converter para JSON
        log_data = asdict(log_entry)
        log_json = json.dumps(log_data, ensure_ascii=False, indent=None)
        
        # Log baseado no nível
        if log_entry.level == "DEBUG":
            self.logger.debug(log_json)
        elif log_entry.level == "INFO":
            self.logger.info(log_json)
        elif log_entry.level == "WARNING":
            self.logger.warning(log_json)
        elif log_entry.level == "ERROR":
            self.logger.error(log_json)
        elif log_entry.level == "CRITICAL":
            self.logger.critical(log_json)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        if not self.production_mode:  # Debug apenas em desenvolvimento
            log_entry = self._create_log_entry(LogLevel.DEBUG, LogCategory.SYSTEM, message, **kwargs)
            self._log_structured(log_entry)
    
    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log de informação"""
        log_entry = self._create_log_entry(LogLevel.INFO, category, message, **kwargs)
        self._log_structured(log_entry)
    
    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log de aviso"""
        log_entry = self._create_log_entry(LogLevel.WARNING, category, message, **kwargs)
        self._log_structured(log_entry)
    
    def error(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log de erro"""
        log_entry = self._create_log_entry(LogLevel.ERROR, category, message, **kwargs)
        self._log_structured(log_entry)
    
    def critical(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """Log crítico"""
        log_entry = self._create_log_entry(LogLevel.CRITICAL, category, message, **kwargs)
        self._log_structured(log_entry)
    
    def security(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de segurança"""
        log_entry = self._create_log_entry(level, LogCategory.SECURITY, message, **kwargs)
        self._log_structured(log_entry)
    
    def performance(self, message: str, duration_ms: float, **kwargs):
        """Log de performance"""
        log_entry = self._create_log_entry(
            LogLevel.INFO, 
            LogCategory.PERFORMANCE, 
            message, 
            duration_ms=duration_ms,
            **kwargs
        )
        self._log_structured(log_entry)
    
    def business(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de negócio"""
        log_entry = self._create_log_entry(level, LogCategory.BUSINESS, message, **kwargs)
        self._log_structured(log_entry)
    
    def api(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de API"""
        log_entry = self._create_log_entry(level, LogCategory.API, message, **kwargs)
        self._log_structured(log_entry)
    
    def validation(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de validação"""
        log_entry = self._create_log_entry(level, LogCategory.VALIDATION, message, **kwargs)
        self._log_structured(log_entry)
    
    def cache(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de cache"""
        log_entry = self._create_log_entry(level, LogCategory.CACHE, message, **kwargs)
        self._log_structured(log_entry)
    
    def database(self, message: str, level: LogLevel = LogLevel.INFO, **kwargs):
        """Log de banco de dados"""
        log_entry = self._create_log_entry(level, LogCategory.DATABASE, message, **kwargs)
        self._log_structured(log_entry)


class PerformanceLogger:
    """
    Logger específico para métricas de performance
    
    Funcionalidades:
    - Medição de tempo de execução
    - Métricas de memória
    - Métricas de CPU
    - Agregação de estatísticas
    """
    
    def __init__(self, secure_logger: SecureLogger):
        """
        Inicializa o logger de performance
        
        Args:
            secure_logger: Instância do logger seguro
        """
        self.secure_logger = secure_logger
        self.metrics = {}
    
    def start_timer(self, operation: str) -> str:
        """
        Inicia timer para operação
        
        Args:
            operation: Nome da operação
            
        Returns:
            ID do timer
        """
        timer_id = hashlib.md5(f"{operation}_{datetime.now()}".encode()).hexdigest()[:8]
        self.metrics[timer_id] = {
            'operation': operation,
            'start_time': datetime.now(),
            'start_memory': self.secure_logger._get_memory_usage()
        }
        return timer_id
    
    def end_timer(self, timer_id: str, success: bool = True, extra_data: Optional[Dict] = None):
        """
        Finaliza timer e registra métricas
        
        Args:
            timer_id: ID do timer
            success: Se a operação foi bem-sucedida
            extra_data: Dados extras
        """
        if timer_id not in self.metrics:
            return
        
        metric = self.metrics[timer_id]
        end_time = datetime.now()
        duration = (end_time - metric['start_time']).total_seconds() * 1000  # ms
        
        end_memory = self.secure_logger._get_memory_usage()
        memory_delta = None
        if end_memory and metric['start_memory']:
            memory_delta = end_memory - metric['start_memory']
        
        # Log de performance
        message = f"Operação '{metric['operation']}' {'concluída' if success else 'falhou'}"
        self.secure_logger.performance(
            message,
            duration_ms=duration,
            extra_data={
                'operation': metric['operation'],
                'success': success,
                'memory_delta_mb': memory_delta,
                **(extra_data or {})
            }
        )
        
        # Remover métrica
        del self.metrics[timer_id]
    
    def log_operation(self, operation: str, duration_ms: float, success: bool = True, **kwargs):
        """
        Log direto de operação
        
        Args:
            operation: Nome da operação
            duration_ms: Duração em milissegundos
            success: Se foi bem-sucedida
            **kwargs: Dados extras
        """
        message = f"Operação '{operation}' {'concluída' if success else 'falhou'}"
        self.secure_logger.performance(
            message,
            duration_ms=duration_ms,
            extra_data={
                'operation': operation,
                'success': success,
                **kwargs
            }
        )


# Instâncias globais
_secure_logger_instance: Optional[SecureLogger] = None
_performance_logger_instance: Optional[PerformanceLogger] = None

def get_secure_logger() -> SecureLogger:
    """Retorna instância global do logger seguro"""
    global _secure_logger_instance
    if _secure_logger_instance is None:
        production_mode = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
        _secure_logger_instance = SecureLogger(production_mode=production_mode)
    return _secure_logger_instance

def get_performance_logger() -> PerformanceLogger:
    """Retorna instância global do logger de performance"""
    global _performance_logger_instance
    if _performance_logger_instance is None:
        _performance_logger_instance = PerformanceLogger(get_secure_logger())
    return _performance_logger_instance

# Funções de conveniência
def log_debug(message: str, **kwargs):
    """Função de conveniência para log de debug"""
    get_secure_logger().debug(message, **kwargs)

def log_info(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
    """Função de conveniência para log de informação"""
    get_secure_logger().info(message, category, **kwargs)

def log_warning(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
    """Função de conveniência para log de aviso"""
    get_secure_logger().warning(message, category, **kwargs)

def log_error(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
    """Função de conveniência para log de erro"""
    get_secure_logger().error(message, category, **kwargs)

def log_security(message: str, level: LogLevel = LogLevel.INFO, **kwargs):
    """Função de conveniência para log de segurança"""
    get_secure_logger().security(message, level, **kwargs)

def log_performance(operation: str, duration_ms: float, success: bool = True, **kwargs):
    """Função de conveniência para log de performance"""
    get_performance_logger().log_operation(operation, duration_ms, success, **kwargs)
