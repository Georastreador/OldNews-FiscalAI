#!/usr/bin/env python3
"""
Script para teste com múltiplas notas CSV e OpenAI
"""

import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def criar_csv_exemplo_multiplas_notas():
    """Cria um CSV de exemplo com múltiplas notas fiscais"""
    
    # Dados de exemplo para múltiplas notas
    dados_notas = [
        # Nota 1 - Consulta médica
        {
            'numero_nota': '000001',
            'serie': '1',
            'data_emissao': '2024-01-15',
            'cnpj_emitente': '12345678000199',
            'razao_social_emitente': 'CLINICA MEDICA EXEMPLO LTDA',
            'cnpj_destinatario': '98765432000188',
            'razao_social_destinatario': 'JOAO SILVA',
            'codigo_produto': 'CONS001',
            'descricao': 'Consulta médica pediátrica',
            'ncm': '85149000',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 1.0,
            'valor_unitario': 150.00,
            'valor_total': 150.00
        },
        
        # Nota 2 - Medicamento
        {
            'numero_nota': '000002',
            'serie': '1',
            'data_emissao': '2024-01-16',
            'cnpj_emitente': '11111111000111',
            'razao_social_emitente': 'FARMACIA CENTRAL LTDA',
            'cnpj_destinatario': '98765432000188',
            'razao_social_destinatario': 'JOAO SILVA',
            'codigo_produto': 'MED001',
            'descricao': 'Paracetamol 500mg - 20 comprimidos',
            'ncm': '30049099',
            'cfop': '5102',
            'unidade': 'UN',
            'quantidade': 2.0,
            'valor_unitario': 25.50,
            'valor_total': 51.00
        },
        
        # Nota 3 - Produto eletrônico (suspeito)
        {
            'numero_nota': '000003',
            'serie': '1',
            'data_emissao': '2024-01-17',
            'cnpj_emitente': '22222222000222',
            'razao_social_emitente': 'ELETRONICOS BRASIL LTDA',
            'cnpj_destinatario': '33333333000333',
            'razao_social_destinatario': 'LOJA TECNOLOGIA LTDA',
            'codigo_produto': 'ELEC001',
            'descricao': 'Smartphone Samsung Galaxy S24',
            'ncm': '85171200',
            'cfop': '1102',
            'unidade': 'UN',
            'quantidade': 1.0,
            'valor_unitario': 500.00,  # Valor suspeitamente baixo
            'valor_total': 500.00
        },
        
        # Nota 4 - Produto com NCM incorreto
        {
            'numero_nota': '000004',
            'serie': '1',
            'data_emissao': '2024-01-18',
            'cnpj_emitente': '44444444000444',
            'razao_social_emitente': 'INDUSTRIA TEXTIL LTDA',
            'cnpj_destinatario': '55555555000555',
            'razao_social_destinatario': 'LOJA ROUPAS LTDA',
            'codigo_produto': 'TEXT001',
            'descricao': 'Camiseta de algodão masculina',
            'ncm': '12345678',  # NCM incorreto (deveria ser 61091000)
            'cfop': '1102',
            'unidade': 'UN',
            'quantidade': 10.0,
            'valor_unitario': 35.00,
            'valor_total': 350.00
        },
        
        # Nota 5 - Serviço de consultoria
        {
            'numero_nota': '000005',
            'serie': '1',
            'data_emissao': '2024-01-19',
            'cnpj_emitente': '66666666000666',
            'razao_social_emitente': 'CONSULTORIA EMPRESARIAL LTDA',
            'cnpj_destinatario': '77777777000777',
            'razao_social_destinatario': 'EMPRESA CLIENTE LTDA',
            'codigo_produto': 'CONS002',
            'descricao': 'Consultoria em gestão empresarial - 20 horas',
            'ncm': '00000000',  # Serviço
            'cfop': '5102',
            'unidade': 'H',
            'quantidade': 20.0,
            'valor_unitario': 200.00,
            'valor_total': 4000.00
        }
    ]
    
    # Criar DataFrame
    df = pd.DataFrame(dados_notas)
    
    # Salvar CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"multiplas_notas_exemplo_{timestamp}.csv"
    filepath = Path(__file__).parent / filename
    
    df.to_csv(filepath, index=False, encoding='utf-8')
    
    print(f"✅ CSV criado: {filepath}")
    print(f"📊 Total de notas: {len(dados_notas)}")
    print(f"📋 Colunas: {list(df.columns)}")
    
    return filepath

def verificar_configuracao_openai():
    """Verifica se a configuração do OpenAI está correta"""
    
    print("🔍 Verificando configuração do OpenAI...")
    
    # Verificar variável de ambiente
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        print("💡 Configure com: export OPENAI_API_KEY='sua_chave_aqui'")
        return False
    
    if openai_key.startswith('sk-'):
        print("✅ OPENAI_API_KEY encontrada e parece válida")
        return True
    else:
        print("⚠️ OPENAI_API_KEY encontrada mas formato pode estar incorreto")
        return False

def testar_modelo_openai():
    """Testa se o modelo OpenAI está funcionando"""
    
    print("🧪 Testando modelo OpenAI...")
    
    try:
        from src.utils.model_manager import get_model_manager
        
        model_manager = get_model_manager()
        
        # Testar GPT-4o Mini
        print("📡 Testando GPT-4o Mini...")
        llm = model_manager.get_llm("gpt-4o-mini")
        
        # Teste simples
        response = llm.invoke("Responda em uma frase: Qual é a capital do Brasil?")
        print(f"✅ Resposta GPT-4o Mini: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar OpenAI: {e}")
        return False

def criar_instrucoes_teste():
    """Cria instruções para o teste"""
    
    print("\n" + "="*60)
    print("🧪 INSTRUÇÕES PARA TESTE COM MÚLTIPLAS NOTAS CSV + OPENAI")
    print("="*60)
    
    print("""
📋 PREPARAÇÃO:
1. ✅ CSV de exemplo criado com 5 notas fiscais
2. ✅ Configuração OpenAI verificada
3. ✅ Modelo OpenAI testado

🚀 COMO EXECUTAR O TESTE:

1. 📤 UPLOAD DO CSV:
   - Acesse a interface Streamlit
   - Vá para "📤 Analisar NF-e"
   - Selecione "📊 CSV (Dados Fiscais)"
   - Faça upload do arquivo CSV criado

2. 🤖 CONFIGURAR MODELO:
   - No sidebar, selecione "☁️ API Externa (OpenAI/Anthropic/Google)"
   - Escolha "GPT-4o Mini (OpenAI)" ou "GPT-4o (OpenAI)"

3. 🔍 EXECUTAR ANÁLISE:
   - Clique em "🚀 Executar CSV!"
   - Aguarde o processamento das 5 notas

4. 📊 VERIFICAR RESULTADOS:
   - Dashboard com métricas consolidadas
   - Análises individuais de cada agente
   - Detecção de fraudes (se houver)
   - Chat com assistente IA

🎯 O QUE ESPERAR:
- ✅ Processamento de 5 notas fiscais diferentes
- ✅ Classificação NCM automática
- ✅ Detecção de possíveis fraudes
- ✅ Respostas de alta qualidade do OpenAI
- ✅ Relatório consolidado

⚠️ POSSÍVEIS FRAUDES DETECTADAS:
- Nota 3: Smartphone com valor suspeitamente baixo
- Nota 4: NCM incorreto para camiseta
""")

def main():
    """Função principal"""
    
    print("🚀 PREPARANDO TESTE COM MÚLTIPLAS NOTAS CSV + OPENAI")
    print("="*60)
    
    # 1. Criar CSV de exemplo
    print("\n1️⃣ Criando CSV de exemplo...")
    csv_file = criar_csv_exemplo_multiplas_notas()
    
    # 2. Verificar configuração OpenAI
    print("\n2️⃣ Verificando configuração OpenAI...")
    openai_ok = verificar_configuracao_openai()
    
    # 3. Testar modelo OpenAI
    if openai_ok:
        print("\n3️⃣ Testando modelo OpenAI...")
        modelo_ok = testar_modelo_openai()
    else:
        modelo_ok = False
    
    # 4. Mostrar instruções
    criar_instrucoes_teste()
    
    # 5. Resumo final
    print("\n" + "="*60)
    print("📊 RESUMO DA PREPARAÇÃO")
    print("="*60)
    print(f"✅ CSV criado: {csv_file.name}")
    print(f"✅ OpenAI configurado: {'Sim' if openai_ok else 'Não'}")
    print(f"✅ Modelo testado: {'Sim' if modelo_ok else 'Não'}")
    
    if openai_ok and modelo_ok:
        print("\n🎉 TUDO PRONTO PARA O TESTE!")
        print("💡 Execute: streamlit run FiscalAI_MVP/ui/app.py")
    else:
        print("\n⚠️ CONFIGURE O OPENAI ANTES DE CONTINUAR")
        print("💡 Configure: export OPENAI_API_KEY='sua_chave_aqui'")

if __name__ == "__main__":
    main()
