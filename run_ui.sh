#!/bin/bash
# Script para executar interface Streamlit do FiscalAI MVP

echo "🚀 Iniciando FiscalAI MVP - Interface Web"
echo "=========================================="
echo ""

# Ativar ambiente virtual
if [ -f "venv/bin/activate" ]; then
    echo "✅ Ativando ambiente virtual..."
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado!"
    echo "   Execute: python -m venv venv"
    echo "   Depois: source venv/bin/activate"
    echo "   E: pip install -r requirements.txt"
    exit 1
fi

# Verificar se streamlit está instalado
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit não encontrado!"
    echo "   Instale com: pip install -r requirements.txt"
    exit 1
fi

# Executar Streamlit
echo "✅ Iniciando servidor Streamlit..."
echo "   Acesse: http://localhost:8501"
echo ""

streamlit run ui/app.py

