"""
OldNews FiscalAI - Sistema de Alertas de Performance
Monitora degradação de performance e envia alertas
"""

import time
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    # Fallback para versões mais antigas
    from email.MIMEText import MIMEText
    from email.MIMEMultipart import MIMEMultipart
import logging

from .validation_dataset import ValidationDataset
from .metrics_dashboard import MetricsDashboard


class PerformanceAlert:
    """
    Classe para representar um alerta de performance
    """
    
    def __init__(self, 
                 alert_type: str,
                 severity: str,
                 message: str,
                 metric_name: str,
                 current_value: float,
                 threshold_value: float,
                 timestamp: datetime = None):
        """
        Inicializa um alerta
        
        Args:
            alert_type: Tipo do alerta (performance, accuracy, availability)
            severity: Severidade (low, medium, high, critical)
            message: Mensagem do alerta
            metric_name: Nome da métrica
            current_value: Valor atual
            threshold_value: Valor do threshold
            timestamp: Timestamp do alerta
        """
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold_value = threshold_value
        self.timestamp = timestamp or datetime.now()
        self.resolved = False
        self.resolution_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte alerta para dicionário"""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None
        }
    
    def resolve(self):
        """Marca alerta como resolvido"""
        self.resolved = True
        self.resolution_time = datetime.now()


class PerformanceAlertManager:
    """
    Gerenciador de alertas de performance
    """
    
    def __init__(self, 
                 validation_dataset: ValidationDataset,
                 metrics_dashboard: MetricsDashboard,
                 config_file: str = "config/alerts.json"):
        """
        Inicializa o gerenciador de alertas
        
        Args:
            validation_dataset: Dataset de validação
            metrics_dashboard: Dashboard de métricas
            config_file: Arquivo de configuração
        """
        self.validation_dataset = validation_dataset
        self.metrics_dashboard = metrics_dashboard
        self.config_file = Path(config_file)
        
        # Carregar configuração
        self.config = self._load_config()
        
        # Histórico de alertas
        self.alerts_history = []
        self.active_alerts = []
        
        # Configurar logging
        self._setup_logging()
        
        # Callbacks para notificações
        self.notification_callbacks = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração de alertas"""
        default_config = {
            "thresholds": {
                "processing_time": 10.0,  # segundos
                "ncm_accuracy": 85.0,     # percentual
                "fraud_detection_rate": 90.0,  # percentual
                "chat_response_time": 3.0,  # segundos
                "system_availability": 99.0  # percentual
            },
            "alert_severity": {
                "processing_time": {
                    "warning": 8.0,
                    "critical": 12.0
                },
                "ncm_accuracy": {
                    "warning": 80.0,
                    "critical": 70.0
                },
                "fraud_detection_rate": {
                    "warning": 85.0,
                    "critical": 75.0
                },
                "chat_response_time": {
                    "warning": 2.5,
                    "critical": 4.0
                }
            },
            "notification": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "recipients": []
                },
                "webhook": {
                    "enabled": False,
                    "url": "",
                    "headers": {}
                }
            },
            "alert_cooldown": 300,  # 5 minutos em segundos
            "max_alerts_per_hour": 10
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Mesclar com configuração padrão
                default_config.update(config)
            except Exception as e:
                print(f"Erro ao carregar configuração: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Configura logging para alertas"""
        log_file = Path("logs/performance_alerts.log")
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def add_notification_callback(self, callback: Callable[[PerformanceAlert], None]):
        """
        Adiciona callback para notificações
        
        Args:
            callback: Função para ser chamada quando um alerta for gerado
        """
        self.notification_callbacks.append(callback)
    
    def check_performance_metrics(self) -> List[PerformanceAlert]:
        """
        Verifica métricas de performance e gera alertas
        
        Returns:
            Lista de alertas gerados
        """
        alerts = []
        
        # Verificar métricas atuais
        current_metrics = self.metrics_dashboard._calculate_current_metrics()
        validation_metrics = self.validation_dataset.calculate_accuracy_metrics()
        
        # Verificar tempo de processamento
        if current_metrics['avg_processing_time'] > 0:
            alert = self._check_processing_time(current_metrics['avg_processing_time'])
            if alert:
                alerts.append(alert)
        
        # Verificar acurácia NCM
        if validation_metrics['ncm_accuracy'] > 0:
            alert = self._check_ncm_accuracy(validation_metrics['ncm_accuracy'])
            if alert:
                alerts.append(alert)
        
        # Verificar taxa de detecção de fraudes
        if validation_metrics['fraud_detection_rate'] > 0:
            alert = self._check_fraud_detection_rate(validation_metrics['fraud_detection_rate'])
            if alert:
                alerts.append(alert)
        
        # Verificar tempo de resposta do chat
        if current_metrics.get('chat_response_time', 0) > 0:
            alert = self._check_chat_response_time(current_metrics['chat_response_time'])
            if alert:
                alerts.append(alert)
        
        # Processar alertas
        for alert in alerts:
            self._process_alert(alert)
        
        return alerts
    
    def _check_processing_time(self, current_time: float) -> Optional[PerformanceAlert]:
        """Verifica tempo de processamento"""
        thresholds = self.config['alert_severity']['processing_time']
        base_threshold = self.config['thresholds']['processing_time']
        
        if current_time >= thresholds['critical']:
            return PerformanceAlert(
                alert_type="performance",
                severity="critical",
                message=f"Tempo de processamento crítico: {current_time:.2f}s (threshold: {base_threshold}s)",
                metric_name="processing_time",
                current_value=current_time,
                threshold_value=base_threshold
            )
        elif current_time >= thresholds['warning']:
            return PerformanceAlert(
                alert_type="performance",
                severity="warning",
                message=f"Tempo de processamento alto: {current_time:.2f}s (threshold: {base_threshold}s)",
                metric_name="processing_time",
                current_value=current_time,
                threshold_value=base_threshold
            )
        
        return None
    
    def _check_ncm_accuracy(self, current_accuracy: float) -> Optional[PerformanceAlert]:
        """Verifica acurácia NCM"""
        thresholds = self.config['alert_severity']['ncm_accuracy']
        base_threshold = self.config['thresholds']['ncm_accuracy']
        
        if current_accuracy <= thresholds['critical']:
            return PerformanceAlert(
                alert_type="accuracy",
                severity="critical",
                message=f"Acurácia NCM crítica: {current_accuracy:.1f}% (threshold: {base_threshold}%)",
                metric_name="ncm_accuracy",
                current_value=current_accuracy,
                threshold_value=base_threshold
            )
        elif current_accuracy <= thresholds['warning']:
            return PerformanceAlert(
                alert_type="accuracy",
                severity="warning",
                message=f"Acurácia NCM baixa: {current_accuracy:.1f}% (threshold: {base_threshold}%)",
                metric_name="ncm_accuracy",
                current_value=current_accuracy,
                threshold_value=base_threshold
            )
        
        return None
    
    def _check_fraud_detection_rate(self, current_rate: float) -> Optional[PerformanceAlert]:
        """Verifica taxa de detecção de fraudes"""
        thresholds = self.config['alert_severity']['fraud_detection_rate']
        base_threshold = self.config['thresholds']['fraud_detection_rate']
        
        if current_rate <= thresholds['critical']:
            return PerformanceAlert(
                alert_type="accuracy",
                severity="critical",
                message=f"Taxa de detecção de fraudes crítica: {current_rate:.1f}% (threshold: {base_threshold}%)",
                metric_name="fraud_detection_rate",
                current_value=current_rate,
                threshold_value=base_threshold
            )
        elif current_rate <= thresholds['warning']:
            return PerformanceAlert(
                alert_type="accuracy",
                severity="warning",
                message=f"Taxa de detecção de fraudes baixa: {current_rate:.1f}% (threshold: {base_threshold}%)",
                metric_name="fraud_detection_rate",
                current_value=current_rate,
                threshold_value=base_threshold
            )
        
        return None
    
    def _check_chat_response_time(self, current_time: float) -> Optional[PerformanceAlert]:
        """Verifica tempo de resposta do chat"""
        thresholds = self.config['alert_severity']['chat_response_time']
        base_threshold = self.config['thresholds']['chat_response_time']
        
        if current_time >= thresholds['critical']:
            return PerformanceAlert(
                alert_type="performance",
                severity="critical",
                message=f"Tempo de resposta do chat crítico: {current_time:.2f}s (threshold: {base_threshold}s)",
                metric_name="chat_response_time",
                current_value=current_time,
                threshold_value=base_threshold
            )
        elif current_time >= thresholds['warning']:
            return PerformanceAlert(
                alert_type="performance",
                severity="warning",
                message=f"Tempo de resposta do chat alto: {current_time:.2f}s (threshold: {base_threshold}s)",
                metric_name="chat_response_time",
                current_value=current_time,
                threshold_value=base_threshold
            )
        
        return None
    
    def _process_alert(self, alert: PerformanceAlert):
        """
        Processa um alerta
        
        Args:
            alert: Alerta a ser processado
        """
        # Verificar cooldown
        if self._is_in_cooldown(alert):
            return
        
        # Verificar limite de alertas por hora
        if self._exceeds_hourly_limit():
            self.logger.warning("Limite de alertas por hora excedido")
            return
        
        # Adicionar ao histórico
        self.alerts_history.append(alert)
        
        # Adicionar aos alertas ativos se não resolvido
        if not alert.resolved:
            self.active_alerts.append(alert)
        
        # Log do alerta
        self.logger.warning(f"ALERTA {alert.severity.upper()}: {alert.message}")
        
        # Enviar notificações
        self._send_notifications(alert)
    
    def _is_in_cooldown(self, alert: PerformanceAlert) -> bool:
        """Verifica se o alerta está em cooldown"""
        cooldown_seconds = self.config['alert_cooldown']
        cutoff_time = datetime.now() - timedelta(seconds=cooldown_seconds)
        
        # Verificar se há alertas similares recentes
        for existing_alert in self.alerts_history:
            if (existing_alert.metric_name == alert.metric_name and
                existing_alert.severity == alert.severity and
                existing_alert.timestamp > cutoff_time):
                return True
        
        return False
    
    def _exceeds_hourly_limit(self) -> bool:
        """Verifica se excede o limite de alertas por hora"""
        max_alerts = self.config['max_alerts_per_hour']
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        recent_alerts = [
            alert for alert in self.alerts_history
            if alert.timestamp > cutoff_time
        ]
        
        return len(recent_alerts) >= max_alerts
    
    def _send_notifications(self, alert: PerformanceAlert):
        """Envia notificações do alerta"""
        # Callbacks personalizados
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Erro em callback de notificação: {e}")
        
        # Email (se configurado)
        if self.config['notification']['email']['enabled']:
            self._send_email_alert(alert)
        
        # Webhook (se configurado)
        if self.config['notification']['webhook']['enabled']:
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert: PerformanceAlert):
        """Envia alerta por email"""
        try:
            email_config = self.config['notification']['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['recipients'])
            msg['Subject'] = f"FiscalAI Alert - {alert.severity.upper()}: {alert.metric_name}"
            
            body = f"""
            Alerta de Performance - OldNews FiscalAI
            
            Tipo: {alert.alert_type}
            Severidade: {alert.severity}
            Métrica: {alert.metric_name}
            Valor Atual: {alert.current_value}
            Threshold: {alert.threshold_value}
            Mensagem: {alert.message}
            Timestamp: {alert.timestamp}
            
            Acesse o dashboard para mais detalhes.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email de alerta enviado para {email_config['recipients']}")
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar email de alerta: {e}")
    
    def _send_webhook_alert(self, alert: PerformanceAlert):
        """Envia alerta via webhook"""
        try:
            import requests
            
            webhook_config = self.config['notification']['webhook']
            
            payload = {
                "alert": alert.to_dict(),
                "system": "OldNews FiscalAI",
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config['headers'],
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Webhook de alerta enviado com sucesso")
            else:
                self.logger.error(f"Erro ao enviar webhook: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook de alerta: {e}")
    
    def resolve_alert(self, alert_id: str):
        """
        Resolve um alerta específico
        
        Args:
            alert_id: ID do alerta (timestamp + métrica)
        """
        for alert in self.active_alerts:
            if f"{alert.timestamp}_{alert.metric_name}" == alert_id:
                alert.resolve()
                self.active_alerts.remove(alert)
                self.logger.info(f"Alerta resolvido: {alert.message}")
                break
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Retorna alertas ativos"""
        return self.active_alerts.copy()
    
    def get_alerts_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """
        Retorna histórico de alertas
        
        Args:
            hours: Número de horas para buscar
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts_history
            if alert.timestamp > cutoff_time
        ]
    
    def generate_alert_report(self) -> str:
        """Gera relatório de alertas"""
        active_count = len(self.active_alerts)
        total_count = len(self.alerts_history)
        
        # Contar por severidade
        severity_counts = {}
        for alert in self.alerts_history:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
        
        report = f"""
# RELATÓRIO DE ALERTAS - FISCALAI MVP
=====================================

## Resumo
- **Alertas Ativos:** {active_count}
- **Total de Alertas (24h):** {total_count}

## Por Severidade
"""
        
        for severity, count in severity_counts.items():
            report += f"- **{severity.upper()}:** {count}\n"
        
        if active_count > 0:
            report += "\n## Alertas Ativos\n"
            for alert in self.active_alerts:
                report += f"- **{alert.severity.upper()}:** {alert.message}\n"
        
        return report
    
    def start_monitoring(self, interval_seconds: int = 60):
        """
        Inicia monitoramento contínuo
        
        Args:
            interval_seconds: Intervalo entre verificações
        """
        self.logger.info(f"Iniciando monitoramento com intervalo de {interval_seconds}s")
        
        while True:
            try:
                alerts = self.check_performance_metrics()
                if alerts:
                    self.logger.info(f"Verificação gerou {len(alerts)} alertas")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoramento interrompido pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"Erro no monitoramento: {e}")
                time.sleep(interval_seconds)


def create_alert_manager() -> PerformanceAlertManager:
    """
    Função utilitária para criar gerenciador de alertas
    """
    validation_dataset = ValidationDataset()
    metrics_dashboard = MetricsDashboard()
    
    return PerformanceAlertManager(validation_dataset, metrics_dashboard)


if __name__ == "__main__":
    # Teste do sistema de alertas
    alert_manager = create_alert_manager()
    
    # Adicionar callback de exemplo
    def log_alert(alert: PerformanceAlert):
        print(f"🚨 ALERTA: {alert.message}")
    
    alert_manager.add_notification_callback(log_alert)
    
    # Verificar métricas
    alerts = alert_manager.check_performance_metrics()
    
    if alerts:
        print(f"Gerados {len(alerts)} alertas")
        for alert in alerts:
            print(f"- {alert.severity.upper()}: {alert.message}")
    else:
        print("Nenhum alerta gerado")
    
    # Gerar relatório
    report = alert_manager.generate_alert_report()
    print(report)
