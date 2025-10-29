#!/usr/bin/env python3
"""
Teste das correções na interface de análise dos agentes CrewAI
"""

import streamlit as st
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_expander_layout():
    """Testa o layout dos expanders para verificar se não há sobreposição"""
    
    st.title("🧪 Teste de Layout - Análises dos Agentes CrewAI")
    st.markdown("---")
    
    st.subheader("🤖 Análises dos Agentes CrewAI")
    
    # Simular os expanders dos agentes
    with st.expander("🔍 Agente 1 - Extrator de Dados", expanded=True):
        st.write("**Chave de Acesso:** 74124611099371218106012754150041410611253000")
        st.write("**Emitente:** VACIMUNE CLINICA DE CRIANCAS E DE ADOLESCENTES LTDA (CNPJ: 31857642000135)")
        st.write("**Destinatário:** JOAO RICARDO DA CUNHA CROCE LOPES (CNPJ: 00016862012819)")
        st.write("**Data de Emissão:** 22/06/2011 18:52")
        st.write("**Valor Total:** R$ 855.00")
        st.write("**Número de Itens:** 1")
    
    with st.expander("🏷️ Agente 2 - Classificador NCM", expanded=True):
        st.write("**Total de Produtos Classificados:** 1")
        st.write("**1. Item 1:** referente a duas consultas medicas (pediátricas) prestada a seus filhos João Henrique Croce Lopes e João Arthur Croce Lopes.")
        st.write("   - **NCM Declarado:** 00000403")
        st.write("   - **NCM Predito:** 00000403")
        st.write("   - **Confiança:** 50%")
        st.write("   - **Justificativa:** Classificação automática falhou. Usando NCM declarado.")
    
    with st.expander("✅ Agente 3 - Validador Fiscal", expanded=True):
        st.write("**Status da Validação:** Conforme")
        st.write("**Conformidade Fiscal:** 100%")
        st.write("**Observações:** Documento atende aos padrões fiscais")
    
    with st.expander("🎯 Agente 4 - Orquestrador", expanded=True):
        st.write("**Análise Concluída:** ✅")
        st.write("**Score de Risco Geral:** 0.0/100")
        st.write("**Nível de Risco:** BAIXO")
        st.write("**Data da Análise:** 24/10/2025 08:44:16")
    
    st.markdown("---")
    st.info("""
    **Verificações:**
    1. ✅ Os títulos dos agentes devem estar claramente visíveis
    2. ✅ Não deve haver sobreposição de texto
    3. ✅ O conteúdo deve estar bem separado dos títulos
    4. ✅ Os expanders devem ter bordas e espaçamento adequados
    """)

def main():
    """Função principal"""
    test_expander_layout()

if __name__ == "__main__":
    main()
