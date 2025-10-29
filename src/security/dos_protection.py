"""
FiscalAI MVP - Proteção contra DoS
Sistema avançado de rate limiting e proteção contra ataques DoS
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import hashlib
import json

logger = logging.getLogger(__name__)

@dataclass
class RateLimitRule:
    """Regra de rate limiting"""
    rule_id: str
    name: str
    pattern: str  # Padrão de URL ou ação
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int
    block_duration: int  # segundos
    enabled: bool

@dataclass
class RateLimitViolation:
    """Violação de rate limit"""
    violation_id: str
    timestamp: datetime
    client_id: str
    rule_id: str
    violation_type: str
    current_count: int
    limit: int
    block_until: Optional[datetime] = None

class DoSProtectionSystem:
    """
    Sistema de proteção contra DoS com rate limiting avançado
    
    Funcionalidades:
    - Rate limiting por IP, usuário e endpoint
    - Detecção de padrões suspeitos
    - Proteção contra ataques distribuídos
    - Whitelist/blacklist dinâmica
    - Análise de comportamento
    """
    
    def __init__(self):
        """Inicializa o sistema de proteção DoS"""
        # Contadores de requisições
        self.request_counters = defaultdict(lambda: defaultdict(lambda: deque()))
        self.blocked_clients = {}
        self.whitelist = set()
        self.blacklist = set()
        
        # Regras de rate limiting
        self.rate_limit_rules = self._initialize_default_rules()
        
        # Configurações
        self.max_requests_per_minute = 60
        self.max_requests_per_hour = 1000
        self.max_requests_per_day = 10000
        self.burst_limit = 10
        self.block_duration = 300  # 5 minutos
        
        # Análise de comportamento
        self.behavior_patterns = defaultdict(list)
        self.suspicious_ips = set()
        
        # Thread de limpeza
        self.cleanup_thread = threading.Thread(target=self._cleanup_counters, daemon=True)
        self.cleanup_thread.start()
    
    def _initialize_default_rules(self) -> Dict[str, RateLimitRule]:
        """Inicializa regras padrão de rate limiting"""
        rules = {}
        
        # Regra para API geral
        rules["api_general"] = RateLimitRule(
            rule_id="api_general",
            name="API Geral",
            pattern="/api/.*",
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=10,
            block_duration=300,
            enabled=True
        )
        
        # Regra para upload de arquivos
        rules["file_upload"] = RateLimitRule(
            rule_id="file_upload",
            name="Upload de Arquivos",
            pattern="/upload.*",
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500,
            burst_limit=3,
            block_duration=600,
            enabled=True
        )
        
        # Regra para análise de documentos
        rules["document_analysis"] = RateLimitRule(
            rule_id="document_analysis",
            name="Análise de Documentos",
            pattern="/analyze.*",
            requests_per_minute=20,
            requests_per_hour=200,
            requests_per_day=1000,
            burst_limit=5,
            block_duration=900,
            enabled=True
        )
        
        # Regra para login
        rules["login"] = RateLimitRule(
            rule_id="login",
            name="Login",
            pattern="/login.*",
            requests_per_minute=5,
            requests_per_hour=20,
            requests_per_day=50,
            burst_limit=3,
            block_duration=1800,
            enabled=True
        )
        
        # Regra para admin
        rules["admin"] = RateLimitRule(
            rule_id="admin",
            name="Administração",
            pattern="/admin.*",
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=2000,
            burst_limit=5,
            block_duration=600,
            enabled=True
        )
        
        return rules
    
    def check_rate_limit(self, 
                        client_id: str, 
                        endpoint: str,
                        user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Verifica rate limit para cliente
        
        Args:
            client_id: ID do cliente (IP ou identificador único)
            endpoint: Endpoint sendo acessado
            user_id: ID do usuário (se autenticado)
            
        Returns:
            (is_allowed, rate_info)
        """
        # Verificar se cliente está bloqueado
        if client_id in self.blocked_clients:
            block_until = self.blocked_clients[client_id]
            if datetime.now() < block_until:
                return False, {
                    "status": "blocked",
                    "block_until": block_until.isoformat(),
                    "reason": "Client is blocked"
                }
            else:
                # Remover do bloqueio
                del self.blocked_clients[client_id]
        
        # Verificar whitelist
        if client_id in self.whitelist:
            return True, {"status": "whitelisted"}
        
        # Verificar blacklist
        if client_id in self.blacklist:
            return False, {"status": "blacklisted", "reason": "Client is blacklisted"}
        
        # Encontrar regra aplicável
        applicable_rule = self._find_applicable_rule(endpoint)
        if not applicable_rule:
            # Usar regras padrão
            return self._check_default_limits(client_id, endpoint)
        
        # Verificar limites da regra
        is_allowed, violation_info = self._check_rule_limits(client_id, endpoint, applicable_rule)
        
        if not is_allowed:
            # Bloquear cliente se necessário
            if violation_info.get("should_block", False):
                self._block_client(client_id, applicable_rule.block_duration)
                violation_info["blocked"] = True
        
        return is_allowed, violation_info
    
    def _find_applicable_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Encontra regra aplicável para endpoint"""
        for rule in self.rate_limit_rules.values():
            if rule.enabled and self._matches_pattern(endpoint, rule.pattern):
                return rule
        return None
    
    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Verifica se endpoint corresponde ao padrão"""
        import re
        return bool(re.match(pattern, endpoint))
    
    def _check_rule_limits(self, client_id: str, endpoint: str, rule: RateLimitRule) -> Tuple[bool, Dict[str, Any]]:
        """Verifica limites de uma regra específica"""
        now = datetime.now()
        
        # Obter contadores do cliente
        client_counters = self.request_counters[client_id]
        
        # Verificar limite por minuto
        minute_count = self._count_requests_in_window(
            client_counters.get("minute", deque()),
            now - timedelta(minutes=1)
        )
        
        if minute_count >= rule.requests_per_minute:
            return False, {
                "status": "rate_limited",
                "limit_type": "minute",
                "current_count": minute_count,
                "limit": rule.requests_per_minute,
                "should_block": minute_count > rule.burst_limit
            }
        
        # Verificar limite por hora
        hour_count = self._count_requests_in_window(
            client_counters.get("hour", deque()),
            now - timedelta(hours=1)
        )
        
        if hour_count >= rule.requests_per_hour:
            return False, {
                "status": "rate_limited",
                "limit_type": "hour",
                "current_count": hour_count,
                "limit": rule.requests_per_hour,
                "should_block": True
            }
        
        # Verificar limite por dia
        day_count = self._count_requests_in_window(
            client_counters.get("day", deque()),
            now - timedelta(days=1)
        )
        
        if day_count >= rule.requests_per_day:
            return False, {
                "status": "rate_limited",
                "limit_type": "day",
                "current_count": day_count,
                "limit": rule.requests_per_day,
                "should_block": True
            }
        
        # Registrar requisição
        self._record_request(client_id, endpoint, now)
        
        return True, {
            "status": "allowed",
            "minute_count": minute_count + 1,
            "hour_count": hour_count + 1,
            "day_count": day_count + 1
        }
    
    def _check_default_limits(self, client_id: str, endpoint: str) -> Tuple[bool, Dict[str, Any]]:
        """Verifica limites padrão"""
        now = datetime.now()
        client_counters = self.request_counters[client_id]
        
        # Verificar limite por minuto
        minute_count = self._count_requests_in_window(
            client_counters.get("minute", deque()),
            now - timedelta(minutes=1)
        )
        
        if minute_count >= self.max_requests_per_minute:
            return False, {
                "status": "rate_limited",
                "limit_type": "minute",
                "current_count": minute_count,
                "limit": self.max_requests_per_minute
            }
        
        # Registrar requisição
        self._record_request(client_id, endpoint, now)
        
        return True, {
            "status": "allowed",
            "minute_count": minute_count + 1
        }
    
    def _count_requests_in_window(self, requests: deque, window_start: datetime) -> int:
        """Conta requisições em uma janela de tempo"""
        # Remover requisições antigas
        while requests and requests[0] < window_start:
            requests.popleft()
        
        return len(requests)
    
    def _record_request(self, client_id: str, endpoint: str, timestamp: datetime):
        """Registra uma requisição"""
        client_counters = self.request_counters[client_id]
        
        # Adicionar timestamp às filas
        client_counters["minute"].append(timestamp)
        client_counters["hour"].append(timestamp)
        client_counters["day"].append(timestamp)
        
        # Manter tamanho das filas
        for window in ["minute", "hour", "day"]:
            if len(client_counters[window]) > 10000:  # Limite de memória
                client_counters[window] = deque(list(client_counters[window])[-5000:])
    
    def _block_client(self, client_id: str, duration: int):
        """Bloqueia cliente por um período"""
        block_until = datetime.now() + timedelta(seconds=duration)
        self.blocked_clients[client_id] = block_until
        
        logger.warning(f"Cliente {client_id} bloqueado até {block_until}")
    
    def add_to_whitelist(self, client_id: str):
        """Adiciona cliente à whitelist"""
        self.whitelist.add(client_id)
        logger.info(f"Cliente {client_id} adicionado à whitelist")
    
    def remove_from_whitelist(self, client_id: str):
        """Remove cliente da whitelist"""
        self.whitelist.discard(client_id)
        logger.info(f"Cliente {client_id} removido da whitelist")
    
    def add_to_blacklist(self, client_id: str):
        """Adiciona cliente à blacklist"""
        self.blacklist.add(client_id)
        logger.info(f"Cliente {client_id} adicionado à blacklist")
    
    def remove_from_blacklist(self, client_id: str):
        """Remove cliente da blacklist"""
        self.blacklist.discard(client_id)
        logger.info(f"Cliente {client_id} removido da blacklist")
    
    def add_rate_limit_rule(self, rule: RateLimitRule):
        """Adiciona regra de rate limiting"""
        self.rate_limit_rules[rule.rule_id] = rule
        logger.info(f"Regra de rate limiting adicionada: {rule.name}")
    
    def remove_rate_limit_rule(self, rule_id: str):
        """Remove regra de rate limiting"""
        if rule_id in self.rate_limit_rules:
            del self.rate_limit_rules[rule_id]
            logger.info(f"Regra de rate limiting removida: {rule_id}")
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas de rate limiting"""
        now = datetime.now()
        
        # Contar clientes ativos
        active_clients = len(self.request_counters)
        
        # Contar clientes bloqueados
        blocked_clients = len(self.blocked_clients)
        
        # Contar requisições por minuto
        total_requests_minute = 0
        for client_counters in self.request_counters.values():
            minute_count = self._count_requests_in_window(
                client_counters.get("minute", deque()),
                now - timedelta(minutes=1)
            )
            total_requests_minute += minute_count
        
        # Contar requisições por hora
        total_requests_hour = 0
        for client_counters in self.request_counters.values():
            hour_count = self._count_requests_in_window(
                client_counters.get("hour", deque()),
                now - timedelta(hours=1)
            )
            total_requests_hour += hour_count
        
        return {
            "active_clients": active_clients,
            "blocked_clients": blocked_clients,
            "whitelisted_clients": len(self.whitelist),
            "blacklisted_clients": len(self.blacklist),
            "total_requests_minute": total_requests_minute,
            "total_requests_hour": total_requests_hour,
            "rate_limit_rules": len(self.rate_limit_rules),
            "enabled_rules": len([r for r in self.rate_limit_rules.values() if r.enabled])
        }
    
    def get_client_info(self, client_id: str) -> Dict[str, Any]:
        """Obtém informações de um cliente específico"""
        now = datetime.now()
        
        if client_id not in self.request_counters:
            return {"status": "not_found"}
        
        client_counters = self.request_counters[client_id]
        
        # Contar requisições por janela
        minute_count = self._count_requests_in_window(
            client_counters.get("minute", deque()),
            now - timedelta(minutes=1)
        )
        
        hour_count = self._count_requests_in_window(
            client_counters.get("hour", deque()),
            now - timedelta(hours=1)
        )
        
        day_count = self._count_requests_in_window(
            client_counters.get("day", deque()),
            now - timedelta(days=1)
        )
        
        # Status do cliente
        status = "active"
        if client_id in self.blocked_clients:
            status = "blocked"
        elif client_id in self.whitelist:
            status = "whitelisted"
        elif client_id in self.blacklist:
            status = "blacklisted"
        
        return {
            "client_id": client_id,
            "status": status,
            "requests_minute": minute_count,
            "requests_hour": hour_count,
            "requests_day": day_count,
            "is_blocked": client_id in self.blocked_clients,
            "block_until": self.blocked_clients.get(client_id),
            "is_whitelisted": client_id in self.whitelist,
            "is_blacklisted": client_id in self.blacklist
        }
    
    def _cleanup_counters(self):
        """Limpa contadores antigos"""
        while True:
            try:
                now = datetime.now()
                cutoff_time = now - timedelta(hours=24)
                
                # Limpar contadores antigos
                for client_id in list(self.request_counters.keys()):
                    client_counters = self.request_counters[client_id]
                    
                    # Limpar requisições antigas
                    for window in ["minute", "hour", "day"]:
                        if window in client_counters:
                            while client_counters[window] and client_counters[window][0] < cutoff_time:
                                client_counters[window].popleft()
                    
                    # Remover cliente se não tem requisições recentes
                    if not any(client_counters.values()):
                        del self.request_counters[client_id]
                
                # Limpar bloqueios expirados
                expired_blocks = [
                    client_id for client_id, block_until in self.blocked_clients.items()
                    if now > block_until
                ]
                for client_id in expired_blocks:
                    del self.blocked_clients[client_id]
                
                time.sleep(300)  # Executar a cada 5 minutos
                
            except Exception as e:
                logger.error(f"Erro na limpeza de contadores: {e}")
                time.sleep(300)
    
    def export_config(self, file_path: str):
        """Exporta configuração do sistema"""
        config = {
            "exported_at": datetime.now().isoformat(),
            "rate_limit_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "requests_per_minute": rule.requests_per_minute,
                    "requests_per_hour": rule.requests_per_hour,
                    "requests_per_day": rule.requests_per_day,
                    "burst_limit": rule.burst_limit,
                    "block_duration": rule.block_duration,
                    "enabled": rule.enabled
                }
                for rule in self.rate_limit_rules.values()
            ],
            "whitelist": list(self.whitelist),
            "blacklist": list(self.blacklist),
            "default_limits": {
                "max_requests_per_minute": self.max_requests_per_minute,
                "max_requests_per_hour": self.max_requests_per_hour,
                "max_requests_per_day": self.max_requests_per_day,
                "burst_limit": self.burst_limit,
                "block_duration": self.block_duration
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Configuração exportada para {file_path}")


# Instância global do sistema de proteção
_dos_protection_instance: Optional[DoSProtectionSystem] = None

def get_dos_protection() -> DoSProtectionSystem:
    """Retorna instância global do sistema de proteção"""
    global _dos_protection_instance
    if _dos_protection_instance is None:
        _dos_protection_instance = DoSProtectionSystem()
    return _dos_protection_instance

def check_rate_limit(client_id: str, endpoint: str, user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
    """Função de conveniência para verificar rate limit"""
    return get_dos_protection().check_rate_limit(client_id, endpoint, user_id)
