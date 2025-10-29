"""
FiscalAI MVP - Dataset de Validação
Cria e gerencia dataset para validação de acurácia das métricas
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import os

from ..models.schemas import NFe, ItemNFe, ClassificacaoNCM, ResultadoAnalise


class ValidationDataset:
    """
    Classe para criar e gerenciar dataset de validação
    """
    
    def __init__(self, dataset_path: str = "data/validation/"):
        """
        Inicializa o dataset de validação
        
        Args:
            dataset_path: Caminho para salvar o dataset
        """
        self.dataset_path = Path(dataset_path)
        self.dataset_path.mkdir(parents=True, exist_ok=True)
        
        # Arquivos do dataset
        self.nfe_samples_file = self.dataset_path / "nfe_samples.json"
        self.ncm_classifications_file = self.dataset_path / "ncm_classifications.json"
        self.fraud_detections_file = self.dataset_path / "fraud_detections.json"
        self.performance_metrics_file = self.dataset_path / "performance_metrics.json"
        
        # Inicializar datasets vazios se não existirem
        self._initialize_datasets()
    
    def _initialize_datasets(self):
        """Inicializa datasets vazios se não existirem"""
        datasets = [
            (self.nfe_samples_file, []),
            (self.ncm_classifications_file, []),
            (self.fraud_detections_file, []),
            (self.performance_metrics_file, [])
        ]
        
        for file_path, default_data in datasets:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2, ensure_ascii=False)
    
    def add_nfe_sample(self, 
                      nfe: NFe, 
                      expected_classifications: Dict[int, str],
                      expected_frauds: List[Dict[str, Any]],
                      processing_time: float,
                      actual_classifications: Optional[Dict[int, ClassificacaoNCM]] = None,
                      actual_result: Optional[ResultadoAnalise] = None):
        """
        Adiciona uma amostra de NF-e ao dataset de validação
        
        Args:
            nfe: NF-e processada
            expected_classifications: NCMs esperados {item_id: ncm}
            expected_frauds: Lista de fraudes esperadas
            processing_time: Tempo de processamento real
            actual_classifications: Classificações reais (opcional)
            actual_result: Resultado real da análise (opcional)
        """
        # Dados da NF-e
        nfe_data = {
            "timestamp": datetime.now().isoformat(),
            "chave_acesso": nfe.chave_acesso,
            "numero": nfe.numero,
            "cnpj_emitente": nfe.cnpj_emitente,
            "valor_total": nfe.valor_total,
            "num_itens": len(nfe.itens),
            "itens": [
                {
                    "numero_item": item.numero_item,
                    "descricao": item.descricao,
                    "ncm_declarado": item.ncm_declarado,
                    "quantidade": item.quantidade,
                    "valor_unitario": item.valor_unitario
                }
                for item in nfe.itens
            ],
            "expected_classifications": expected_classifications,
            "expected_frauds": expected_frauds,
            "processing_time": processing_time,
            "actual_classifications": self._serialize_classifications(actual_classifications),
            "actual_result": self._serialize_result(actual_result)
        }
        
        # Salvar amostra
        self._append_to_file(self.nfe_samples_file, nfe_data)
        
        # Adicionar métricas de performance
        if actual_result:
            self._add_performance_metrics(nfe_data, actual_result)
    
    def _serialize_classifications(self, classifications: Optional[Dict[int, ClassificacaoNCM]]) -> Optional[Dict]:
        """Serializa classificações para JSON"""
        if not classifications:
            return None
        
        return {
            str(item_id): {
                "ncm_predito": classif.ncm_predito,
                "ncm_declarado": classif.ncm_declarado,
                "confianca": classif.confianca,
                "justificativa": classif.justificativa,
                "diverge": classif.diverge
            }
            for item_id, classif in classifications.items()
        }
    
    def _serialize_result(self, result: Optional[ResultadoAnalise]) -> Optional[Dict]:
        """Serializa resultado da análise para JSON"""
        if not result:
            return None
        
        return {
            "score_risco_geral": result.score_risco_geral,
            "nivel_risco": result.nivel_risco.value if result.nivel_risco else None,
            "fraudes_detectadas": len(result.fraudes_detectadas),
            "itens_suspeitos": result.itens_suspeitos,
            "tempo_processamento_segundos": result.tempo_processamento_segundos
        }
    
    def _add_performance_metrics(self, nfe_data: Dict, actual_result: ResultadoAnalise):
        """Adiciona métricas de performance"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "chave_acesso": nfe_data["chave_acesso"],
            "processing_time": nfe_data["processing_time"],
            "num_itens": nfe_data["num_itens"],
            "score_risco": actual_result.score_risco_geral,
            "fraudes_detectadas": len(actual_result.fraudes_detectadas),
            "tempo_por_item": nfe_data["processing_time"] / nfe_data["num_itens"] if nfe_data["num_itens"] > 0 else 0
        }
        
        self._append_to_file(self.performance_metrics_file, metrics)
    
    def _append_to_file(self, file_path: Path, data: Dict):
        """Adiciona dados ao arquivo JSON"""
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        existing_data.append(data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    def calculate_accuracy_metrics(self) -> Dict[str, float]:
        """
        Calcula métricas de acurácia do dataset
        
        Returns:
            Dict com métricas de acurácia
        """
        # Carregar dados
        with open(self.nfe_samples_file, 'r', encoding='utf-8') as f:
            samples = json.load(f)
        
        if not samples:
            return {
                "ncm_accuracy": 0.0,
                "fraud_detection_rate": 0.0,
                "avg_processing_time": 0.0,
                "total_samples": 0
            }
        
        # Calcular acurácia de classificação NCM
        ncm_correct = 0
        ncm_total = 0
        
        # Calcular taxa de detecção de fraudes
        fraud_detected = 0
        fraud_expected = 0
        
        # Calcular tempo médio de processamento
        processing_times = []
        
        for sample in samples:
            # Acurácia NCM
            if sample.get("actual_classifications") and sample.get("expected_classifications"):
                for item_id, expected_ncm in sample["expected_classifications"].items():
                    actual_classif = sample["actual_classifications"].get(item_id)
                    if actual_classif:
                        ncm_total += 1
                        if actual_classif["ncm_predito"] == expected_ncm:
                            ncm_correct += 1
            
            # Detecção de fraudes
            expected_frauds = len(sample.get("expected_frauds", []))
            actual_frauds = sample.get("actual_result", {}).get("fraudes_detectadas", 0)
            
            fraud_expected += expected_frauds
            if actual_frauds > 0 and expected_frauds > 0:
                fraud_detected += min(actual_frauds, expected_frauds)
            
            # Tempo de processamento
            processing_times.append(sample.get("processing_time", 0))
        
        # Calcular métricas finais
        ncm_accuracy = (ncm_correct / ncm_total) * 100 if ncm_total > 0 else 0.0
        fraud_detection_rate = (fraud_detected / fraud_expected) * 100 if fraud_expected > 0 else 0.0
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        
        return {
            "ncm_accuracy": round(ncm_accuracy, 2),
            "fraud_detection_rate": round(fraud_detection_rate, 2),
            "avg_processing_time": round(avg_processing_time, 2),
            "total_samples": len(samples),
            "ncm_total_classifications": ncm_total,
            "fraud_expected_total": fraud_expected
        }
    
    def generate_validation_report(self) -> str:
        """
        Gera relatório de validação
        
        Returns:
            Relatório em formato texto
        """
        metrics = self.calculate_accuracy_metrics()
        
        report = f"""
# RELATÓRIO DE VALIDAÇÃO - FISCALAI MVP
========================================

## Métricas de Acurácia
- **Acurácia de Classificação NCM:** {metrics['ncm_accuracy']}%
- **Taxa de Detecção de Fraudes:** {metrics['fraud_detection_rate']}%
- **Tempo Médio de Processamento:** {metrics['avg_processing_time']}s

## Estatísticas do Dataset
- **Total de Amostras:** {metrics['total_samples']}
- **Total de Classificações NCM:** {metrics['ncm_total_classifications']}
- **Total de Fraudes Esperadas:** {metrics['fraud_expected_total']}

## Conformidade com Metas MVP
- **NCM Accuracy ≥ 85%:** {'✅ CONFORME' if metrics['ncm_accuracy'] >= 85 else '❌ NÃO CONFORME'}
- **Fraud Detection ≥ 90%:** {'✅ CONFORME' if metrics['fraud_detection_rate'] >= 90 else '❌ NÃO CONFORME'}
- **Processing Time < 10s:** {'✅ CONFORME' if metrics['avg_processing_time'] < 10 else '❌ NÃO CONFORME'}

## Recomendações
"""
        
        if metrics['ncm_accuracy'] < 85:
            report += "- Melhorar algoritmo de classificação NCM\n"
        
        if metrics['fraud_detection_rate'] < 90:
            report += "- Ajustar thresholds dos detectores de fraude\n"
        
        if metrics['avg_processing_time'] >= 10:
            report += "- Otimizar performance do processamento\n"
        
        if all([
            metrics['ncm_accuracy'] >= 85,
            metrics['fraud_detection_rate'] >= 90,
            metrics['avg_processing_time'] < 10
        ]):
            report += "- ✅ Todas as métricas estão conformes!\n"
        
        return report
    
    def export_to_csv(self, output_path: str = "data/validation/validation_report.csv"):
        """
        Exporta métricas para CSV
        
        Args:
            output_path: Caminho do arquivo CSV
        """
        metrics = self.calculate_accuracy_metrics()
        
        # Criar DataFrame
        df = pd.DataFrame([{
            "timestamp": datetime.now().isoformat(),
            "ncm_accuracy": metrics['ncm_accuracy'],
            "fraud_detection_rate": metrics['fraud_detection_rate'],
            "avg_processing_time": metrics['avg_processing_time'],
            "total_samples": metrics['total_samples'],
            "ncm_total_classifications": metrics['ncm_total_classifications'],
            "fraud_expected_total": metrics['fraud_expected_total']
        }])
        
        # Salvar CSV
        df.to_csv(output_path, index=False)
        print(f"Relatório de validação exportado para: {output_path}")
    
    def create_sample_data(self):
        """
        Cria dados de exemplo para teste
        """
        # Exemplo de NF-e
        sample_nfe = NFe(
            chave_acesso="12345678901234567890123456789012345678901234",
            numero="12345",
            serie="1",
            data_emissao=datetime.now(),
            cnpj_emitente="12345678000195",
            razao_social_emitente="Empresa Exemplo LTDA",
            cnpj_destinatario="98765432000123",
            razao_social_destinatario="Cliente Exemplo LTDA",
            valor_total=1000.00,
            valor_produtos=1000.00,
            itens=[
                ItemNFe(
                    numero_item=1,
                    descricao="Produto de exemplo",
                    ncm_declarado="12345678",
                    quantidade=1,
                    valor_unitario=1000.00
                )
            ]
        )
        
        # Adicionar amostra
        self.add_nfe_sample(
            nfe=sample_nfe,
            expected_classifications={1: "12345678"},
            expected_frauds=[],
            processing_time=2.5
        )
        
        print("Dados de exemplo criados com sucesso!")


def create_validation_dataset():
    """
    Função utilitária para criar dataset de validação
    """
    dataset = ValidationDataset()
    dataset.create_sample_data()
    
    # Gerar relatório
    report = dataset.generate_validation_report()
    print(report)
    
    # Exportar CSV
    dataset.export_to_csv()
    
    return dataset


if __name__ == "__main__":
    create_validation_dataset()
