@echo off
chcp 65001 >nul
title OldNews FiscalAI - Sistema Inteligente de Análise Fiscal

echo.
echo 🚀 OldNews FiscalAI - Sistema Inteligente de Análise Fiscal
echo ==========================================================
echo.

REM Verificar se estamos no diretório correto
if not exist "requirements.txt" (
    echo ❌ Erro: Execute este script no diretório raiz do projeto
    echo 💡 Certifique-se de estar em: C:\caminho\para\OldNews-FiscalAI
    echo.
    pause
    exit /b 1
)

REM Verificar Python
echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Erro: Python não encontrado!
    echo 💡 Instale Python primeiro: https://python.org
    echo 💡 Certifique-se de marcar "Add Python to PATH" durante a instalação
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% encontrado

REM Verificar/ criar ambiente virtual
echo 🔍 Verificando ambiente virtual...
if not exist "venv" (
    echo 📦 Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Erro ao criar ambiente virtual!
        pause
        exit /b 1
    )
    echo ✅ Ambiente virtual criado
)

REM Ativar ambiente virtual
echo 🔧 Ativando ambiente virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Erro ao ativar ambiente virtual!
    pause
    exit /b 1
)
echo ✅ Ambiente virtual ativado

REM Verificar/ instalar dependências
echo 📦 Verificando dependências...
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo 📥 Instalando dependências...
    echo ⏳ Isso pode levar alguns minutos...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Erro ao instalar dependências!
        echo.
        pause
        exit /b 1
    )
    echo ✅ Dependências instaladas
) else (
    echo ✅ Dependências já instaladas
)

REM Verificar arquivo .env
echo 🔍 Verificando configuração...
if not exist ".env" (
    if exist "config\production.env.example" (
        echo 📋 Criando arquivo .env...
        copy config\production.env.example .env >nul
        echo ⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua API Key da OpenAI
    )
) else (
    echo ✅ Arquivo .env encontrado
)

REM Verificar se Streamlit está instalado
echo 🔍 Verificando Streamlit...
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo 📥 Instalando Streamlit...
    pip install streamlit
    if errorlevel 1 (
        echo ❌ Erro ao instalar Streamlit!
        echo.
        pause
        exit /b 1
    )
    echo ✅ Streamlit instalado
)

REM Executar aplicação
echo.
echo 🌐 Iniciando aplicação...
echo 📱 A aplicação será aberta no seu navegador
echo 🔗 URL: http://localhost:8501
echo.
echo ⚠️  IMPORTANTE:
echo    • Mantenha esta janela aberta
echo    • Para parar, feche esta janela ou pressione Ctrl+C
echo    • Configure sua API Key da OpenAI na interface
echo.

REM Aguardar um pouco
timeout /t 3 /nobreak >nul

REM Executar Streamlit
echo 🚀 Executando aplicação...
streamlit run ui\app.py

REM Manter a janela aberta após o fechamento
echo.
echo Aplicação encerrada. Pressione qualquer tecla para fechar...
pause >nul
