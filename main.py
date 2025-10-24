"""
OldNews FiscalAI - Main Entry Point
Sistema multi-agente para análise fiscal de NF-e
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils import get_model_manager
from src.agents import (
    Agente1Extrator,
    Agente2Classificador,
    Agente3Validador,
    Agente4Orquestrador,
    Agente5Interface,
)
from src.detectors import OrquestradorDeteccaoFraudes
from src.models import LLMConfig, LLMProvider

# Carregar variáveis de ambiente
load_dotenv()


def analisar_nfe(xml_path: str, model_name: str = "mistral-7b-local") -> dict:
    """
    Analisa uma NF-e XML completa
    
    Args:
        xml_path: Caminho para o arquivo XML da NF-e
        model_name: Nome do modelo LLM a usar
    
    Returns:
        Dict com relatório completo
    """
    print("=" * 80)
    print("🚀 OldNews FiscalAI - Sistema de Análise Fiscal Inteligente")
    print("=" * 80)
    print()
    
    # 1. Configurar LLM
    print(f"⚙️  Configurando modelo: {model_name}")
    model_manager = get_model_manager()
    llm = model_manager.get_llm(model_name)
    print(f"✅ Modelo {model_name} carregado com sucesso!")
    print()
    
    # 2. Criar agentes
    print("🤖 Inicializando agentes...")
    agente1 = Agente1Extrator(llm)
    agente2 = Agente2Classificador(llm)
    
    # Criar orquestrador de fraudes
    orquestrador_fraudes = OrquestradorDeteccaoFraudes()
    agente3 = Agente3Validador(llm, orquestrador_fraudes)
    agente4 = Agente4Orquestrador(llm)
    agente5 = Agente5Interface(llm)
    print("✅ 5 agentes inicializados!")
    print()
    
    # 3. Executar análise completa
    try:
        relatorio = agente4.executar_fluxo_completo(
            xml_path=xml_path,
            agente1=agente1,
            agente2=agente2,
            agente3=agente3,
        )
        
        # 4. Exibir resultados
        print()
        print("=" * 80)
        print("📊 RESULTADOS DA ANÁLISE")
        print("=" * 80)
        print()
        
        print(f"📄 NF-e: {relatorio.nfe.numero}/{relatorio.nfe.serie}")
        print(f"🔑 Chave: {relatorio.nfe.chave_acesso}")
        print(f"💰 Valor Total: R$ {relatorio.nfe.valor_total:,.2f}")
        print(f"📦 Itens: {len(relatorio.nfe.itens)}")
        print()
        
        print(f"🎯 Score de Risco: {relatorio.resultado_analise.score_risco_geral}/100")
        print(f"⚠️  Nível de Risco: {relatorio.resultado_analise.nivel_risco.value.upper()}")
        print(f"🚨 Fraudes Detectadas: {len(relatorio.resultado_analise.fraudes_detectadas)}")
        print()
        
        if relatorio.resultado_analise.fraudes_detectadas:
            print("🔍 FRAUDES DETECTADAS:")
            for i, fraude in enumerate(relatorio.resultado_analise.fraudes_detectadas, 1):
                print(f"\n{i}. {fraude.tipo_fraude.value.upper()} (Score: {fraude.score}/100)")
                print(f"   Item: {fraude.item_numero or 'NF-e completa'}")
                print(f"   Confiança: {fraude.confianca:.0%}")
                print(f"   Evidências:")
                for ev in fraude.evidencias[:3]:
                    print(f"   - {ev}")
        else:
            print("✅ Nenhuma fraude detectada!")
        
        print()
        print("📋 AÇÕES RECOMENDADAS:")
        for acao in relatorio.acoes_recomendadas[:5]:
            print(f"  • {acao}")
        
        print()
        print("=" * 80)
        print(f"✅ Análise concluída em {relatorio.resultado_analise.tempo_processamento_segundos}s")
        print("=" * 80)
        print()
        
        # 5. Carregar relatório no agente de interface
        agente5.carregar_relatorio(relatorio)
        
        return {
            "relatorio": relatorio,
            "nfe": relatorio.nfe,
            "classificacoes": relatorio.classificacoes_ncm,
            "resultado_analise": relatorio.resultado_analise,
            "agente_interface": agente5,
            "sucesso": True,
        }
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "erro": str(e),
            "sucesso": False,
        }


def exportar_relatorio_pdf(xml_path: str, model_name: str = "mistral-7b-local", output_path: str = None) -> str:
    """
    Analisa NF-e e exporta relatório em PDF
    
    Args:
        xml_path: Caminho para o arquivo XML da NF-e
        model_name: Nome do modelo LLM a usar
        output_path: Caminho opcional para salvar o PDF
        
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    print("=" * 80)
    print("📄 OldNews FiscalAI - Exportação de Relatório PDF")
    print("=" * 80)
    print()
    
    # Analisar NF-e
    relatorio = analisar_nfe(xml_path, model_name)
    
    if not relatorio["sucesso"]:
        raise ValueError(f"Erro na análise: {relatorio.get('erro')}")
    
    # Exportar PDF
    print("📄 Gerando relatório PDF...")
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"relatorio_fiscal_{timestamp}.pdf"
    
    # Usar o orquestrador para exportar PDF
    model_manager = get_model_manager()
    llm = model_manager.get_llm(model_name)
    orquestrador = Agente4Orquestrador(llm)
    
    pdf_path = orquestrador.exportar_relatorio_pdf(
        relatorio['nfe'],
        relatorio['classificacoes'],
        relatorio['resultado_analise'],
        output_path
    )
    
    print(f"✅ Relatório PDF gerado: {pdf_path}")
    return pdf_path


def modo_interativo(agente5: Agente5Interface):
    """
    Modo interativo de chat com o assistente
    
    Args:
        agente5: Agente de interface carregado com relatório
    """
    print()
    print("=" * 80)
    print("💬 MODO INTERATIVO - Chat com Assistente Fiscal")
    print("=" * 80)
    print()
    print("Digite 'sair' para encerrar")
    print("Digite 'sugestões' para ver perguntas sugeridas")
    print()
    
    # Exibir mensagem inicial
    mensagem_inicial = agente5.obter_historico()[0]["content"]
    print(f"🤖 Assistente: {mensagem_inicial}")
    print()
    
    while True:
        try:
            # Input do usuário
            pergunta = input("👤 Você: ").strip()
            
            if not pergunta:
                continue
            
            if pergunta.lower() in ['sair', 'exit', 'quit']:
                print("\n👋 Até logo!")
                break
            
            if pergunta.lower() in ['sugestões', 'sugestoes', 'ajuda', 'help']:
                sugestoes = agente5.sugerir_perguntas()
                print("\n💡 Perguntas sugeridas:")
                for i, sug in enumerate(sugestoes, 1):
                    print(f"   {i}. {sug}")
                print()
                continue
            
            # Processar pergunta
            resposta = agente5.conversar(pergunta)
            print(f"\n🤖 Assistente: {resposta}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Até logo!")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}\n")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OldNews FiscalAI - Sistema de Análise Fiscal Inteligente"
    )
    parser.add_argument(
        "xml_path",
        help="Caminho para o arquivo XML da NF-e"
    )
    parser.add_argument(
        "--model",
        default="mistral-7b-local",
        help="Modelo LLM a usar (padrão: mistral-7b-local)"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Ativar modo interativo (chat) após análise"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Listar modelos disponíveis"
    )
    parser.add_argument(
        "--export-pdf",
        action="store_true",
        help="Exportar relatório em PDF após análise"
    )
    parser.add_argument(
        "--pdf-output",
        type=str,
        help="Caminho para salvar o PDF (padrão: auto-gerado)"
    )
    
    args = parser.parse_args()
    
    # Listar modelos
    if args.list_models:
        print("\n📋 MODELOS DISPONÍVEIS:\n")
        model_manager = get_model_manager()
        modelos = model_manager.list_available_models()
        
        for nome, info in modelos.items():
            print(f"  • {nome}")
            print(f"    Descrição: {info['description']}")
            print(f"    Provider: {info['provider'].value}")
            print(f"    Custo: ${info['cost_per_1k_tokens']:.5f} por 1k tokens")
            print()
        
        return
    
    # Verificar se arquivo existe
    xml_path = Path(args.xml_path)
    if not xml_path.exists():
        print(f"❌ Arquivo não encontrado: {xml_path}")
        return
    
    # Executar análise
    resultado = analisar_nfe(str(xml_path), args.model)
    
    if not resultado["sucesso"]:
        sys.exit(1)
    
    # Exportar PDF se solicitado
    if args.export_pdf:
        try:
            pdf_path = exportar_relatorio_pdf(
                str(xml_path), 
                args.model, 
                args.pdf_output
            )
            print(f"\n📄 Relatório PDF salvo em: {pdf_path}")
        except Exception as e:
            print(f"\n❌ Erro ao gerar PDF: {e}")
    
    # Modo interativo
    if args.interactive:
        agente5 = resultado["agente_interface"]
        modo_interativo(agente5)


if __name__ == "__main__":
    main()

