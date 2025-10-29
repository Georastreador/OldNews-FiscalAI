"""
FiscalAI MVP - Sistema de Monitoramento
Métricas em tempo real para observabilidade e performance
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging
from pathlib import Path
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class Metric:
    """Métrica individual"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    unit: str = "count"

@dataclass
class PerformanceMetric:
    """Métrica de performance"""
    operation: str
    duration_ms: float
    success: bool
    timestamp: datetime
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None

@dataclass
class SystemMetric:
    """Métrica do sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_mb: float
    network_sent_mb: float
    network_recv_mb: float

class MetricsCollector:
    """
    Coletor de métricas em tempo real
    
    Funcionalidades:
    - Coleta de métricas de sistema
    - Métricas de aplicação
    - Métricas de performance
    - Agregação de dados
    - Alertas automáticos
    """
    
    def __init__(self, 
                 metrics_dir: str = "metrics",
                 retention_days: int = 30,
                 collection_interval: int = 60):
        """
        Inicializa o coletor de métricas
        
        Args:
            metrics_dir: Diretório para armazenar métricas
            retention_days: Dias de retenção de dados
            collection_interval: Intervalo de coleta em segundos
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        self.retention_days = retention_days
        self.collection_interval = collection_interval
        
        # Armazenamento de métricas
        self.metrics: deque = deque(maxlen=10000)  # Últimas 10k métricas
        self.performance_metrics: deque = deque(maxlen=5000)
        self.system_metrics: deque = deque(maxlen=1000)
        
        # Contadores
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Thread de coleta
        self.collection_thread = None
        self.running = False
        self.lock = threading.RLock()
        
        # Alertas
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'response_time_ms': 5000.0,
            'error_rate_percent': 5.0
        }
    
    def start_collection(self):
        """Inicia coleta de métricas"""
        if self.running:
            return
        
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        logger.info("Coleta de métricas iniciada")
    
    def stop_collection(self):
        """Para coleta de métricas"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5.0)
        
        logger.info("Coleta de métricas parada")
    
    def _collection_loop(self):
        """Loop principal de coleta"""
        while self.running:
            try:
                self._collect_system_metrics()
                self._cleanup_old_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Erro na coleta de métricas: {e}")
                time.sleep(5)  # Aguardar antes de tentar novamente
    
    def _collect_system_metrics(self):
        """Coleta métricas do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memória
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_mb = disk.free / (1024 * 1024)
            
            # Rede
            network = psutil.net_io_counters()
            network_sent_mb = network.bytes_sent / (1024 * 1024)
            network_recv_mb = network.bytes_recv / (1024 * 1024)
            
            # Criar métrica do sistema
            system_metric = SystemMetric(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_mb=disk_free_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb
            )
            
            with self.lock:
                self.system_metrics.append(system_metric)
            
            # Verificar alertas
            self._check_alerts(system_metric)
            
        except Exception as e:
            logger.error(f"Erro ao coletar métricas do sistema: {e}")
    
    def _check_alerts(self, system_metric: SystemMetric):
        """Verifica alertas baseados nas métricas"""
        alerts = []
        
        # CPU alto
        if system_metric.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'message': f"CPU usage high: {system_metric.cpu_percent:.1f}%",
                'severity': 'warning',
                'timestamp': system_metric.timestamp,
                'value': system_metric.cpu_percent,
                'threshold': self.alert_thresholds['cpu_percent']
            })
        
        # Memória alta
        if system_metric.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'message': f"Memory usage high: {system_metric.memory_percent:.1f}%",
                'severity': 'warning',
                'timestamp': system_metric.timestamp,
                'value': system_metric.memory_percent,
                'threshold': self.alert_thresholds['memory_percent']
            })
        
        # Disco cheio
        if system_metric.disk_usage_percent > self.alert_thresholds['disk_usage_percent']:
            alerts.append({
                'type': 'disk_full',
                'message': f"Disk usage high: {system_metric.disk_usage_percent:.1f}%",
                'severity': 'critical',
                'timestamp': system_metric.timestamp,
                'value': system_metric.disk_usage_percent,
                'threshold': self.alert_thresholds['disk_usage_percent']
            })
        
        # Adicionar alertas
        for alert in alerts:
            self._add_alert(alert)
    
    def _add_alert(self, alert: Dict[str, Any]):
        """Adiciona alerta"""
        with self.lock:
            self.alerts.append(alert)
            # Manter apenas últimos 1000 alertas
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]
    
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Registra contador"""
        with self.lock:
            self.counters[name] += value
            
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {},
                unit="count"
            )
            self.metrics.append(metric)
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra gauge"""
        with self.lock:
            self.gauges[name] = value
            
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {},
                unit="gauge"
            )
            self.metrics.append(metric)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Registra histograma"""
        with self.lock:
            self.histograms[name].append(value)
            # Manter apenas últimos 1000 valores
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {},
                unit="histogram"
            )
            self.metrics.append(metric)
    
    def record_performance(self, operation: str, duration_ms: float, success: bool = True, 
                          extra_data: Optional[Dict[str, Any]] = None):
        """Registra métrica de performance"""
        try:
            memory_usage = psutil.Process().memory_info().rss / (1024 * 1024)
            cpu_usage = psutil.cpu_percent()
        except:
            memory_usage = None
            cpu_usage = None
        
        performance_metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            timestamp=datetime.now(),
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            extra_data=extra_data
        )
        
        with self.lock:
            self.performance_metrics.append(performance_metric)
        
        # Registrar como histograma também
        self.record_histogram(f"operation_duration_{operation}", duration_ms)
        
        # Verificar alerta de tempo de resposta
        if duration_ms > self.alert_thresholds['response_time_ms']:
            self._add_alert({
                'type': 'slow_operation',
                'message': f"Slow operation: {operation} took {duration_ms:.1f}ms",
                'severity': 'warning',
                'timestamp': datetime.now(),
                'value': duration_ms,
                'threshold': self.alert_thresholds['response_time_ms']
            })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas"""
        with self.lock:
            # Métricas atuais
            current_metrics = {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histogram_stats': {}
            }
            
            # Estatísticas dos histogramas
            for name, values in self.histograms.items():
                if values:
                    current_metrics['histogram_stats'][name] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 0 else 0
                    }
            
            # Métricas do sistema (última)
            latest_system = self.system_metrics[-1] if self.system_metrics else None
            if latest_system:
                current_metrics['system'] = asdict(latest_system)
            
            # Performance (últimas 10)
            recent_performance = list(self.performance_metrics)[-10:]
            current_metrics['recent_performance'] = [asdict(p) for p in recent_performance]
            
            # Alertas ativos (últimas 24h)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_alerts = [a for a in self.alerts if a['timestamp'] > cutoff_time]
            current_metrics['recent_alerts'] = recent_alerts
            
            return current_metrics
    
    def get_performance_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Retorna estatísticas de performance"""
        with self.lock:
            if operation:
                # Filtrar por operação
                filtered_metrics = [p for p in self.performance_metrics if p.operation == operation]
            else:
                filtered_metrics = list(self.performance_metrics)
            
            if not filtered_metrics:
                return {}
            
            durations = [p.duration_ms for p in filtered_metrics]
            successes = [p for p in filtered_metrics if p.success]
            
            return {
                'total_operations': len(filtered_metrics),
                'successful_operations': len(successes),
                'success_rate': len(successes) / len(filtered_metrics) * 100,
                'avg_duration_ms': sum(durations) / len(durations),
                'min_duration_ms': min(durations),
                'max_duration_ms': max(durations),
                'p95_duration_ms': sorted(durations)[int(len(durations) * 0.95)] if durations else 0
            }
    
    def _cleanup_old_metrics(self):
        """Remove métricas antigas"""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        
        with self.lock:
            # Limpar métricas antigas
            self.metrics = deque([m for m in self.metrics if m.timestamp > cutoff_time], maxlen=10000)
            self.performance_metrics = deque([p for p in self.performance_metrics if p.timestamp > cutoff_time], maxlen=5000)
            self.system_metrics = deque([s for s in self.system_metrics if s.timestamp > cutoff_time], maxlen=1000)
    
    def export_metrics(self, file_path: str):
        """Exporta métricas para arquivo"""
        with self.lock:
            data = {
                'exported_at': datetime.now().isoformat(),
                'metrics': [asdict(m) for m in self.metrics],
                'performance_metrics': [asdict(p) for p in self.performance_metrics],
                'system_metrics': [asdict(s) for s in self.system_metrics],
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'alerts': self.alerts
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
    
    def set_alert_threshold(self, metric_name: str, threshold: float):
        """Define threshold para alerta"""
        if metric_name in self.alert_thresholds:
            self.alert_thresholds[metric_name] = threshold
            logger.info(f"Threshold para {metric_name} definido como {threshold}")


class MonitoringDashboard:
    """
    Dashboard de monitoramento
    
    Funcionalidades:
    - Visualização de métricas
    - Alertas em tempo real
    - Gráficos de performance
    - Status do sistema
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """
        Inicializa o dashboard
        
        Args:
            metrics_collector: Instância do coletor de métricas
        """
        self.metrics_collector = metrics_collector
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Retorna dados para o dashboard"""
        summary = self.metrics_collector.get_metrics_summary()
        
        # Adicionar informações do dashboard
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'status': self._get_system_status(summary),
            'metrics': summary,
            'performance': self.metrics_collector.get_performance_stats(),
            'alerts': self._get_active_alerts(summary.get('recent_alerts', [])),
            'recommendations': self._get_recommendations(summary)
        }
        
        return dashboard_data
    
    def _get_system_status(self, summary: Dict[str, Any]) -> str:
        """Determina status do sistema"""
        system = summary.get('system', {})
        
        if not system:
            return 'unknown'
        
        # Verificar alertas críticos
        alerts = summary.get('recent_alerts', [])
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        
        if critical_alerts:
            return 'critical'
        
        # Verificar métricas de sistema
        cpu = system.get('cpu_percent', 0)
        memory = system.get('memory_percent', 0)
        disk = system.get('disk_usage_percent', 0)
        
        if cpu > 90 or memory > 95 or disk > 95:
            return 'warning'
        
        if cpu > 70 or memory > 80 or disk > 80:
            return 'degraded'
        
        return 'healthy'
    
    def _get_active_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retorna alertas ativos"""
        # Filtrar alertas das últimas 2 horas
        cutoff_time = datetime.now() - timedelta(hours=2)
        active_alerts = []
        
        for alert in alerts:
            if isinstance(alert['timestamp'], str):
                alert_time = datetime.fromisoformat(alert['timestamp'])
            else:
                alert_time = alert['timestamp']
            
            if alert_time > cutoff_time:
                active_alerts.append(alert)
        
        return active_alerts
    
    def _get_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nas métricas"""
        recommendations = []
        
        system = summary.get('system', {})
        if system:
            cpu = system.get('cpu_percent', 0)
            memory = system.get('memory_percent', 0)
            disk = system.get('disk_usage_percent', 0)
            
            if cpu > 80:
                recommendations.append("Considerar otimização de CPU ou scaling horizontal")
            
            if memory > 85:
                recommendations.append("Considerar aumento de memória ou otimização de uso")
            
            if disk > 90:
                recommendations.append("Limpeza de disco necessária - espaço crítico")
        
        # Verificar performance
        performance = summary.get('recent_performance', [])
        if performance:
            avg_duration = sum(p['duration_ms'] for p in performance) / len(performance)
            if avg_duration > 5000:
                recommendations.append("Tempos de resposta altos - considerar otimização")
        
        return recommendations


# Instâncias globais
_metrics_collector_instance: Optional[MetricsCollector] = None
_dashboard_instance: Optional[MonitoringDashboard] = None

def get_metrics_collector() -> MetricsCollector:
    """Retorna instância global do coletor de métricas"""
    global _metrics_collector_instance
    if _metrics_collector_instance is None:
        _metrics_collector_instance = MetricsCollector()
        _metrics_collector_instance.start_collection()
    return _metrics_collector_instance

def get_monitoring_dashboard() -> MonitoringDashboard:
    """Retorna instância global do dashboard"""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard(get_metrics_collector())
    return _dashboard_instance

# Funções de conveniência
def record_counter(name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
    """Função de conveniência para registrar contador"""
    get_metrics_collector().record_counter(name, value, tags)

def record_gauge(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Função de conveniência para registrar gauge"""
    get_metrics_collector().record_gauge(name, value, tags)

def record_performance(operation: str, duration_ms: float, success: bool = True, **kwargs):
    """Função de conveniência para registrar performance"""
    get_metrics_collector().record_performance(operation, duration_ms, success, kwargs)

def get_dashboard_data() -> Dict[str, Any]:
    """Função de conveniência para obter dados do dashboard"""
    return get_monitoring_dashboard().get_dashboard_data()
