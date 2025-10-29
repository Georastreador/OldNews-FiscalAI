#!/bin/bash
# Script principal para inicializar o FiscalAI
# Permite escolher entre UI, API ou ambos

# Obter diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "🚀 FiscalAI - Sistema de Análise Fiscal Inteligente"
echo "=================================================="
echo "📁 Diretório do projeto: $PROJECT_DIR"
echo ""

# Navegar para o diretório do projeto
cd "$PROJECT_DIR"

# Verificar ambiente virtual
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "   Execute: python -m venv venv"
    echo "   Depois: source venv/bin/activate"
    echo "   E: pip install -r requirements.txt"
    exit 1
fi

# Ativar ambiente virtual
echo "✅ Ativando ambiente virtual..."
source venv/bin/activate

# Menu de opções
echo ""
echo "Escolha uma opção:"
echo "1) 🌐 Interface Web (Streamlit)"
echo "2) 🔌 API REST (FastAPI)"
echo "3) 🚀 Ambos (UI + API)"
echo "4) 🔧 Verificar instalação"
echo "5) ❌ Sair"
echo ""

read -p "Digite sua escolha (1-5): " choice

case $choice in
    1)
        echo "🌐 Iniciando Interface Web..."
        ./scripts/run_ui.sh
        ;;
    2)
        echo "🔌 Iniciando API REST..."
        ./scripts/run_api.sh
        ;;
    3)
        echo "🚀 Iniciando ambos (UI + API)..."
        echo "   Interface Web: http://localhost:8501"
        echo "   API REST: http://localhost:8000"
        echo ""
        # Executar API em background
        ./scripts/run_api.sh &
        API_PID=$!
        # Aguardar um pouco para a API inicializar
        sleep 3
        # Executar UI
        ./scripts/run_ui.sh
        # Parar API quando UI for fechada
        kill $API_PID 2>/dev/null
        ;;
    4)
        echo "🔧 Verificando instalação..."
        echo ""
        echo "📦 Verificando dependências Python..."
        python -c "
import sys
print(f'Python: {sys.version}')
try:
    import streamlit
    print(f'✅ Streamlit: {streamlit.__version__}')
except ImportError:
    print('❌ Streamlit não instalado')

try:
    import fastapi
    print(f'✅ FastAPI: {fastapi.__version__}')
except ImportError:
    print('❌ FastAPI não instalado')

try:
    import pandas
    print(f'✅ Pandas: {pandas.__version__}')
except ImportError:
    print('❌ Pandas não instalado')

try:
    import plotly
    print(f'✅ Plotly: {plotly.__version__}')
except ImportError:
    print('❌ Plotly não instalado')
"
        echo ""
        echo "📁 Estrutura do projeto:"
        ls -la
        ;;
    5)
        echo "👋 Saindo..."
        exit 0
        ;;
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac
