"""
FiscalAI MVP - Auditoria de Segurança
Sistema de monitoramento e auditoria de segurança
"""

import json
import hashlib
import hmac
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from pathlib import Path
import re
from collections import defaultdict, Counter
import threading
import time

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Evento de segurança"""
    event_id: str
    timestamp: datetime
    event_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    source_ip: str
    user_id: Optional[str]
    action: str
    resource: str
    details: Dict[str, Any]
    risk_score: float
    is_blocked: bool
    correlation_id: Optional[str] = None

@dataclass
class SecurityAlert:
    """Alerta de segurança"""
    alert_id: str
    timestamp: datetime
    alert_type: str
    severity: str
    description: str
    affected_resources: List[str]
    recommended_actions: List[str]
    is_resolved: bool
    resolved_at: Optional[datetime] = None

@dataclass
class SecurityReport:
    """Relatório de segurança"""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    top_threats: List[Dict[str, Any]]
    security_score: float
    recommendations: List[str]

class SecurityAuditor:
    """
    Auditor de segurança para monitoramento e detecção de ameaças
    
    Funcionalidades:
    - Coleta de eventos de segurança
    - Detecção de anomalias
    - Geração de alertas
    - Análise de padrões suspeitos
    - Relatórios de segurança
    """
    
    def __init__(self, audit_dir: str = "security/audit"):
        """
        Inicializa o auditor de segurança
        
        Args:
            audit_dir: Diretório para armazenar logs de auditoria
        """
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Armazenamento de eventos
        self.events: List[SecurityEvent] = []
        self.alerts: List[SecurityAlert] = []
        
        # Configurações de detecção
        self.threat_patterns = self._load_threat_patterns()
        self.rate_limits = {
            "login_attempts": {"limit": 5, "window": 300},  # 5 tentativas em 5 minutos
            "api_calls": {"limit": 100, "window": 60},      # 100 chamadas em 1 minuto
            "file_uploads": {"limit": 10, "window": 300}    # 10 uploads em 5 minutos
        }
        
        # Contadores de eventos
        self.event_counters = defaultdict(lambda: defaultdict(int))
        self.ip_counters = defaultdict(lambda: defaultdict(int))
        
        # Thread de limpeza
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_events, daemon=True)
        self.cleanup_thread.start()
        
        # Carregar dados existentes
        self._load_audit_data()
    
    def _load_threat_patterns(self) -> Dict[str, List[str]]:
        """Carrega padrões de ameaças conhecidas"""
        return {
            "sql_injection": [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
                r"(\bUNION\s+SELECT\b)",
                r"(\bDROP\s+TABLE\b)"
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*="
            ],
            "path_traversal": [
                r"\.\./",
                r"\.\.\\",
                r"\.\.%2f",
                r"\.\.%5c"
            ],
            "command_injection": [
                r"[;&|`$]",
                r"\b(cat|ls|dir|type|rm|del|wget|curl|nc)\b",
                r"\b(python|perl|ruby|php|bash|sh|cmd)\b"
            ],
            "brute_force": [
                r"password\s*=\s*['\"]?admin['\"]?",
                r"password\s*=\s*['\"]?123456['\"]?",
                r"password\s*=\s*['\"]?password['\"]?"
            ],
            "suspicious_headers": [
                r"User-Agent:\s*$",
                r"X-Forwarded-For:\s*$",
                r"X-Real-IP:\s*$"
            ]
        }
    
    def log_security_event(self, 
                          event_type: str,
                          source_ip: str,
                          action: str,
                          resource: str,
                          details: Dict[str, Any],
                          user_id: Optional[str] = None,
                          severity: str = "medium") -> str:
        """
        Registra evento de segurança
        
        Args:
            event_type: Tipo do evento
            source_ip: IP de origem
            action: Ação realizada
            resource: Recurso afetado
            details: Detalhes do evento
            user_id: ID do usuário
            severity: Severidade do evento
            
        Returns:
            ID do evento
        """
        event_id = self._generate_event_id()
        
        # Calcular score de risco
        risk_score = self._calculate_risk_score(event_type, source_ip, action, details)
        
        # Verificar se deve ser bloqueado
        is_blocked = self._should_block_event(event_type, source_ip, action, risk_score)
        
        # Criar evento
        event = SecurityEvent(
            event_id=event_id,
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            risk_score=risk_score,
            is_blocked=is_blocked
        )
        
        # Adicionar evento
        self.events.append(event)
        
        # Atualizar contadores
        self.event_counters[event_type][source_ip] += 1
        self.ip_counters[source_ip][event_type] += 1
        
        # Verificar se deve gerar alerta
        if risk_score > 0.7 or is_blocked:
            self._generate_alert(event)
        
        # Salvar evento
        self._save_event(event)
        
        logger.info(f"Evento de segurança registrado: {event_id} - {event_type}")
        
        return event_id
    
    def _generate_event_id(self) -> str:
        """Gera ID único para evento"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        random_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"SEC_{timestamp}_{random_part}"
    
    def _calculate_risk_score(self, event_type: str, source_ip: str, action: str, details: Dict[str, Any]) -> float:
        """
        Calcula score de risco do evento
        
        Args:
            event_type: Tipo do evento
            source_ip: IP de origem
            action: Ação realizada
            details: Detalhes do evento
            
        Returns:
            Score de risco (0-1)
        """
        score = 0.0
        
        # Score baseado no tipo de evento
        event_scores = {
            "login_failure": 0.3,
            "login_success": 0.0,
            "file_upload": 0.2,
            "api_access": 0.1,
            "data_access": 0.2,
            "admin_action": 0.4,
            "suspicious_activity": 0.6,
            "security_violation": 0.8
        }
        score += event_scores.get(event_type, 0.1)
        
        # Score baseado em padrões de ameaça
        threat_score = self._detect_threat_patterns(action, details)
        score += threat_score * 0.3
        
        # Score baseado em frequência
        frequency_score = self._calculate_frequency_score(event_type, source_ip)
        score += frequency_score * 0.2
        
        # Score baseado em IP suspeito
        ip_score = self._calculate_ip_score(source_ip)
        score += ip_score * 0.2
        
        return min(score, 1.0)
    
    def _detect_threat_patterns(self, action: str, details: Dict[str, Any]) -> float:
        """
        Detecta padrões de ameaça no evento
        
        Args:
            action: Ação realizada
            details: Detalhes do evento
            
        Returns:
            Score de ameaça (0-1)
        """
        threat_score = 0.0
        
        # Verificar padrões de ameaça
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if re.search(pattern, action, re.IGNORECASE):
                    threat_score += 0.2
                    logger.warning(f"Padrão de ameaça detectado: {threat_type}")
        
        # Verificar detalhes do evento
        for key, value in details.items():
            if isinstance(value, str):
                for threat_type, patterns in self.threat_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            threat_score += 0.1
        
        return min(threat_score, 1.0)
    
    def _calculate_frequency_score(self, event_type: str, source_ip: str) -> float:
        """
        Calcula score baseado na frequência de eventos
        
        Args:
            event_type: Tipo do evento
            source_ip: IP de origem
            
        Returns:
            Score de frequência (0-1)
        """
        # Verificar limites de taxa
        if event_type in self.rate_limits:
            limit_config = self.rate_limits[event_type]
            current_count = self.event_counters[event_type][source_ip]
            
            if current_count > limit_config["limit"]:
                return 1.0
            elif current_count > limit_config["limit"] * 0.8:
                return 0.7
            elif current_count > limit_config["limit"] * 0.5:
                return 0.3
        
        return 0.0
    
    def _calculate_ip_score(self, source_ip: str) -> float:
        """
        Calcula score baseado no IP de origem
        
        Args:
            source_ip: IP de origem
            
        Returns:
            Score do IP (0-1)
        """
        # Verificar se é IP local
        if source_ip in ["127.0.0.1", "::1", "localhost"]:
            return 0.0
        
        # Verificar se é IP privado
        if source_ip.startswith(("10.", "172.", "192.168.")):
            return 0.1
        
        # Verificar frequência de eventos deste IP
        total_events = sum(self.ip_counters[source_ip].values())
        if total_events > 100:
            return 0.8
        elif total_events > 50:
            return 0.5
        elif total_events > 20:
            return 0.2
        
        return 0.0
    
    def _should_block_event(self, event_type: str, source_ip: str, action: str, risk_score: float) -> bool:
        """
        Determina se evento deve ser bloqueado
        
        Args:
            event_type: Tipo do evento
            source_ip: IP de origem
            action: Ação realizada
            risk_score: Score de risco
            
        Returns:
            True se deve ser bloqueado
        """
        # Bloquear se score de risco muito alto
        if risk_score > 0.9:
            return True
        
        # Bloquear se excedeu limites de taxa
        if event_type in self.rate_limits:
            limit_config = self.rate_limits[event_type]
            current_count = self.event_counters[event_type][source_ip]
            
            if current_count > limit_config["limit"]:
                return True
        
        # Bloquear se detectou padrões de ameaça críticos
        for threat_type, patterns in self.threat_patterns.items():
            if threat_type in ["sql_injection", "command_injection"]:
                for pattern in patterns:
                    if re.search(pattern, action, re.IGNORECASE):
                        return True
        
        return False
    
    def _generate_alert(self, event: SecurityEvent):
        """
        Gera alerta de segurança
        
        Args:
            event: Evento que gerou o alerta
        """
        alert_id = f"ALERT_{event.event_id}"
        
        # Determinar tipo de alerta
        if event.risk_score > 0.9:
            alert_type = "critical_threat"
            severity = "critical"
        elif event.risk_score > 0.7:
            alert_type = "high_risk_activity"
            severity = "high"
        else:
            alert_type = "suspicious_activity"
            severity = "medium"
        
        # Gerar descrição
        description = f"Evento de segurança detectado: {event.event_type} de {event.source_ip}"
        
        # Determinar ações recomendadas
        recommended_actions = self._get_recommended_actions(event)
        
        # Criar alerta
        alert = SecurityAlert(
            alert_id=alert_id,
            timestamp=datetime.now(),
            alert_type=alert_type,
            severity=severity,
            description=description,
            affected_resources=[event.resource],
            recommended_actions=recommended_actions,
            is_resolved=False
        )
        
        self.alerts.append(alert)
        
        # Salvar alerta
        self._save_alert(alert)
        
        logger.warning(f"Alerta de segurança gerado: {alert_id}")
    
    def _get_recommended_actions(self, event: SecurityEvent) -> List[str]:
        """
        Obtém ações recomendadas para evento
        
        Args:
            event: Evento de segurança
            
        Returns:
            Lista de ações recomendadas
        """
        actions = []
        
        if event.risk_score > 0.8:
            actions.append("Bloquear IP de origem")
            actions.append("Investigar atividade suspeita")
        
        if event.event_type == "login_failure":
            actions.append("Verificar credenciais")
            actions.append("Implementar 2FA")
        
        if event.event_type == "file_upload":
            actions.append("Verificar arquivo enviado")
            actions.append("Escanear por malware")
        
        if event.is_blocked:
            actions.append("Revisar logs de bloqueio")
            actions.append("Considerar whitelist se falso positivo")
        
        return actions
    
    def get_security_events(self, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           event_type: Optional[str] = None,
                           severity: Optional[str] = None,
                           source_ip: Optional[str] = None) -> List[SecurityEvent]:
        """
        Obtém eventos de segurança filtrados
        
        Args:
            start_time: Data de início
            end_time: Data de fim
            event_type: Tipo de evento
            severity: Severidade
            source_ip: IP de origem
            
        Returns:
            Lista de eventos filtrados
        """
        filtered_events = self.events
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]
        
        if source_ip:
            filtered_events = [e for e in filtered_events if e.source_ip == source_ip]
        
        return filtered_events
    
    def get_security_alerts(self, resolved: Optional[bool] = None) -> List[SecurityAlert]:
        """
        Obtém alertas de segurança
        
        Args:
            resolved: Filtrar por status de resolução
            
        Returns:
            Lista de alertas
        """
        if resolved is None:
            return self.alerts
        else:
            return [a for a in self.alerts if a.is_resolved == resolved]
    
    def generate_security_report(self, 
                                start_time: datetime,
                                end_time: datetime) -> SecurityReport:
        """
        Gera relatório de segurança
        
        Args:
            start_time: Data de início
            end_time: Data de fim
            
        Returns:
            Relatório de segurança
        """
        # Filtrar eventos do período
        period_events = self.get_security_events(start_time, end_time)
        
        # Estatísticas básicas
        total_events = len(period_events)
        events_by_type = Counter([e.event_type for e in period_events])
        events_by_severity = Counter([e.severity for e in period_events])
        
        # Top ameaças
        top_threats = self._analyze_top_threats(period_events)
        
        # Calcular score de segurança
        security_score = self._calculate_security_score(period_events)
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(period_events)
        
        # Criar relatório
        report = SecurityReport(
            report_id=f"RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generated_at=datetime.now(),
            period_start=start_time,
            period_end=end_time,
            total_events=total_events,
            events_by_type=dict(events_by_type),
            events_by_severity=dict(events_by_severity),
            top_threats=top_threats,
            security_score=security_score,
            recommendations=recommendations
        )
        
        # Salvar relatório
        self._save_report(report)
        
        return report
    
    def _analyze_top_threats(self, events: List[SecurityEvent]) -> List[Dict[str, Any]]:
        """Analisa principais ameaças"""
        threat_scores = defaultdict(float)
        
        for event in events:
            for threat_type, patterns in self.threat_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, event.action, re.IGNORECASE):
                        threat_scores[threat_type] += event.risk_score
        
        # Ordenar por score
        sorted_threats = sorted(threat_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"threat_type": threat, "score": score, "count": int(score * 10)}
            for threat, score in sorted_threats[:5]
        ]
    
    def _calculate_security_score(self, events: List[SecurityEvent]) -> float:
        """Calcula score de segurança"""
        if not events:
            return 100.0
        
        # Penalizar por eventos de alto risco
        high_risk_events = [e for e in events if e.risk_score > 0.7]
        penalty = len(high_risk_events) * 5
        
        # Penalizar por eventos bloqueados
        blocked_events = [e for e in events if e.is_blocked]
        penalty += len(blocked_events) * 2
        
        # Calcular score
        score = max(0.0, 100.0 - penalty)
        
        return score
    
    def _generate_recommendations(self, events: List[SecurityEvent]) -> List[str]:
        """Gera recomendações de segurança"""
        recommendations = []
        
        # Analisar padrões
        high_risk_events = [e for e in events if e.risk_score > 0.7]
        if len(high_risk_events) > 10:
            recommendations.append("Implementar rate limiting mais restritivo")
        
        blocked_events = [e for e in events if e.is_blocked]
        if len(blocked_events) > 5:
            recommendations.append("Revisar regras de bloqueio para evitar falsos positivos")
        
        login_failures = [e for e in events if e.event_type == "login_failure"]
        if len(login_failures) > 20:
            recommendations.append("Implementar 2FA para contas administrativas")
        
        # Verificar IPs suspeitos
        ip_counts = Counter([e.source_ip for e in events])
        suspicious_ips = [ip for ip, count in ip_counts.items() if count > 50]
        if suspicious_ips:
            recommendations.append(f"Investigar IPs suspeitos: {', '.join(suspicious_ips[:3])}")
        
        return recommendations
    
    def _save_event(self, event: SecurityEvent):
        """Salva evento em arquivo"""
        event_file = self.audit_dir / f"events_{datetime.now().strftime('%Y%m%d')}.json"
        
        event_data = asdict(event)
        event_data['timestamp'] = event.timestamp.isoformat()
        
        with open(event_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + '\n')
    
    def _save_alert(self, alert: SecurityAlert):
        """Salva alerta em arquivo"""
        alert_file = self.audit_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        
        alert_data = asdict(alert)
        alert_data['timestamp'] = alert.timestamp.isoformat()
        if alert.resolved_at:
            alert_data['resolved_at'] = alert.resolved_at.isoformat()
        
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert_data, ensure_ascii=False) + '\n')
    
    def _save_report(self, report: SecurityReport):
        """Salva relatório em arquivo"""
        report_file = self.audit_dir / f"report_{report.report_id}.json"
        
        report_data = asdict(report)
        report_data['generated_at'] = report.generated_at.isoformat()
        report_data['period_start'] = report.period_start.isoformat()
        report_data['period_end'] = report.period_end.isoformat()
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    def _load_audit_data(self):
        """Carrega dados de auditoria existentes"""
        # Carregar eventos do dia atual
        today = datetime.now().strftime('%Y%m%d')
        event_file = self.audit_dir / f"events_{today}.json"
        
        if event_file.exists():
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        event_data = json.loads(line.strip())
                        event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                        event = SecurityEvent(**event_data)
                        self.events.append(event)
                
                logger.info(f"Carregados {len(self.events)} eventos de auditoria")
            except Exception as e:
                logger.error(f"Erro ao carregar eventos de auditoria: {e}")
    
    def _cleanup_old_events(self):
        """Limpa eventos antigos"""
        while True:
            try:
                # Manter apenas eventos dos últimos 30 dias
                cutoff_date = datetime.now() - timedelta(days=30)
                self.events = [e for e in self.events if e.timestamp > cutoff_date]
                
                # Limpar contadores antigos
                for event_type in list(self.event_counters.keys()):
                    for ip in list(self.event_counters[event_type].keys()):
                        if self.event_counters[event_type][ip] == 0:
                            del self.event_counters[event_type][ip]
                
                time.sleep(3600)  # Executar a cada hora
            except Exception as e:
                logger.error(f"Erro na limpeza de eventos: {e}")
                time.sleep(3600)


# Instância global do auditor
_security_auditor_instance: Optional[SecurityAuditor] = None

def get_security_auditor() -> SecurityAuditor:
    """Retorna instância global do auditor"""
    global _security_auditor_instance
    if _security_auditor_instance is None:
        _security_auditor_instance = SecurityAuditor()
    return _security_auditor_instance

def log_security_event(event_type: str, source_ip: str, action: str, resource: str, 
                      details: Dict[str, Any], user_id: Optional[str] = None, 
                      severity: str = "medium") -> str:
    """Função de conveniência para registrar evento"""
    return get_security_auditor().log_security_event(
        event_type, source_ip, action, resource, details, user_id, severity
    )
