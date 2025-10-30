# 🪟 Como Usar no Windows - OldNews FiscalAI

## 📋 Visão Geral

Este guia explica como usar o OldNews FiscalAI no Windows, desde a instalação até a execução da aplicação.

## 🚀 Instalação Rápida

### **Opção 1: Duplo-Clique (Mais Fácil)**

1. **Baixe o projeto:**
   ```cmd
   git clone https://github.com/Georastreador/OldNews-FiscalAI.git
   cd OldNews-FiscalAI
   ```

2. **Execute o script:**
   - Duplo-clique em `INICIAR_APLICACAO.bat`
   - Aguarde a instalação automática
   - A aplicação abrirá no navegador

### **Opção 2: PowerShell (Recomendado)**

1. **Abra PowerShell como Administrador**

2. **Navegue até o projeto:**
   ```powershell
   cd C:\caminho\para\OldNews-FiscalAI
   ```

3. **Execute o script:**
   ```powershell
   .\INICIAR_APLICACAO.ps1
   ```

## 🔧 Pré-requisitos

### **Python 3.11+ (Obrigatório)**

1. **Baixe Python:**
   - Acesse: https://python.org/downloads
   - Baixe Python 3.11 ou superior
   - **IMPORTANTE:** Marque "Add Python to PATH"

2. **Verifique a instalação:**
   ```cmd
   python --version
   ```

### **Git (Opcional, mas recomendado)**

1. **Baixe Git:**
   - Acesse: https://git-scm.com/download/win
   - Instale com configurações padrão

## 🎯 Uso da Aplicação

### **1. Interface de Privacidade**

Na barra lateral, você pode escolher:

#### **🏠 Modelo Local (Recomendado para iniciantes)**
- ✅ **100% Privado** - Dados não saem do seu computador
- ✅ **Gratuito** - Sem custos de API
- ✅ **Offline** - Funciona sem internet
- ⚠️ **Mais lento** - Processamento local

#### **🌐 API Externa (Para usuários avançados)**
- ✅ **Mais rápido** - Processamento na nuvem
- ✅ **Mais preciso** - Modelos avançados
- ⚠️ **Requer API key** - Configuração necessária
- ⚠️ **Custos** - Pode ter custos por uso

### **2. Configuração de API Externa**

Se escolher API Externa:

1. **Selecione o provedor:**
   - OpenAI (GPT-4o, GPT-4o Mini)
   - Anthropic (Claude 3.5 Sonnet)
   - Google (Gemini 1.5 Pro)
   - Groq (Llama 3.1 8B)

2. **Insira sua API key:**
   - Cole a chave no campo de entrada
   - Clique em "🧪 Testar API"
   - Aguarde a confirmação

3. **Obter API keys:**
   - **OpenAI:** https://platform.openai.com/account/api-keys
   - **Anthropic:** https://console.anthropic.com/
   - **Google:** https://makersuite.google.com/app/apikey
   - **Groq:** https://console.groq.com/keys

### **3. Chat Inteligente**

O chat pode responder perguntas como:

- **"Quantas NFs foram analisadas?"**
- **"Qual o valor total das NFs?"**
- **"Quantas NFs estão entre R$ 500 e R$ 1000?"**
- **"Quais fraudes foram detectadas?"**
- **"Quantos itens tem cada NF?"**

## 📁 Estrutura de Arquivos

```
OldNews-FiscalAI/
├── INICIAR_APLICACAO.bat     # Script principal (duplo-clique)
├── INICIAR_APLICACAO.ps1     # Script PowerShell
├── config/
│   ├── env.example           # Configuração de exemplo
│   └── production.env.example
├── ui/
│   └── app.py                # Interface web
├── src/                      # Código fonte
├── models/                   # Modelos de IA locais
├── data/                     # Dados de exemplo
└── venv/                     # Ambiente virtual Python
```

## 🚨 Solução de Problemas

### **Erro: "Python não encontrado"**

1. **Verifique se Python está instalado:**
   ```cmd
   python --version
   ```

2. **Se não estiver instalado:**
   - Baixe de https://python.org
   - **IMPORTANTE:** Marque "Add Python to PATH"

3. **Se estiver instalado mas não encontrado:**
   - Reinstale Python marcando "Add Python to PATH"
   - Reinicie o prompt de comando

### **Erro: "Permissão negada"**

1. **Execute como Administrador:**
   - Clique com botão direito no arquivo .bat
   - Selecione "Executar como administrador"

2. **Ou use PowerShell:**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\INICIAR_APLICACAO.ps1
   ```

### **Erro: "Porta 8501 em uso"**

1. **Feche outros programas** que usam a porta 8501
2. **Reinicie o computador** se necessário
3. **Use o script de limpeza:**
   ```cmd
   taskkill /f /im python.exe
   ```

### **Erro: "Dependências faltando"**

1. **Execute o script completo:**
   ```cmd
   INICIAR_APLICACAO.bat
   ```

2. **Ou instale manualmente:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

### **Aplicação não abre no navegador**

1. **Acesse manualmente:**
   - Abra o navegador
   - Vá para: http://localhost:8501

2. **Verifique se a aplicação está rodando:**
   - Olhe na janela do terminal
   - Deve aparecer "You can now view your Streamlit app"

## 🔄 Atualizações

### **Atualizar o projeto:**
```cmd
git pull origin main
```

### **Reinstalar dependências:**
```cmd
rmdir /s venv
INICIAR_APLICACAO.bat
```

## 📞 Suporte

### **Se precisar de ajuda:**

1. **Verifique os logs** na janela do terminal
2. **Consulte a documentação** em `docs/`
3. **Abra uma issue** no GitHub
4. **Entre em contato:** ursodecasaco@gmail.com

### **Informações úteis para suporte:**

- Versão do Windows
- Versão do Python (`python --version`)
- Mensagem de erro completa
- Logs da aplicação

## 🎉 Pronto!

Agora você pode usar o OldNews FiscalAI no Windows! 

**Lembre-se:**
- ✅ Mantenha a janela do terminal aberta
- ✅ Configure sua API key se usar API externa
- ✅ Use Ctrl+C para parar a aplicação
- ✅ Acesse http://localhost:8501 no navegador

---

**Desenvolvido com ❤️ para análise fiscal inteligente no Windows**
