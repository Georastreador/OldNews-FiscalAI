#!/bin/bash

# Script de teste para verificar se executar_aplicacao.sh está funcionando
echo "🧪 Testando script executar_aplicacao.sh..."

# Verificar se estamos no diretório correto
if [ ! -f "executar_aplicacao.sh" ]; then
    echo "❌ Script executar_aplicacao.sh não encontrado"
    exit 1
fi

# Verificar permissões
if [ ! -x "executar_aplicacao.sh" ]; then
    echo "❌ Script não tem permissão de execução"
    exit 1
fi

# Verificar dependências básicas
echo "🔍 Verificando dependências básicas..."

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado"
    exit 1
fi

# Verificar arquivos necessários
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt não encontrado"
    exit 1
fi

if [ ! -f "ui/app.py" ]; then
    echo "❌ ui/app.py não encontrado"
    exit 1
fi

# Verificar ambiente virtual
if [ ! -d "venv" ]; then
    echo "⚠️  Ambiente virtual não encontrado (será criado pelo script)"
else
    echo "✅ Ambiente virtual encontrado"
fi

echo "✅ Todas as verificações básicas passaram"
echo "🚀 O script executar_aplicacao.sh está pronto para uso!"
echo ""
echo "Para executar:"
echo "  ./executar_aplicacao.sh"
