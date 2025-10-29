#!/bin/bash

# OldNews FiscalAI - Script de Execução Automática
# Este script configura e executa a aplicação automaticamente

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 OldNews FiscalAI - Sistema Inteligente de Análise Fiscal${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Verificar se estamos no diretório correto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Erro: Execute este script no diretório raiz do projeto${NC}"
    echo -e "${YELLOW}💡 Certifique-se de estar em: /caminho/para/OldNews-FiscalAI${NC}"
    exit 1
fi

# Verificar Python
echo -e "${YELLOW}🔍 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado!${NC}"
    echo -e "${YELLOW}💡 Instale Python 3.11+ primeiro: https://python.org${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} encontrado${NC}"

# Verificar/ criar ambiente virtual
echo -e "${YELLOW}🔍 Verificando ambiente virtual...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Criando ambiente virtual...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ Ambiente virtual criado${NC}"
fi

# Ativar ambiente virtual
echo -e "${YELLOW}🔧 Ativando ambiente virtual...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"

# Verificar/ instalar dependências
echo -e "${YELLOW}📦 Verificando dependências...${NC}"
if [ ! -f "venv/pyvenv.cfg" ] || ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${YELLOW}📥 Instalando dependências...${NC}"
    echo -e "${YELLOW}⏳ Isso pode levar alguns minutos...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Dependências já instaladas${NC}"
fi

# Verificar arquivo .env
echo -e "${YELLOW}🔍 Verificando configuração...${NC}"
if [ ! -f ".env" ]; then
    if [ -f "config/production.env.example" ]; then
        echo -e "${YELLOW}📋 Criando arquivo .env...${NC}"
        cp config/production.env.example .env
        echo -e "${YELLOW}⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua API Key da OpenAI${NC}"
    fi
else
    echo -e "${GREEN}✅ Arquivo .env encontrado${NC}"
fi

# Verificar se Streamlit está instalado
echo -e "${YELLOW}🔍 Verificando Streamlit...${NC}"
if ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${YELLOW}📥 Instalando Streamlit...${NC}"
    pip install streamlit
    echo -e "${GREEN}✅ Streamlit instalado${NC}"
fi

# Executar aplicação
echo ""
echo -e "${GREEN}🌐 Iniciando aplicação...${NC}"
echo -e "${BLUE}📱 A aplicação será aberta no seu navegador${NC}"
echo -e "${BLUE}🔗 URL: http://localhost:8501${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
echo -e "${YELLOW}   • Mantenha esta janela aberta${NC}"
echo -e "${YELLOW}   • Para parar, pressione Ctrl+C${NC}"
echo -e "${YELLOW}   • Configure sua API Key da OpenAI na interface${NC}"
echo ""

# Aguardar um pouco
sleep 3

# Executar Streamlit
echo -e "${GREEN}🚀 Executando aplicação...${NC}"
streamlit run ui/app.py

echo ""
echo -e "${YELLOW}Aplicação encerrada. Pressione Enter para fechar...${NC}"
read
