# OldNews FiscalAI - Script PowerShell para Windows
# Executa a aplicação com verificações completas

param(
    [switch]$Force
)

# Configurações
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Cores para output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Blue "🚀 OldNews FiscalAI - PowerShell Script"
Write-ColorOutput Blue "======================================"

# Verificar se estamos no diretório correto
if (-not (Test-Path "ui\app.py")) {
    Write-ColorOutput Red "❌ Erro: Execute este script no diretório raiz do OldNews-FiscalAI"
    exit 1
}

# Verificar Python
Write-ColorOutput Yellow "🔍 Verificando Python..."
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.(1[1-9]|[2-9][0-9])") {
        Write-ColorOutput Green "✅ Python encontrado: $pythonVersion"
    } else {
        Write-ColorOutput Red "❌ Python 3.11+ necessário. Encontrado: $pythonVersion"
        exit 1
    }
} catch {
    Write-ColorOutput Red "❌ Python não encontrado. Instale Python 3.11+ primeiro"
    exit 1
}

# Verificar/Criar ambiente virtual
Write-ColorOutput Yellow "🔧 Verificando ambiente virtual..."
if (-not (Test-Path "venv")) {
    Write-ColorOutput Yellow "📦 Criando ambiente virtual..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput Red "❌ Erro ao criar ambiente virtual"
        exit 1
    }
    Write-ColorOutput Green "✅ Ambiente virtual criado"
}

# Ativar ambiente virtual
Write-ColorOutput Yellow "🔧 Ativando ambiente virtual..."
& "venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput Red "❌ Erro ao ativar ambiente virtual"
    exit 1
}
Write-ColorOutput Green "✅ Ambiente virtual ativado"

# Verificar dependências
Write-ColorOutput Yellow "🔍 Verificando dependências..."
try {
    python -c "import streamlit, pandas, langchain" 2>$null
    Write-ColorOutput Green "✅ Dependências principais OK"
} catch {
    Write-ColorOutput Yellow "📥 Instalando dependências..."
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput Red "❌ Erro ao instalar dependências"
        exit 1
    }
    Write-ColorOutput Green "✅ Dependências instaladas"
}

# Verificar arquivo .env
Write-ColorOutput Yellow "🔍 Verificando configuração..."
if (-not (Test-Path ".env")) {
    if (Test-Path "config\env.example") {
        Write-ColorOutput Yellow "📋 Criando arquivo .env..."
        Copy-Item "config\env.example" ".env"
        Write-ColorOutput Yellow "⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua API Key da OpenAI"
    } elseif (Test-Path "config\production.env.example") {
        Write-ColorOutput Yellow "📋 Criando arquivo .env..."
        Copy-Item "config\production.env.example" ".env"
        Write-ColorOutput Yellow "⚠️  IMPORTANTE: Edite o arquivo .env e adicione sua API Key da OpenAI"
    } else {
        Write-ColorOutput Yellow "⚠️  Nenhum arquivo de exemplo .env encontrado"
    }
} else {
    Write-ColorOutput Green "✅ Arquivo .env encontrado"
}

# Verificar porta 8501
Write-ColorOutput Yellow "🔍 Verificando porta 8501..."
$portInUse = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-ColorOutput Yellow "⚠️  Porta 8501 em uso. Tentando parar processos..."
    Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.CommandLine -like "*streamlit*"} | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Executar aplicação
Write-ColorOutput Green "🌐 Iniciando aplicação..."
Write-ColorOutput Blue "📱 A aplicação será aberta no seu navegador"
Write-ColorOutput Blue "🔗 URL: http://localhost:8501"
Write-ColorOutput Yellow "⚠️  IMPORTANTE:"
Write-ColorOutput Yellow "   • Mantenha esta janela aberta"
Write-ColorOutput Yellow "   • Para parar, pressione Ctrl+C"
Write-ColorOutput Yellow "   • Configure sua API Key da OpenAI na interface"
Write-Output ""

# Aguardar um pouco
Start-Sleep -Seconds 3

# Executar Streamlit
try {
    & "venv\Scripts\streamlit.exe" run ui\app.py --server.port 8501 --server.address 0.0.0.0
} catch {
    Write-ColorOutput Red "❌ Erro ao executar a aplicação"
    Write-ColorOutput Yellow "💡 Verifique os logs acima para mais detalhes"
    exit 1
}
