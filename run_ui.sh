#!/bin/bash

# OldNews FiscalAI - Script para Interface Web
# Executa a interface Streamlit

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 OldNews FiscalAI - Interface Web${NC}"
echo -e "${BLUE}====================================${NC}"

# Verificar se estamos no diretório correto
if [ ! -f "ui/app.py" ]; then
    echo -e "${RED}❌ Erro: Execute este script no diretório raiz do OldNews-FiscalAI${NC}"
    exit 1
fi

# Ativar ambiente virtual
echo -e "${YELLOW}🔧 Ativando ambiente virtual...${NC}"
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
else
    echo -e "${RED}❌ Ambiente virtual não encontrado. Execute ./executar_aplicacao.sh primeiro${NC}"
    exit 1
fi

# Verificar dependências críticas
echo -e "${YELLOW}🔍 Verificando dependências...${NC}"
python -c "import streamlit, pandas, langchain" 2>/dev/null || {
    echo -e "${RED}❌ Dependências faltando. Execute ./executar_aplicacao.sh primeiro${NC}"
    exit 1
}
echo -e "${GREEN}✅ Dependências OK${NC}"

# Verificar porta 8501
echo -e "${YELLOW}🔍 Verificando porta 8501...${NC}"
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Porta 8501 em uso. Parando processos...${NC}"
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 2
fi

# Executar Streamlit
echo -e "${GREEN}🌐 Iniciando interface web...${NC}"
echo -e "${BLUE}📱 Acesse: http://localhost:8501${NC}"
echo -e "${YELLOW}⚠️  Para parar: Ctrl+C${NC}"
echo ""

streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
