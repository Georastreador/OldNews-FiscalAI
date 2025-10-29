# 🔑 GUIA DE CONFIGURAÇÃO DO OPENAI - FISCALAI MVP

## ✅ **CONFIGURAÇÃO NECESSÁRIA PARA TESTE**

Para executar o teste com múltiplas notas CSV e OpenAI, você precisa configurar sua chave de API do OpenAI.

## 🔑 **1. OBTER CHAVE DE API DO OPENAI**

### **Passo 1: Acessar OpenAI**
1. Acesse: https://platform.openai.com/
2. Faça login ou crie uma conta
3. Vá para "API Keys" no menu lateral

### **Passo 2: Criar Nova Chave**
1. Clique em "Create new secret key"
2. Dê um nome para a chave (ex: "FiscalAI-MVP")
3. Copie a chave gerada (começa com `sk-`)

⚠️ **IMPORTANTE**: Salve a chave em local seguro, ela não será mostrada novamente!

## 🔧 **2. CONFIGURAR NO SISTEMA**

### **Opção A: Variável de Ambiente (Recomendado)**
```bash
# No terminal (Mac/Linux)
export OPENAI_API_KEY='sk-sua_chave_aqui'

# Para tornar permanente (adicionar ao ~/.bashrc ou ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-sua_chave_aqui"' >> ~/.zshrc
source ~/.zshrc
```

### **Opção B: Arquivo .env**
```bash
# Criar arquivo .env na raiz do projeto
echo 'OPENAI_API_KEY=sk-sua_chave_aqui' > .env
```

### **Opção C: Interface Streamlit**
1. Acesse a interface do FiscalAI
2. Vá para "🔑 Configurar APIs"
3. Cole sua chave no campo "OpenAI API Key"
4. Clique em "Salvar Configurações"

## 🧪 **3. TESTAR CONFIGURAÇÃO**

### **Teste Rápido:**
```bash
# Ativar ambiente virtual
source fiscalai_env/bin/activate

# Executar teste
python FiscalAI_MVP/teste_multiplas_notas_csv.py
```

### **Teste na Interface:**
1. Execute: `streamlit run FiscalAI_MVP/ui/app.py`
2. No sidebar, selecione "☁️ API Externa"
3. Escolha "GPT-4o Mini (OpenAI)"
4. Faça upload do CSV criado
5. Execute a análise

## 💰 **4. CUSTOS E LIMITES**

### **Modelos Disponíveis:**
- **GPT-4o Mini**: $0.15/1M tokens (Recomendado para testes)
- **GPT-4o**: $2.50/1M tokens (Alta qualidade)

### **Estimativa de Custo para Teste:**
- **5 notas CSV**: ~$0.01-0.05 (muito baixo)
- **Análise completa**: ~$0.10-0.50 (dependendo do modelo)

### **Limites Gratuitos:**
- Contas novas têm $5 de crédito gratuito
- Suficiente para centenas de testes

## 🚀 **5. EXECUTAR TESTE COMPLETO**

### **Arquivo CSV Criado:**
- **Nome**: `multiplas_notas_exemplo_20251024_090155.csv`
- **Notas**: 5 notas fiscais diferentes
- **Cenários**: Consulta médica, medicamento, eletrônico suspeito, NCM incorreto, consultoria

### **Passos:**
1. ✅ Configure a chave OpenAI
2. ✅ Execute: `streamlit run FiscalAI_MVP/ui/app.py`
3. ✅ Vá para "📤 Analisar NF-e"
4. ✅ Selecione "📊 CSV (Dados Fiscais)"
5. ✅ Faça upload do arquivo CSV
6. ✅ Configure modelo OpenAI no sidebar
7. ✅ Clique "🚀 Executar CSV!"

## 🎯 **6. RESULTADOS ESPERADOS**

### **Análises dos Agentes:**
- **Agente 1**: Extração de dados das 5 notas
- **Agente 2**: Classificação NCM automática
- **Agente 3**: Validação fiscal
- **Agente 4**: Orquestração e relatório

### **Fraudes Detectadas:**
- **Nota 3**: Smartphone com valor suspeitamente baixo (R$ 500)
- **Nota 4**: NCM incorreto para camiseta (12345678 vs 61091000)

### **Chat com IA:**
- Respostas de alta qualidade do OpenAI
- Análise detalhada de cada nota
- Explicações técnicas claras

## 🔧 **7. SOLUÇÃO DE PROBLEMAS**

### **Erro: "OPENAI_API_KEY não configurada"**
```bash
# Verificar se a variável está definida
echo $OPENAI_API_KEY

# Se vazio, configurar novamente
export OPENAI_API_KEY='sk-sua_chave_aqui'
```

### **Erro: "Invalid API key"**
- Verifique se a chave começa com `sk-`
- Confirme se a chave está ativa no painel OpenAI
- Verifique se há créditos disponíveis

### **Erro: "Rate limit exceeded"**
- Aguarde alguns minutos
- Considere usar GPT-4o Mini (mais barato)
- Verifique limites da sua conta

## 📊 **8. MONITORAMENTO DE USO**

### **Painel OpenAI:**
1. Acesse: https://platform.openai.com/usage
2. Monitore tokens usados
3. Acompanhe custos em tempo real

### **Logs do FiscalAI:**
- O sistema mostra tokens usados
- Estimativa de custo por análise
- Histórico de uso

## 🎉 **PRONTO PARA TESTAR!**

Com a configuração do OpenAI, você terá:
- ✅ **Análises de alta qualidade** com GPT-4o
- ✅ **Classificação NCM precisa** 
- ✅ **Detecção avançada de fraudes**
- ✅ **Chat inteligente** com respostas detalhadas
- ✅ **Relatórios profissionais**

**🚀 Execute o teste e veja a diferença na qualidade das análises!**
