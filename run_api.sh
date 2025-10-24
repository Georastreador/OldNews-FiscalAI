#!/bin/bash

# FiscalAI MVP - Script para executar API REST
# Executa a API FastAPI do FiscalAI

echo "🚀 Iniciando FiscalAI MVP API..."
echo "=================================="

# Verificar se está no ambiente virtual
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Verificar dependências
echo "📦 Verificando dependências..."
python -c "import fastapi, uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Dependências não encontradas. Instalando..."
    pip install fastapi uvicorn python-multipart
fi

# Executar API
echo "🌐 Iniciando servidor API..."
echo "📖 Documentação disponível em: http://localhost:8000/docs"
echo "🔍 Health check em: http://localhost:8000/health"
echo ""
echo "Pressione Ctrl+C para parar o servidor"
echo ""

cd "$(dirname "$0")"
python -m src.api.main
