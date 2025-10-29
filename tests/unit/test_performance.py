"""
FiscalAI MVP - Testes de Performance
Testes automatizados para validar métricas de performance
"""

import unittest
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import json

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.utils.model_manager import get_model_manager
from src.agents import Agente1Extrator, Agente2Classificador, Agente3Validador, Agente5Interface
from src.detectors import OrquestradorDeteccaoFraudes
from src.models import NFe, ItemNFe
from src.utils.validation_dataset import ValidationDataset
from src.utils.metrics_dashboard import MetricsDashboard


class PerformanceTestSuite(unittest.TestCase):
    """
    Suite de testes de performance
    """
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial para todos os testes"""
        print("🚀 Iniciando Testes de Performance...")
        
        # Inicializar componentes
        cls.model_manager = get_model_manager()
        cls.llm = cls.model_manager.get_llm('mistral-7b-gguf')
        
        # Criar agentes
        cls.agente1 = Agente1Extrator(cls.llm)
        cls.agente2 = Agente2Classificador(cls.llm)
        cls.agente3 = Agente3Validador(cls.llm)
        cls.agente5 = Agente5Interface(cls.llm)
        
        # Criar orquestrador
        cls.orquestrador = OrquestradorDeteccaoFraudes()
        
        # Dataset de validação
        cls.validation_dataset = ValidationDataset()
        
        # Dashboard de métricas
        cls.metrics_dashboard = MetricsDashboard()
        
        print("✅ Componentes inicializados com sucesso!")
    
    def test_model_loading_time(self):
        """Testa tempo de carregamento do modelo"""
        print("\n🤖 Testando tempo de carregamento do modelo...")
        
        start_time = time.time()
        llm = self.model_manager.get_llm('mistral-7b-gguf')
        load_time = time.time() - start_time
        
        print(f"⏱️ Tempo de carregamento: {load_time:.2f} segundos")
        
        # Verificar se o modelo carregou corretamente
        self.assertIsNotNone(llm, "Modelo deve carregar sem erros")
        
        # Tempo deve ser razoável (menos de 10 segundos para carregamento inicial)
        self.assertLess(load_time, 10.0, f"Tempo de carregamento muito alto: {load_time:.2f}s")
        
        print("✅ Teste de carregamento do modelo passou!")
    
    def test_chat_response_time(self):
        """Testa tempo de resposta do chat"""
        print("\n💬 Testando tempo de resposta do chat...")
        
        # Criar relatório de exemplo
        from src.models.schemas import RelatorioFiscal, ResultadoAnalise, NivelRisco
        from datetime import datetime
        
        resultado = ResultadoAnalise(
            chave_acesso="12345678901234567890123456789012345678901234",
            score_risco_geral=25,
            nivel_risco=NivelRisco.BAIXO,
            fraudes_detectadas=[],
            itens_suspeitos=[],
            acoes_recomendadas=[],
            timestamp_analise=datetime.now(),
            tempo_processamento_segundos=2.5
        )
        
        relatorio = RelatorioFiscal(
            resultado_analise=resultado,
            resumo_executivo="NF-e analisada com sucesso",
            detalhes_tecnicos="Análise completa realizada",
            recomendacoes="Aprovar NF-e"
        )
        
        # Carregar relatório no agente
        self.agente5.carregar_relatorio(relatorio)
        
        # Testar múltiplas perguntas
        perguntas_teste = [
            "Qual é o score de risco desta NF-e?",
            "Existem fraudes detectadas?",
            "Posso aprovar esta NF-e?",
            "Explique o resultado da análise"
        ]
        
        tempos_resposta = []
        
        for pergunta in perguntas_teste:
            start_time = time.time()
            resposta = self.agente5.conversar(pergunta)
            response_time = time.time() - start_time
            
            tempos_resposta.append(response_time)
            print(f"  📝 Pergunta: {pergunta[:30]}...")
            print(f"  ⏱️ Tempo: {response_time:.2f}s")
            print(f"  📄 Resposta: {resposta[:50]}...")
            
            # Verificar se a resposta não está vazia
            self.assertIsNotNone(resposta, "Resposta não deve ser None")
            self.assertGreater(len(resposta), 0, "Resposta não deve estar vazia")
        
        # Calcular tempo médio
        tempo_medio = sum(tempos_resposta) / len(tempos_resposta)
        print(f"\n📊 Tempo médio de resposta: {tempo_medio:.2f} segundos")
        
        # Verificar se atende à meta (< 3 segundos)
        self.assertLess(tempo_medio, 3.0, f"Tempo médio de resposta muito alto: {tempo_medio:.2f}s")
        
        print("✅ Teste de tempo de resposta do chat passou!")
    
    def test_nfe_processing_time(self):
        """Testa tempo de processamento de NF-e"""
        print("\n📄 Testando tempo de processamento de NF-e...")
        
        # Criar NF-e de exemplo
        nfe = NFe(
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
                    descricao="Produto de exemplo para teste",
                    ncm_declarado="12345678",
                    quantidade=1,
                    valor_unitario=1000.00
                ),
                ItemNFe(
                    numero_item=2,
                    descricao="Outro produto de exemplo",
                    ncm_declarado="87654321",
                    quantidade=2,
                    valor_unitario=500.00
                )
            ]
        )
        
        # Testar processamento completo
        start_time = time.time()
        
        # Simular classificação NCM
        classificacoes = {}
        for item in nfe.itens:
            classificacoes[item.numero_item] = {
                "ncm_predito": item.ncm_declarado,
                "confianca": 0.95
            }
        
        # Executar análise
        resultado = self.orquestrador.analisar_nfe(nfe, classificacoes)
        
        processing_time = time.time() - start_time
        
        print(f"⏱️ Tempo de processamento: {processing_time:.2f} segundos")
        print(f"📊 Score de risco: {resultado.score_risco_geral}")
        print(f"🔍 Fraudes detectadas: {len(resultado.fraudes_detectadas)}")
        
        # Verificar se atende à meta (< 10 segundos)
        self.assertLess(processing_time, 10.0, f"Tempo de processamento muito alto: {processing_time:.2f}s")
        
        # Verificar se o resultado foi gerado
        self.assertIsNotNone(resultado, "Resultado da análise deve ser gerado")
        self.assertIsNotNone(resultado.score_risco_geral, "Score de risco deve ser calculado")
        
        print("✅ Teste de tempo de processamento de NF-e passou!")
    
    def test_cache_performance(self):
        """Testa performance do cache do chat"""
        print("\n💾 Testando performance do cache...")
        
        # Criar relatório de exemplo
        from src.models.schemas import RelatorioFiscal, ResultadoAnalise, NivelRisco
        from datetime import datetime
        
        resultado = ResultadoAnalise(
            chave_acesso="12345678901234567890123456789012345678901234",
            score_risco_geral=25,
            nivel_risco=NivelRisco.BAIXO,
            fraudes_detectadas=[],
            itens_suspeitos=[],
            acoes_recomendadas=[],
            timestamp_analise=datetime.now(),
            tempo_processamento_segundos=2.5
        )
        
        relatorio = RelatorioFiscal(
            resultado_analise=resultado,
            resumo_executivo="NF-e analisada com sucesso",
            detalhes_tecnicos="Análise completa realizada",
            recomendacoes="Aprovar NF-e"
        )
        
        self.agente5.carregar_relatorio(relatorio)
        
        # Primeira pergunta (sem cache)
        pergunta = "Qual é o score de risco desta NF-e?"
        
        start_time = time.time()
        resposta1 = self.agente5.conversar(pergunta)
        tempo_sem_cache = time.time() - start_time
        
        # Segunda pergunta (com cache)
        start_time = time.time()
        resposta2 = self.agente5.conversar(pergunta)
        tempo_com_cache = time.time() - start_time
        
        print(f"⏱️ Tempo sem cache: {tempo_sem_cache:.2f}s")
        print(f"⏱️ Tempo com cache: {tempo_com_cache:.2f}s")
        print(f"📈 Melhoria: {((tempo_sem_cache - tempo_com_cache) / tempo_sem_cache * 100):.1f}%")
        
        # Verificar se as respostas são iguais
        self.assertEqual(resposta1, resposta2, "Respostas com e sem cache devem ser iguais")
        
        # Verificar se o cache melhorou a performance
        self.assertLess(tempo_com_cache, tempo_sem_cache, "Cache deve melhorar a performance")
        
        # Verificar estatísticas do cache
        stats = self.agente5.obter_estatisticas_cache()
        print(f"📊 Estatísticas do cache: {stats}")
        
        self.assertGreater(stats['total_entradas'], 0, "Cache deve ter entradas")
        
        print("✅ Teste de performance do cache passou!")
    
    def test_validation_dataset_performance(self):
        """Testa performance do dataset de validação"""
        print("\n📊 Testando performance do dataset de validação...")
        
        # Criar dados de exemplo
        nfe = NFe(
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
        
        # Testar adição de amostra
        start_time = time.time()
        
        self.validation_dataset.add_nfe_sample(
            nfe=nfe,
            expected_classifications={1: "12345678"},
            expected_frauds=[],
            processing_time=2.5
        )
        
        add_time = time.time() - start_time
        
        # Testar cálculo de métricas
        start_time = time.time()
        metrics = self.validation_dataset.calculate_accuracy_metrics()
        metrics_time = time.time() - start_time
        
        print(f"⏱️ Tempo para adicionar amostra: {add_time:.3f}s")
        print(f"⏱️ Tempo para calcular métricas: {metrics_time:.3f}s")
        print(f"📊 Métricas calculadas: {metrics}")
        
        # Verificar se as operações são rápidas
        self.assertLess(add_time, 1.0, "Adição de amostra deve ser rápida")
        self.assertLess(metrics_time, 1.0, "Cálculo de métricas deve ser rápido")
        
        # Verificar se as métricas foram calculadas
        self.assertIsInstance(metrics, dict, "Métricas devem ser um dicionário")
        self.assertIn('ncm_accuracy', metrics, "Métricas devem incluir acurácia NCM")
        
        print("✅ Teste de performance do dataset de validação passou!")
    
    def test_metrics_dashboard_performance(self):
        """Testa performance do dashboard de métricas"""
        print("\n📈 Testando performance do dashboard de métricas...")
        
        # Adicionar alguns pontos de métrica
        start_time = time.time()
        
        for i in range(10):
            self.metrics_dashboard.add_metric_point(
                processing_time=2.0 + i * 0.1,
                num_items=3 + i,
                score_risco=20 + i * 5,
                frauds_detected=i % 2
            )
        
        add_time = time.time() - start_time
        
        # Testar cálculo de métricas atuais
        start_time = time.time()
        current_metrics = self.metrics_dashboard._calculate_current_metrics()
        calc_time = time.time() - start_time
        
        print(f"⏱️ Tempo para adicionar 10 pontos: {add_time:.3f}s")
        print(f"⏱️ Tempo para calcular métricas: {calc_time:.3f}s")
        print(f"📊 Métricas atuais: {current_metrics}")
        
        # Verificar se as operações são rápidas
        self.assertLess(add_time, 1.0, "Adição de pontos deve ser rápida")
        self.assertLess(calc_time, 1.0, "Cálculo de métricas deve ser rápido")
        
        # Verificar se as métricas foram calculadas
        self.assertIsInstance(current_metrics, dict, "Métricas devem ser um dicionário")
        self.assertIn('avg_processing_time', current_metrics, "Métricas devem incluir tempo médio")
        
        print("✅ Teste de performance do dashboard de métricas passou!")
    
    def test_system_availability(self):
        """Testa disponibilidade do sistema"""
        print("\n🔄 Testando disponibilidade do sistema...")
        
        # Testar inicialização de todos os componentes
        components = [
            ("Model Manager", self.model_manager),
            ("Agente 1", self.agente1),
            ("Agente 2", self.agente2),
            ("Agente 3", self.agente3),
            ("Agente 5", self.agente5),
            ("Orquestrador", self.orquestrador),
            ("Dataset de Validação", self.validation_dataset),
            ("Dashboard de Métricas", self.metrics_dashboard)
        ]
        
        for name, component in components:
            self.assertIsNotNone(component, f"{name} deve estar disponível")
            print(f"  ✅ {name}: Operacional")
        
        # Testar operações básicas
        try:
            # Testar LLM
            response = self.llm.invoke("Teste de disponibilidade")
            self.assertIsNotNone(response, "LLM deve responder")
            
            # Testar dataset
            metrics = self.validation_dataset.calculate_accuracy_metrics()
            self.assertIsInstance(metrics, dict, "Dataset deve funcionar")
            
            # Testar dashboard
            current_metrics = self.metrics_dashboard._calculate_current_metrics()
            self.assertIsInstance(current_metrics, dict, "Dashboard deve funcionar")
            
        except Exception as e:
            self.fail(f"Sistema deve estar disponível, mas falhou: {e}")
        
        print("✅ Teste de disponibilidade do sistema passou!")
    
    def run_performance_report(self):
        """Gera relatório de performance"""
        print("\n📊 GERANDO RELATÓRIO DE PERFORMANCE")
        print("=" * 50)
        
        # Executar todos os testes
        test_methods = [
            self.test_model_loading_time,
            self.test_chat_response_time,
            self.test_nfe_processing_time,
            self.test_cache_performance,
            self.test_validation_dataset_performance,
            self.test_metrics_dashboard_performance,
            self.test_system_availability
        ]
        
        results = {}
        
        for test_method in test_methods:
            try:
                test_method()
                results[test_method.__name__] = "✅ PASSOU"
            except Exception as e:
                results[test_method.__name__] = f"❌ FALHOU: {e}"
        
        # Exibir resultados
        print("\n📋 RESULTADOS DOS TESTES:")
        for test_name, result in results.items():
            print(f"  {test_name}: {result}")
        
        # Calcular score geral
        passed = sum(1 for result in results.values() if result.startswith("✅"))
        total = len(results)
        score = (passed / total) * 100
        
        print(f"\n🎯 SCORE GERAL: {score:.1f}% ({passed}/{total} testes passaram)")
        
        if score >= 90:
            print("🏆 EXCELENTE! Sistema atende às métricas de performance.")
        elif score >= 70:
            print("👍 BOM! Sistema atende à maioria das métricas.")
        else:
            print("⚠️ ATENÇÃO! Sistema precisa de melhorias.")
        
        return results


def run_performance_tests():
    """
    Função principal para executar testes de performance
    """
    print("🚀 FISCALAI MVP - TESTES DE PERFORMANCE")
    print("=" * 50)
    
    # Criar suite de testes
    suite = unittest.TestSuite()
    
    # Adicionar testes
    test_suite = PerformanceTestSuite()
    suite.addTest(test_suite)
    
    # Executar relatório
    results = test_suite.run_performance_report()
    
    return results


if __name__ == "__main__":
    run_performance_tests()
