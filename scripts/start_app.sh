#!/bin/bash

# Script melhorado para executar a aplicação FiscalAI

echo "🚀 Iniciando FiscalAI..."
echo "📁 Diretório: $(pwd)"

# Configurar API key do OpenAI (configure sua chave aqui)
# export OPENAI_API_KEY="sua_chave_aqui"
echo "🔑 Configure sua API Key OpenAI no arquivo .env ou descomente a linha acima"

# Função para encontrar porta disponível
find_available_port() {
    local port=8501
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; do
        port=$((port + 1))
    done
    echo $port
}

# Ativar ambiente virtual
echo "🐍 Ativando ambiente virtual..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Erro ao ativar ambiente virtual!"
    exit 1
fi

echo "✅ Ambiente virtual ativado"

# Verificar dependências críticas
echo "🔍 Verificando dependências..."

python -c "
import streamlit, chardet, pandas, openai
print('✅ Todas as dependências estão OK')
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ Dependências faltando. Instalando..."
    pip install -r requirements.txt
fi

# Encontrar porta disponível
PORT=$(find_available_port)
echo "🌐 Usando porta: $PORT"

# Verificar se há processo na porta padrão
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ Porta 8501 em uso. Matando processo..."
    kill -9 $(lsof -ti:8501) 2>/dev/null
    sleep 2
fi

echo "🎯 Iniciando aplicação Streamlit..."
echo "🌐 Acesse: http://localhost:$PORT"
echo ""

# Executar Streamlit
streamlit run ui/app.py --server.port $PORT --server.headless false
