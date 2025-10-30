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
    python -m pip install --upgrade pip wheel setuptools
    python -m pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Dependências já instaladas${NC}"
fi

# Verificar arquivo .env
echo -e "${YELLOW}🔍 Verificando configuração...${NC}"
if [ ! -f ".env" ]; then
    if [ -f "production.env.example" ]; then
        echo -e "${YELLOW}📋 Criando arquivo .env...${NC}"
        cp production.env.example .env
        echo -e "${YELLOW}⚠️  IMPORTANTE: Edite o arquivo .env e adicione suas chaves de API (OpenAI/Anthropic/Google/Groq)${NC}"
    elif [ -f "debug_config_example.env" ]; then
        echo -e "${YELLOW}📋 Criando arquivo .env a partir de debug_config_example.env...${NC}"
        cp debug_config_example.env .env
        echo -e "${YELLOW}⚠️  IMPORTANTE: Edite o arquivo .env e ajuste as chaves de API${NC}"
    else
        echo -e "${YELLOW}⚠️  Nenhum arquivo de exemplo .env encontrado${NC}"
    fi
else
    echo -e "${GREEN}✅ Arquivo .env encontrado${NC}"
fi

# Verificar dependências críticas
echo -e "${YELLOW}🔍 Verificando dependências críticas...${NC}"
MISSING_DEPS=()

# Verificar Streamlit
if ! python -c "import streamlit" 2>/dev/null; then
    MISSING_DEPS+=("streamlit")
fi

# Verificar pandas
if ! python -c "import pandas" 2>/dev/null; then
    MISSING_DEPS+=("pandas")
fi

# Verificar langchain
if ! python -c "import langchain" 2>/dev/null; then
    MISSING_DEPS+=("langchain")
fi

# Instalar dependências faltantes
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}📥 Instalando dependências faltantes: ${MISSING_DEPS[*]}${NC}"
    pip install "${MISSING_DEPS[@]}"
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Todas as dependências críticas estão instaladas${NC}"
fi

# Verificar se a porta 8501 está disponível
echo -e "${YELLOW}🔍 Verificando porta 8501...${NC}"
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Porta 8501 já está em uso. Tentando parar processos...${NC}"
    pkill -f "streamlit run" 2>/dev/null || true
    sleep 2
    if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}❌ Não foi possível liberar a porta 8501${NC}"
        echo -e "${YELLOW}💡 Feche outros processos que usam a porta 8501 e tente novamente${NC}"
        exit 1
    fi
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

# Executar Streamlit com tratamento de erro
echo -e "${GREEN}🚀 Executando aplicação...${NC}"
if ! streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0; then
    echo -e "${RED}❌ Erro ao executar a aplicação${NC}"
    echo -e "${YELLOW}💡 Verifique os logs acima para mais detalhes${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Aplicação encerrada. Pressione Enter para fechar...${NC}"
read
