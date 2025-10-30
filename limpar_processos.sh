#!/bin/bash

# Script para limpar processos do FiscalAI
echo "🧹 Limpando processos do FiscalAI..."

# Parar processos Streamlit
echo "🛑 Parando processos Streamlit..."
pkill -f "streamlit run" 2>/dev/null || true

# Aguardar um pouco
sleep 2

# Verificar se a porta 8501 está livre
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Porta 8501 ainda está em uso"
    echo "💡 Execute: lsof -i :8501 para ver quais processos estão usando"
else
    echo "✅ Porta 8501 liberada"
fi

echo "✅ Limpeza concluída"
