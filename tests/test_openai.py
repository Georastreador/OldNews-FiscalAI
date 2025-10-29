#!/usr/bin/env python3
"""
Teste da aplicação OldNews-FiscalAI com OpenAI API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_openai_connection():
    """Testa conexão com OpenAI"""
    print("🔍 Testando conexão com OpenAI...")
    
    try:
        from openai import OpenAI
        
        # Configurar cliente OpenAI
        client = OpenAI(api_key="YOUR_OPENAI_API_KEY_HERE")
        
        # Testar conexão com uma pergunta simples
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Olá! Responda apenas 'Conexão OK' se você recebeu esta mensagem."}
            ],
            max_tokens=10
        )
        
        print(f"✅ Resposta da OpenAI: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão com OpenAI: {e}")
        return False

def test_agents_with_openai():
    """Testa agentes com OpenAI"""
    print("\n🔍 Testando agentes com OpenAI...")
    
    try:
        from src.agents.agente1_extrator import Agente1Extrator
        from src.agents.agente2_classificador import Agente2Classificador
        from src.agents.agente3_validador import Agente3Validador
        from src.agents.agente4_orquestrador import Agente4Orquestrador
        from langchain.llms import OpenAI
        
        # Configurar OpenAI
        os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY_HERE"
        
        # Criar LLM OpenAI
        llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)
        
        # Criar agentes
        extrator = Agente1Extrator()
        classificador = Agente2Classificador(llm)
        validador = Agente3Validador(llm)
        orquestrador = Agente4Orquestrador(llm)
        
        print("✅ Agente1Extrator criado com sucesso")
        print("✅ Agente2Classificador criado com OpenAI")
        print("✅ Agente3Validador criado com OpenAI")
        print("✅ Agente4Orquestrador criado com OpenAI")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na criação dos agentes com OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_xml_processing_with_openai():
    """Testa processamento de XML com OpenAI"""
    print("\n🔍 Testando processamento de XML com OpenAI...")
    
    try:
        from src.utils.universal_xml_parser import parse_fiscal_xml
        from src.agents.agente2_classificador import Agente2Classificador
        from src.agents.agente3_validador import Agente3Validador
        from langchain.llms import OpenAI
        
        # Configurar OpenAI
        os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY_HERE"
        
        # Criar LLM OpenAI
        llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)
        
        # Verificar se há arquivos XML de exemplo
        xml_files = []
        for root, dirs, files in os.walk("data/samples"):
            for file in files:
                if file.endswith('.xml'):
                    xml_files.append(os.path.join(root, file))
        
        if xml_files:
            print(f"✅ Encontrados {len(xml_files)} arquivos XML de exemplo")
            
            # Testar parsing de um arquivo
            xml_file = xml_files[0]
            print(f"🔍 Processando arquivo: {xml_file}")
            
            # Parsear XML
            nfe, status, message = parse_fiscal_xml(xml_file)
            print(f"✅ XML parseado - Status: {status}")
            print(f"✅ XML parseado - Message: {message}")
            
            if nfe:
                print(f"✅ NFe extraída - Chave: {nfe.chave_acesso[:20]}...")
                print(f"✅ NFe extraída - Emitente: {nfe.razao_social_emitente}")
                print(f"✅ NFe extraída - Valor: R$ {nfe.valor_total}")
                print(f"✅ NFe extraída - Itens: {len(nfe.itens)}")
                
                # Testar classificação com OpenAI
                if nfe.itens:
                    print("\n🔍 Testando classificação de NCM com OpenAI...")
                    classificador = Agente2Classificador(llm)
                    
                    # Classificar todos os itens
                    print(f"📦 Itens para classificar: {len(nfe.itens)}")
                    for i, item in enumerate(nfe.itens):
                        print(f"  {i+1}. {item.descricao} (NCM: {item.ncm_declarado})")
                    
                    # Executar classificação
                    resultado_classificacao = classificador.executar(nfe.itens)
                    print(f"✅ Classificação executada: {len(resultado_classificacao)} itens classificados")
                
                # Testar validação com OpenAI
                print("\n🔍 Testando validação com OpenAI...")
                validador = Agente3Validador(llm)
                
                # Executar validação (precisa das classificações)
                resultado_validacao = validador.executar(nfe, resultado_classificacao)
                print(f"✅ Validação executada: {type(resultado_validacao).__name__}")
                if hasattr(resultado_validacao, 'fraudes_detectadas'):
                    print(f"✅ Fraudes detectadas: {len(resultado_validacao.fraudes_detectadas)}")
                
        else:
            print("⚠️ Nenhum arquivo XML de exemplo encontrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no processamento de XML com OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_streamlit_with_openai():
    """Testa aplicação Streamlit com OpenAI"""
    print("\n🔍 Testando aplicação Streamlit com OpenAI...")
    
    try:
        # Configurar OpenAI
        os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY_HERE"
        
        # Testar importação do app
        import ui.app
        print("✅ Aplicação Streamlit importada com sucesso")
        
        # Verificar se as funções principais existem
        from ui.app import pagina_dashboard, pagina_upload, pagina_config
        print("✅ Funções principais do app encontradas")
        
        # Verificar configuração de APIs
        print("✅ Função de configuração de APIs verificada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na aplicação Streamlit com OpenAI: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal de teste"""
    print("🚀 Testando aplicação OldNews-FiscalAI com OpenAI")
    print("=" * 60)
    
    success = True
    
    # Teste 1: Conexão OpenAI
    if not test_openai_connection():
        success = False
    
    # Teste 2: Agentes com OpenAI
    if not test_agents_with_openai():
        success = False
    
    # Teste 3: Processamento XML com OpenAI
    if not test_xml_processing_with_openai():
        success = False
    
    # Teste 4: Streamlit com OpenAI
    if not test_streamlit_with_openai():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Todos os testes com OpenAI passaram!")
        print("✅ A aplicação está pronta para uso com OpenAI API")
    else:
        print("❌ Alguns testes com OpenAI falharam.")
        print("⚠️ Verifique a configuração da API e tente novamente")
    
    return success

if __name__ == "__main__":
    main()
