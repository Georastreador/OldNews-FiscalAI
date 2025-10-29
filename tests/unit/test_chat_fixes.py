#!/usr/bin/env python3
"""
Teste das correções no chat do modelo local
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.model_manager import get_model_manager
from src.models import LLMConfig, LLMProvider

load_dotenv()

def test_model_config():
    """Testa se a configuração do modelo está correta"""
    print("🔧 Testando configuração do modelo...")
    
    manager = get_model_manager()
    
    # Testar configuração padrão
    config_default = manager._load_default_config()
    print(f"✅ Configuração padrão:")
    print(f"  Provider: {config_default.provider}")
    print(f"  Model: {config_default.model}")
    print(f"  Temperature: {config_default.temperature}")
    print(f"  Max tokens: {config_default.max_tokens}")
    
    # Testar configuração de modelo específico
    llm = manager.get_llm("mistral-7b-gguf")
    print(f"✅ LLM obtido: {type(llm).__name__}")
    
    return True

def test_response_cleaning():
    """Testa a limpeza de respostas"""
    print("\n🧹 Testando limpeza de respostas...")
    
    from src.utils.model_manager import LocalGGUFWrapper
    from src.models import LLMConfig, LLMProvider
    
    # Criar wrapper de teste
    config = LLMConfig(
        provider=LLMProvider.LOCAL,
        model="test",
        temperature=0.1,
        max_tokens=512
    )
    
    # Mock do local_manager
    class MockLocalManager:
        def generate_response(self, model_name, prompt, **kwargs):
            return "ASSISTANT: Esta é uma resposta de teste. Esta é uma resposta de teste."
    
    wrapper = LocalGGUFWrapper(MockLocalManager(), "test", config)
    
    # Testar limpeza
    test_response = "ASSISTANT: Esta é uma resposta de teste. Esta é uma resposta de teste."
    cleaned = wrapper._clean_response(test_response)
    
    print(f"✅ Resposta original: {test_response}")
    print(f"✅ Resposta limpa: {cleaned}")
    
    return "ASSISTANT:" not in cleaned and len(cleaned.split('\n')) <= 2

def test_simple_prompt():
    """Testa um prompt simples com o modelo local"""
    print("\n💬 Testando prompt simples...")
    
    try:
        manager = get_model_manager()
        llm = manager.get_llm("mistral-7b-gguf")
        
        prompt = "Responda em uma frase: Qual é a capital do Brasil?"
        response = llm.invoke(prompt, max_tokens=50)
        
        print(f"✅ Prompt: {prompt}")
        print(f"✅ Resposta: {response}")
        
        # Verificar se a resposta é razoável
        return len(response) < 200 and "Brasília" in response or "brasília" in response
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def test_fiscal_prompt():
    """Testa um prompt fiscal específico"""
    print("\n📊 Testando prompt fiscal...")
    
    try:
        manager = get_model_manager()
        llm = manager.get_llm("mistral-7b-gguf")
        
        prompt = """Você é um assistente fiscal especializado. Responda de forma clara e concisa.

CONTEXTO: NF-e R$ 1.000, 5 itens, risco 25/100, 0 fraudes

PERGUNTA: Qual o valor total das NFs?

INSTRUÇÕES:
1. Responda APENAS à pergunta feita
2. Seja direto e objetivo (máximo 3 parágrafos)
3. Use dados específicos do relatório quando disponível
4. Se não souber, diga "Não tenho essa informação no relatório"
5. Use **negrito** para destacar informações importantes
6. Termine a resposta com um ponto final

RESPOSTA:"""
        
        response = llm.invoke(prompt, max_tokens=100)
        
        print(f"✅ Prompt fiscal testado")
        print(f"✅ Resposta: {response}")
        
        # Verificar se a resposta é relevante
        return len(response) < 300 and ("R$" in response or "valor" in response.lower())
        
    except Exception as e:
        print(f"❌ Erro no teste fiscal: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🧪 TESTE DAS CORREÇÕES NO CHAT DO MODELO LOCAL")
    print("=" * 60)
    
    results = {}
    
    # Teste 1: Configuração
    print("\n🔬 Teste 1: Configuração do Modelo")
    print("-" * 40)
    results["config"] = test_model_config()
    print(f"✅ Configuração: {'PASSOU' if results['config'] else 'FALHOU'}")
    
    # Teste 2: Limpeza de respostas
    print("\n🔬 Teste 2: Limpeza de Respostas")
    print("-" * 40)
    results["cleaning"] = test_response_cleaning()
    print(f"✅ Limpeza: {'PASSOU' if results['cleaning'] else 'FALHOU'}")
    
    # Teste 3: Prompt simples
    print("\n🔬 Teste 3: Prompt Simples")
    print("-" * 40)
    results["simple"] = test_simple_prompt()
    print(f"✅ Prompt Simples: {'PASSOU' if results['simple'] else 'FALHOU'}")
    
    # Teste 4: Prompt fiscal
    print("\n🔬 Teste 4: Prompt Fiscal")
    print("-" * 40)
    results["fiscal"] = test_fiscal_prompt()
    print(f"✅ Prompt Fiscal: {'PASSOU' if results['fiscal'] else 'FALHOU'}")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test_name, passed in results.items():
        print(f"{test_name.replace('_', ' ').title()}: {'✅ PASSOU' if passed else '❌ FALHOU'}")
    
    all_passed = all(results.values())
    print(f"\n🎯 Resultado Final: {sum(results.values())}/{len(results)} testes passaram")
    
    if all_passed:
        print("🎉 Todas as correções funcionaram! O chat deve estar melhor agora.")
    else:
        print("⚠️ Alguns testes falharam. Verifique os logs acima.")
    
    return all_passed

if __name__ == "__main__":
    main()
