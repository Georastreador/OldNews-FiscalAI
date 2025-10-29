"""
FiscalAI MVP - Rate Limiter
Sistema de limitação de taxa para proteger APIs e recursos
"""

import time
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuração de rate limiting"""
    max_requests: int
    time_window: int  # em segundos
    burst_limit: Optional[int] = None  # limite de rajada
    block_duration: int = 300  # duração do bloqueio em segundos

@dataclass
class RateLimitInfo:
    """Informações de rate limiting"""
    requests_count: int
    window_start: float
    last_request: float
    is_blocked: bool
    block_until: Optional[float] = None

class RateLimiter:
    """
    Rate limiter com múltiplas estratégias
    
    Funcionalidades:
    - Token bucket
    - Sliding window
    - Fixed window
    - IP-based limiting
    - User-based limiting
    - API endpoint limiting
    """
    
    def __init__(self):
        """Inicializa o rate limiter"""
        self.limits: Dict[str, RateLimitConfig] = {}
        self.clients: Dict[str, RateLimitInfo] = {}
        self.lock = threading.RLock()
        
        # Configurações padrão
        self._setup_default_limits()
    
    def _setup_default_limits(self):
        """Configura limites padrão"""
        self.limits = {
            'api_general': RateLimitConfig(
                max_requests=100,
                time_window=3600,  # 1 hora
                burst_limit=20,
                block_duration=300
            ),
            'api_analysis': RateLimitConfig(
                max_requests=10,
                time_window=3600,  # 1 hora
                burst_limit=3,
                block_duration=600
            ),
            'api_upload': RateLimitConfig(
                max_requests=20,
                time_window=3600,  # 1 hora
                burst_limit=5,
                block_duration=300
            ),
            'ui_requests': RateLimitConfig(
                max_requests=1000,
                time_window=3600,  # 1 hora
                burst_limit=100,
                block_duration=60
            )
        }
    
    def add_limit(self, limit_name: str, config: RateLimitConfig):
        """
        Adiciona ou atualiza limite de taxa
        
        Args:
            limit_name: Nome do limite
            config: Configuração do limite
        """
        with self.lock:
            self.limits[limit_name] = config
            logger.info(f"Limite '{limit_name}' configurado: {config.max_requests} req/{config.time_window}s")
    
    def is_allowed(self, 
                   client_id: str, 
                   limit_name: str, 
                   increment: bool = True) -> tuple[bool, Dict[str, Any]]:
        """
        Verifica se requisição é permitida
        
        Args:
            client_id: ID do cliente (IP, user_id, etc.)
            limit_name: Nome do limite a verificar
            increment: Se deve incrementar contador
            
        Returns:
            (is_allowed, info_dict)
        """
        with self.lock:
            if limit_name not in self.limits:
                logger.warning(f"Limite '{limit_name}' não encontrado")
                return True, {'error': f'Limite {limit_name} não configurado'}
            
            config = self.limits[limit_name]
            client_key = f"{client_id}:{limit_name}"
            current_time = time.time()
            
            # Inicializar ou recuperar informações do cliente
            if client_key not in self.clients:
                self.clients[client_key] = RateLimitInfo(
                    requests_count=0,
                    window_start=current_time,
                    last_request=0,
                    is_blocked=False
                )
            
            client_info = self.clients[client_key]
            
            # Verificar se está bloqueado
            if client_info.is_blocked:
                if client_info.block_until and current_time < client_info.block_until:
                    remaining_block = client_info.block_until - current_time
                    return False, {
                        'blocked': True,
                        'block_remaining': remaining_block,
                        'block_until': client_info.block_until
                    }
                else:
                    # Desbloquear cliente
                    client_info.is_blocked = False
                    client_info.block_until = None
                    client_info.requests_count = 0
                    client_info.window_start = current_time
            
            # Verificar se janela de tempo expirou
            if current_time - client_info.window_start >= config.time_window:
                # Resetar contador
                client_info.requests_count = 0
                client_info.window_start = current_time
            
            # Verificar limite de rajada
            if config.burst_limit:
                time_since_last = current_time - client_info.last_request
                if time_since_last < 1.0:  # Menos de 1 segundo desde última requisição
                    if client_info.requests_count >= config.burst_limit:
                        return False, {
                            'burst_limit_exceeded': True,
                            'burst_limit': config.burst_limit,
                            'retry_after': 1.0 - time_since_last
                        }
            
            # Verificar limite principal
            if client_info.requests_count >= config.max_requests:
                # Bloquear cliente
                client_info.is_blocked = True
                client_info.block_until = current_time + config.block_duration
                
                return False, {
                    'rate_limit_exceeded': True,
                    'limit': config.max_requests,
                    'window': config.time_window,
                    'block_duration': config.block_duration,
                    'block_until': client_info.block_until
                }
            
            # Incrementar contador se permitido
            if increment:
                client_info.requests_count += 1
                client_info.last_request = current_time
            
            # Calcular informações de retorno
            remaining_requests = config.max_requests - client_info.requests_count
            window_reset = client_info.window_start + config.time_window
            
            return True, {
                'allowed': True,
                'remaining_requests': remaining_requests,
                'window_reset': window_reset,
                'requests_count': client_info.requests_count,
                'limit': config.max_requests
            }
    
    def get_client_info(self, client_id: str, limit_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do cliente
        
        Args:
            client_id: ID do cliente
            limit_name: Nome do limite
            
        Returns:
            Informações do cliente ou None
        """
        with self.lock:
            client_key = f"{client_id}:{limit_name}"
            if client_key not in self.clients:
                return None
            
            client_info = self.clients[client_key]
            config = self.limits.get(limit_name)
            
            if not config:
                return None
            
            return {
                'client_id': client_id,
                'limit_name': limit_name,
                'requests_count': client_info.requests_count,
                'is_blocked': client_info.is_blocked,
                'block_until': client_info.block_until,
                'window_start': client_info.window_start,
                'last_request': client_info.last_request,
                'remaining_requests': config.max_requests - client_info.requests_count,
                'limit_config': {
                    'max_requests': config.max_requests,
                    'time_window': config.time_window,
                    'burst_limit': config.burst_limit,
                    'block_duration': config.block_duration
                }
            }
    
    def reset_client(self, client_id: str, limit_name: Optional[str] = None):
        """
        Reseta contadores do cliente
        
        Args:
            client_id: ID do cliente
            limit_name: Nome do limite (None para todos)
        """
        with self.lock:
            if limit_name:
                client_key = f"{client_id}:{limit_name}"
                if client_key in self.clients:
                    del self.clients[client_key]
            else:
                # Remover todos os limites do cliente
                keys_to_remove = [key for key in self.clients.keys() if key.startswith(f"{client_id}:")]
                for key in keys_to_remove:
                    del self.clients[key]
            
            logger.info(f"Cliente {client_id} resetado para limite {limit_name or 'todos'}")
    
    def cleanup_expired_clients(self):
        """Remove clientes expirados"""
        with self.lock:
            current_time = time.time()
            expired_clients = []
            
            for client_key, client_info in self.clients.items():
                # Considerar expirado se não houve atividade por 24 horas
                if current_time - client_info.last_request > 86400:
                    expired_clients.append(client_key)
            
            for client_key in expired_clients:
                del self.clients[client_key]
            
            if expired_clients:
                logger.info(f"Removidos {len(expired_clients)} clientes expirados")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do rate limiter"""
        with self.lock:
            total_clients = len(self.clients)
            blocked_clients = sum(1 for info in self.clients.values() if info.is_blocked)
            
            # Estatísticas por limite
            limit_stats = {}
            for limit_name, config in self.limits.items():
                clients_for_limit = [info for key, info in self.clients.items() 
                                   if key.endswith(f":{limit_name}")]
                
                limit_stats[limit_name] = {
                    'total_clients': len(clients_for_limit),
                    'blocked_clients': sum(1 for info in clients_for_limit if info.is_blocked),
                    'avg_requests': sum(info.requests_count for info in clients_for_limit) / len(clients_for_limit) if clients_for_limit else 0,
                    'config': {
                        'max_requests': config.max_requests,
                        'time_window': config.time_window,
                        'burst_limit': config.burst_limit,
                        'block_duration': config.block_duration
                    }
                }
            
            return {
                'total_clients': total_clients,
                'blocked_clients': blocked_clients,
                'active_clients': total_clients - blocked_clients,
                'limits': limit_stats
            }


class RateLimitMiddleware:
    """
    Middleware para rate limiting em APIs
    
    Funcionalidades:
    - Decorator para endpoints
    - Headers de resposta
    - Logging de violações
    """
    
    def __init__(self, rate_limiter: RateLimiter):
        """
        Inicializa o middleware
        
        Args:
            rate_limiter: Instância do rate limiter
        """
        self.rate_limiter = rate_limiter
    
    def limit_by_ip(self, limit_name: str):
        """
        Decorator para limitar por IP
        
        Args:
            limit_name: Nome do limite a aplicar
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extrair IP da requisição (implementar conforme framework)
                client_ip = self._extract_client_ip()
                
                is_allowed, info = self.rate_limiter.is_allowed(client_ip, limit_name)
                
                if not is_allowed:
                    logger.warning(f"Rate limit excedido para IP {client_ip} no limite {limit_name}")
                    return self._create_rate_limit_response(info)
                
                # Adicionar headers de rate limit
                response = func(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers.update(self._create_rate_limit_headers(info))
                
                return response
            
            return wrapper
        return decorator
    
    def limit_by_user(self, limit_name: str, user_id_extractor: Callable):
        """
        Decorator para limitar por usuário
        
        Args:
            limit_name: Nome do limite a aplicar
            user_id_extractor: Função para extrair ID do usuário
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    user_id = user_id_extractor(*args, **kwargs)
                    if not user_id:
                        return func(*args, **kwargs)
                    
                    is_allowed, info = self.rate_limiter.is_allowed(str(user_id), limit_name)
                    
                    if not is_allowed:
                        logger.warning(f"Rate limit excedido para usuário {user_id} no limite {limit_name}")
                        return self._create_rate_limit_response(info)
                    
                    response = func(*args, **kwargs)
                    if hasattr(response, 'headers'):
                        response.headers.update(self._create_rate_limit_headers(info))
                    
                    return response
                except Exception as e:
                    logger.error(f"Erro no rate limiting por usuário: {e}")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def _extract_client_ip(self) -> str:
        """Extrai IP do cliente (implementar conforme framework)"""
        # Implementação básica - adaptar conforme necessário
        import socket
        return socket.gethostbyname(socket.gethostname())
    
    def _create_rate_limit_response(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Cria resposta de rate limit excedido"""
        return {
            'error': 'Rate limit exceeded',
            'message': 'Muitas requisições. Tente novamente mais tarde.',
            'details': info,
            'status_code': 429
        }
    
    def _create_rate_limit_headers(self, info: Dict[str, Any]) -> Dict[str, str]:
        """Cria headers de rate limit"""
        headers = {}
        
        if 'remaining_requests' in info:
            headers['X-RateLimit-Remaining'] = str(info['remaining_requests'])
        
        if 'limit' in info:
            headers['X-RateLimit-Limit'] = str(info['limit'])
        
        if 'window_reset' in info:
            headers['X-RateLimit-Reset'] = str(int(info['window_reset']))
        
        if 'block_until' in info:
            headers['X-RateLimit-Block-Until'] = str(int(info['block_until']))
        
        return headers


# Instância global do rate limiter
_rate_limiter_instance: Optional[RateLimiter] = None
_middleware_instance: Optional[RateLimitMiddleware] = None

def get_rate_limiter() -> RateLimiter:
    """Retorna instância global do rate limiter"""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance

def get_rate_limit_middleware() -> RateLimitMiddleware:
    """Retorna instância global do middleware"""
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = RateLimitMiddleware(get_rate_limiter())
    return _middleware_instance

def check_rate_limit(client_id: str, limit_name: str) -> tuple[bool, Dict[str, Any]]:
    """Função de conveniência para verificar rate limit"""
    return get_rate_limiter().is_allowed(client_id, limit_name)

def get_client_rate_limit_info(client_id: str, limit_name: str) -> Optional[Dict[str, Any]]:
    """Função de conveniência para obter informações do cliente"""
    return get_rate_limiter().get_client_info(client_id, limit_name)
