"""
OldNews FiscalAI - Exemplo de Uso da Nova Estrutura OOP
Demonstra como usar as classes base e interfaces refatoradas
"""

from typing import List, Dict, Any
import pandas as pd

from ..core.base_agent import BaseAgent
from ..core.base_detector import BaseDetector
from ..core.base_parser import BaseParser
from ..core.interfaces import IAgent, IDetector, IParser
from ..agents.agente2_classificador_refatorado import Agente2Classificador
from ..detectors.detector_subfaturamento_refatorado import DetectorSubfaturamento
from ..models import NFe, ItemNFe, ClassificacaoNCM, TipoFraude


class ExemploUsoOOP:
    """
    Exemplo de como usar a nova estrutura OOP
    """
    
    def __init__(self):
        """Inicializa o exemplo"""
        self.agentes = []
        self.detectores = []
        self.parsers = []
    
    def demonstrar_heranca_e_polimorfismo(self):
        """Demonstra herança e polimorfismo"""
        print("=== Demonstração de Herança e Polimorfismo ===\n")
        
        # 1. Criar agentes (todos herdam de BaseAgent)
        agente_classificador = Agente2Classificador(
            llm=None,  # Em produção, seria uma instância real do LLM
            confianca_minima=0.8
        )
        
        # 2. Demonstrar polimorfismo - todos implementam IAgent
        self.agentes.append(agente_classificador)
        
        # 3. Usar interface comum
        for agente in self.agentes:
            print(f"Agente: {agente.role}")
            print(f"Objetivo: {agente.goal}")
            print(f"Tipo: {type(agente).__name__}")
            print(f"Implementa IAgent: {isinstance(agente, IAgent)}")
            print()
    
    def demonstrar_encapsulamento(self):
        """Demonstra encapsulamento adequado"""
        print("=== Demonstração de Encapsulamento ===\n")
        
        # Criar detector
        detector = DetectorSubfaturamento(
            threshold_score_minimo=25,
            threshold_confianca_minima=0.6
        )
        
        # 1. Acesso controlado via propriedades
        print(f"Tipo de fraude: {detector.tipo_fraude}")
        print(f"Score mínimo: {detector.threshold_score_minimo}")
        print(f"Confiança mínima: {detector.threshold_confianca_minima}")
        
        # 2. Validação automática nos setters
        try:
            detector.threshold_score_minimo = 150  # Deve falhar
        except ValueError as e:
            print(f"Erro esperado: {e}")
        
        # 3. Configuração via método específico
        detector.configurar_thresholds(
            desvio_percentual=-25.0,
            z_score=-2.5,
            valor_alto=5000.0
        )
        
        print(f"Configurações: {detector._configuracoes}")
        print()
    
    def demonstrar_abstracao_e_interfaces(self):
        """Demonstra abstração e uso de interfaces"""
        print("=== Demonstração de Abstração e Interfaces ===\n")
        
        # 1. Usar interface comum para diferentes implementações
        detectores: List[IDetector] = [
            DetectorSubfaturamento(),
            # Outros detectores implementariam IDetector
        ]
        
        # 2. Polimorfismo - mesmo método, implementações diferentes
        for detector in detectores:
            print(f"Detector: {type(detector).__name__}")
            print(f"Tipo de fraude: {detector.tipo_fraude}")
            print(f"Implementa IDetector: {isinstance(detector, IDetector)}")
            print()
    
    def demonstrar_responsabilidade_unica(self):
        """Demonstra princípio da responsabilidade única"""
        print("=== Demonstração de Responsabilidade Única ===\n")
        
        # 1. Agente Classificador - responsabilidade única: classificar NCM
        agente = Agente2Classificador(llm=None)
        print(f"Agente Classificador:")
        print(f"- Responsabilidade: {agente.goal}")
        print(f"- Métodos específicos: executar(), validar_entrada()")
        print()
        
        # 2. Detector Subfaturamento - responsabilidade única: detectar subfaturamento
        detector = DetectorSubfaturamento()
        print(f"Detector Subfaturamento:")
        print(f"- Responsabilidade: Detectar {detector.tipo_fraude.value}")
        print(f"- Métodos específicos: detectar(), analisar_nfe()")
        print()
    
    def demonstrar_composicao_e_agregacao(self):
        """Demonstra composição e agregação"""
        print("=== Demonstração de Composição e Agregação ===\n")
        
        # 1. Composição - BaseAgent contém Agent do CrewAI
        agente = Agente2Classificador(llm=None)
        print(f"Agente contém:")
        print(f"- LLM: {agente.llm is not None}")
        print(f"- Agent CrewAI: {hasattr(agente, '_agent')}")
        print(f"- Logger: {hasattr(agente, '_logger')}")
        print()
        
        # 2. Agregação - Detector usa DataFrame externo
        detector = DetectorSubfaturamento()
        print(f"Detector usa:")
        print(f"- Base de preços: {detector.base_precos is not None}")
        print(f"- Histórico: {detector.historico is not None}")
        print()
    
    def demonstrar_tratamento_de_erros(self):
        """Demonstra tratamento de erros robusto"""
        print("=== Demonstração de Tratamento de Erros ===\n")
        
        agente = Agente2Classificador(llm=None)
        
        # 1. Validação de entrada
        try:
            # Dados inválidos
            resultado = agente.executar([])  # Lista vazia
        except ValueError as e:
            print(f"Erro de validação capturado: {e}")
        
        # 2. Validação de LLM
        try:
            agente_invalido = Agente2Classificador(llm=None)
            agente_invalido._llm = None  # Simular LLM inválido
            agente_invalido._executar_com_validacao([])
        except ValueError as e:
            print(f"Erro de LLM capturado: {e}")
        
        print()
    
    def demonstrar_cache_e_otimizacao(self):
        """Demonstra uso de cache e otimização"""
        print("=== Demonstração de Cache e Otimização ===\n")
        
        agente = Agente2Classificador(llm=None)
        
        # 1. Cache de classificações
        print(f"Cache inicial: {agente.obter_estatisticas_cache()}")
        
        # 2. Limpar cache
        agente.limpar_cache()
        print(f"Após limpar: {agente.obter_estatisticas_cache()}")
        
        print()
    
    def executar_todos_exemplos(self):
        """Executa todos os exemplos"""
        print("🚀 Exemplos de Uso da Nova Estrutura OOP\n")
        print("=" * 50)
        
        self.demonstrar_heranca_e_polimorfismo()
        self.demonstrar_encapsulamento()
        self.demonstrar_abstracao_e_interfaces()
        self.demonstrar_responsabilidade_unica()
        self.demonstrar_composicao_e_agregacao()
        self.demonstrar_tratamento_de_erros()
        self.demonstrar_cache_e_otimizacao()
        
        print("✅ Todos os exemplos executados com sucesso!")


def main():
    """Função principal para executar os exemplos"""
    exemplo = ExemploUsoOOP()
    exemplo.executar_todos_exemplos()


if __name__ == "__main__":
    main()
