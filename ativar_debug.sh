#!/bin/bash

# Script para ativar debug temporário no FiscalAI MVP
# Uso: ./ativar_debug.sh [nivel]
# Níveis: 1=essencial, 2=detalhado, 3=completo

NIVEL=${1:-2}

echo "🔍 Ativando debug temporário do FiscalAI MVP..."
echo "📊 Nível de debug: $NIVEL"

# Exportar variáveis de ambiente para debug
export FISCALAI_DEBUG=true
export FISCALAI_DEBUG_LEVEL=$NIVEL
export FISCALAI_DEBUG_ORQUESTRADOR=true
export FISCALAI_DEBUG_NCM=true
export FISCALAI_DEBUG_VALOR=true
export FISCALAI_DEBUG_STREAMLIT=true
export FISCALAI_DEBUG_PERFORMANCE=true

echo "✅ Debug ativado!"
echo ""
echo "Para executar com debug:"
echo "  python main.py"
echo "  streamlit run ui/app.py"
echo ""
echo "Para desativar debug:"
echo "  unset FISCALAI_DEBUG"
echo "  unset FISCALAI_DEBUG_LEVEL"
echo ""

# Executar o comando passado como argumento adicional
if [ $# -gt 1 ]; then
    shift
    echo "🚀 Executando: $@"
    exec "$@"
fi
