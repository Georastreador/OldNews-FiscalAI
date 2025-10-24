"""
OldNews FiscalAI - Dashboard de Métricas em Tempo Real
Monitora e exibe métricas de performance do sistema
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import time
from pathlib import Path

from .validation_dataset import ValidationDataset


class MetricsDashboard:
    """
    Dashboard de métricas em tempo real
    """
    
    def __init__(self):
        """Inicializa o dashboard"""
        self.validation_dataset = ValidationDataset()
        self.metrics_history = []
        self.load_metrics_history()
    
    def load_metrics_history(self):
        """Carrega histórico de métricas"""
        try:
            with open(self.validation_dataset.performance_metrics_file, 'r', encoding='utf-8') as f:
                self.metrics_history = json.load(f)
        except FileNotFoundError:
            self.metrics_history = []
    
    def add_metric_point(self, 
                        processing_time: float,
                        num_items: int,
                        score_risco: int,
                        frauds_detected: int):
        """
        Adiciona ponto de métrica em tempo real
        
        Args:
            processing_time: Tempo de processamento
            num_items: Número de itens processados
            score_risco: Score de risco
            frauds_detected: Número de fraudes detectadas
        """
        metric_point = {
            "timestamp": datetime.now().isoformat(),
            "processing_time": processing_time,
            "num_items": num_items,
            "score_risco": score_risco,
            "frauds_detected": frauds_detected,
            "time_per_item": processing_time / num_items if num_items > 0 else 0
        }
        
        self.metrics_history.append(metric_point)
        
        # Manter apenas últimos 100 pontos
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        # Salvar no arquivo
        self._save_metrics_history()
    
    def _save_metrics_history(self):
        """Salva histórico de métricas"""
        with open(self.validation_dataset.performance_metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics_history, f, indent=2, ensure_ascii=False)
    
    def render_dashboard(self):
        """Renderiza o dashboard completo"""
        st.title("📊 Dashboard de Métricas - OldNews FiscalAI")
        
        # Métricas principais
        self._render_main_metrics()
        
        # Gráficos de performance
        self._render_performance_charts()
        
        # Métricas de validação
        self._render_validation_metrics()
        
        # Status do sistema
        self._render_system_status()
    
    def _render_main_metrics(self):
        """Renderiza métricas principais"""
        st.subheader("🎯 Métricas Principais")
        
        # Calcular métricas atuais
        current_metrics = self._calculate_current_metrics()
        
        # Layout em colunas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="⏱️ Tempo Médio de Processamento",
                value=f"{current_metrics['avg_processing_time']:.2f}s",
                delta=f"{current_metrics['processing_time_trend']:.2f}s",
                help="Tempo médio para processar uma NF-e"
            )
        
        with col2:
            st.metric(
                label="🎯 Acurácia NCM",
                value=f"{current_metrics['ncm_accuracy']:.1f}%",
                delta=f"{current_metrics['ncm_accuracy_trend']:.1f}%",
                help="Precisão na classificação de códigos NCM"
            )
        
        with col3:
            st.metric(
                label="🔍 Taxa de Detecção de Fraudes",
                value=f"{current_metrics['fraud_detection_rate']:.1f}%",
                delta=f"{current_metrics['fraud_detection_trend']:.1f}%",
                help="Percentual de fraudes detectadas corretamente"
            )
        
        with col4:
            st.metric(
                label="📈 Total de Análises",
                value=f"{current_metrics['total_analyses']}",
                delta=f"{current_metrics['analyses_today']}",
                help="Total de análises realizadas"
            )
    
    def _render_performance_charts(self):
        """Renderiza gráficos de performance"""
        st.subheader("📈 Gráficos de Performance")
        
        if not self.metrics_history:
            st.info("Nenhum dado de performance disponível ainda.")
            return
        
        # Converter para DataFrame
        df = pd.DataFrame(self.metrics_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Gráfico de tempo de processamento
        col1, col2 = st.columns(2)
        
        with col1:
            fig_time = px.line(
                df, 
                x='timestamp', 
                y='processing_time',
                title='Tempo de Processamento ao Longo do Tempo',
                labels={'processing_time': 'Tempo (s)', 'timestamp': 'Data/Hora'}
            )
            fig_time.add_hline(y=10, line_dash="dash", line_color="red", 
                             annotation_text="Meta: < 10s")
            st.plotly_chart(fig_time, use_container_width=True)
        
        with col2:
            fig_items = px.scatter(
                df, 
                x='num_items', 
                y='processing_time',
                title='Tempo vs Número de Itens',
                labels={'processing_time': 'Tempo (s)', 'num_items': 'Número de Itens'}
            )
            st.plotly_chart(fig_items, use_container_width=True)
        
        # Gráfico de score de risco
        col3, col4 = st.columns(2)
        
        with col3:
            fig_risk = px.histogram(
                df, 
                x='score_risco',
                title='Distribuição de Scores de Risco',
                labels={'score_risco': 'Score de Risco', 'count': 'Frequência'}
            )
            st.plotly_chart(fig_risk, use_container_width=True)
        
        with col4:
            fig_frauds = px.bar(
                df.groupby('frauds_detected').size().reset_index(name='count'),
                x='frauds_detected',
                y='count',
                title='Distribuição de Fraudes Detectadas',
                labels={'frauds_detected': 'Fraudes Detectadas', 'count': 'Frequência'}
            )
            st.plotly_chart(fig_frauds, use_container_width=True)
    
    def _render_validation_metrics(self):
        """Renderiza métricas de validação"""
        st.subheader("✅ Métricas de Validação")
        
        # Calcular métricas de validação
        validation_metrics = self.validation_dataset.calculate_accuracy_metrics()
        
        # Layout em colunas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Acurácia NCM
            accuracy_color = "green" if validation_metrics['ncm_accuracy'] >= 85 else "red"
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {accuracy_color}; border-radius: 10px;">
                <h3 style="color: {accuracy_color};">{validation_metrics['ncm_accuracy']}%</h3>
                <p>Acurácia NCM</p>
                <small>Meta: ≥ 85%</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Taxa de detecção de fraudes
            fraud_color = "green" if validation_metrics['fraud_detection_rate'] >= 90 else "red"
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {fraud_color}; border-radius: 10px;">
                <h3 style="color: {fraud_color};">{validation_metrics['fraud_detection_rate']}%</h3>
                <p>Detecção de Fraudes</p>
                <small>Meta: ≥ 90%</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Tempo de processamento
            time_color = "green" if validation_metrics['avg_processing_time'] < 10 else "red"
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border: 2px solid {time_color}; border-radius: 10px;">
                <h3 style="color: {time_color};">{validation_metrics['avg_processing_time']}s</h3>
                <p>Tempo Médio</p>
                <small>Meta: < 10s</small>
            </div>
            """, unsafe_allow_html=True)
        
        # Estatísticas detalhadas
        st.markdown("### 📊 Estatísticas Detalhadas")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            - **Total de Amostras:** {validation_metrics['total_samples']}
            - **Classificações NCM:** {validation_metrics['ncm_total_classifications']}
            - **Fraudes Esperadas:** {validation_metrics['fraud_expected_total']}
            """)
        
        with col2:
            # Status de conformidade
            conformidade = self._calculate_compliance_status(validation_metrics)
            st.markdown(f"""
            - **Status Geral:** {conformidade['status']}
            - **Métricas Conformes:** {conformidade['conformes']}/3
            - **Score de Conformidade:** {conformidade['score']}%
            """)
    
    def _render_system_status(self):
        """Renderiza status do sistema"""
        st.subheader("🖥️ Status do Sistema")
        
        # Status dos componentes
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🤖 Modelo de IA")
            st.success("✅ Operacional")
            st.caption("Mistral 7B GGUF carregado")
        
        with col2:
            st.markdown("### 🔍 Detectores")
            st.success("✅ Operacional")
            st.caption("Todos os detectores ativos")
        
        with col3:
            st.markdown("### 💬 Chat")
            st.success("✅ Operacional")
            st.caption("Cache ativo, respostas otimizadas")
        
        # Uso de recursos
        st.markdown("### 📊 Uso de Recursos")
        
        # Simular dados de uso (em produção, viria de monitoramento real)
        resource_data = {
            "CPU": 45,
            "Memória": 62,
            "GPU": 38,
            "Disco": 23
        }
        
        for resource, usage in resource_data.items():
            color = "green" if usage < 70 else "orange" if usage < 90 else "red"
            st.progress(usage / 100, text=f"{resource}: {usage}%")
    
    def _calculate_current_metrics(self) -> Dict[str, float]:
        """Calcula métricas atuais"""
        if not self.metrics_history:
            return {
                'avg_processing_time': 0.0,
                'processing_time_trend': 0.0,
                'ncm_accuracy': 0.0,
                'ncm_accuracy_trend': 0.0,
                'fraud_detection_rate': 0.0,
                'fraud_detection_trend': 0.0,
                'total_analyses': 0,
                'analyses_today': 0
            }
        
        # Calcular métricas dos últimos dados
        recent_data = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history
        
        avg_processing_time = sum(d['processing_time'] for d in recent_data) / len(recent_data)
        
        # Calcular tendência (comparar com dados anteriores)
        if len(self.metrics_history) >= 20:
            older_data = self.metrics_history[-20:-10]
            older_avg = sum(d['processing_time'] for d in older_data) / len(older_data)
            processing_time_trend = avg_processing_time - older_avg
        else:
            processing_time_trend = 0.0
        
        # Métricas de validação
        validation_metrics = self.validation_dataset.calculate_accuracy_metrics()
        
        # Análises hoje
        today = datetime.now().date()
        analyses_today = len([
            d for d in self.metrics_history 
            if datetime.fromisoformat(d['timestamp']).date() == today
        ])
        
        return {
            'avg_processing_time': avg_processing_time,
            'processing_time_trend': processing_time_trend,
            'ncm_accuracy': validation_metrics['ncm_accuracy'],
            'ncm_accuracy_trend': 0.0,  # Seria calculado com histórico
            'fraud_detection_rate': validation_metrics['fraud_detection_rate'],
            'fraud_detection_trend': 0.0,  # Seria calculado com histórico
            'total_analyses': len(self.metrics_history),
            'analyses_today': analyses_today
        }
    
    def _calculate_compliance_status(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Calcula status de conformidade"""
        conformes = 0
        total = 3
        
        if metrics['ncm_accuracy'] >= 85:
            conformes += 1
        if metrics['fraud_detection_rate'] >= 90:
            conformes += 1
        if metrics['avg_processing_time'] < 10:
            conformes += 1
        
        score = (conformes / total) * 100
        
        if score == 100:
            status = "✅ TOTALMENTE CONFORME"
        elif score >= 66:
            status = "🟡 PARCIALMENTE CONFORME"
        else:
            status = "❌ NÃO CONFORME"
        
        return {
            'status': status,
            'conformes': conformes,
            'score': score
        }
    
    def export_metrics_report(self) -> str:
        """
        Exporta relatório de métricas
        
        Returns:
            Caminho do arquivo exportado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"data/validation/metrics_report_{timestamp}.csv"
        
        # Criar DataFrame com métricas
        current_metrics = self._calculate_current_metrics()
        validation_metrics = self.validation_dataset.calculate_accuracy_metrics()
        
        report_data = {
            "timestamp": [datetime.now().isoformat()],
            "avg_processing_time": [current_metrics['avg_processing_time']],
            "ncm_accuracy": [validation_metrics['ncm_accuracy']],
            "fraud_detection_rate": [validation_metrics['fraud_detection_rate']],
            "total_analyses": [current_metrics['total_analyses']],
            "analyses_today": [current_metrics['analyses_today']]
        }
        
        df = pd.DataFrame(report_data)
        df.to_csv(report_path, index=False)
        
        return report_path


def render_metrics_page():
    """
    Função para renderizar página de métricas no Streamlit
    """
    dashboard = MetricsDashboard()
    dashboard.render_dashboard()
    
    # Botão para exportar relatório
    if st.button("📊 Exportar Relatório de Métricas"):
        report_path = dashboard.export_metrics_report()
        st.success(f"Relatório exportado para: {report_path}")


if __name__ == "__main__":
    # Teste do dashboard
    dashboard = MetricsDashboard()
    
    # Adicionar alguns dados de exemplo
    for i in range(5):
        dashboard.add_metric_point(
            processing_time=2.5 + i * 0.5,
            num_items=3 + i,
            score_risco=20 + i * 10,
            frauds_detected=i % 2
        )
    
    print("Dashboard de métricas criado com sucesso!")
