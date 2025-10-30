# 🚀 Guia de Instalação - OldNews FiscalAI

## 📋 Pré-requisitos

### **Sistema Operacional**
- ✅ **Windows 10/11**
- ✅ **macOS 10.15+**
- ✅ **Linux Ubuntu 20.04+**

### **Software Necessário**
- ✅ **Python 3.11+** (recomendado: 3.13)
- ✅ **Git** (para clonar o repositório)
- ✅ **8GB RAM** (mínimo)
- ✅ **10GB espaço livre** (para modelo IA)

---

## 🔧 Instalação Rápida

### **1. Clonar Repositório**
```bash
git clone https://github.com/seu-usuario/OldNews-FiscalAI.git
cd OldNews-FiscalAI
```

### **2. Criar Ambiente Virtual**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### **3. Instalar Dependências**
```bash
pip install -r requirements.txt
```

### **4. Configurar Variáveis de Ambiente**
```bash
# Copiar arquivo de exemplo
cp config/production.env.example .env

# Editar com suas configurações
# Adicionar sua API Key da OpenAI
```

### **5. Executar Aplicação**

#### **Opção A: Script Automático (Recomendado)**
```bash
# Windows
INICIAR_APLICACAO.bat

# macOS/Linux
./executar_aplicacao.sh
```

#### **Opção B: Manual**
```bash
# Interface Web
streamlit run ui/app.py

# API REST
python src/api/main.py
```

---

## ⚙️ Configuração Detalhada

### **1. Configuração da OpenAI**

Edite o arquivo `.env`:
```env
OPENAI_API_KEY=sk-proj-sua-chave-aqui
OPENAI_MODEL=gpt-3.5-turbo
```

### **2. Configuração de Modelo Local (Opcional)**

Para usar modelo local Mistral:
```bash
# Baixar modelo (4.3GB)
# Colocar em models/mistral-7b-instruct-v0.1.Q4_K_M.gguf
```

### **3. Configuração de Banco de Dados**

O banco SQLite será criado automaticamente em `data/ncm_database.db`

---

## 🧪 Teste da Instalação

### **Teste Rápido**
```bash
python -c "from src.models.schemas import NFe; print('✅ Instalação OK')"
```

### **Teste Completo**
```bash
# Executar testes
pytest tests/

# Teste com OpenAI
python tests/test_openai.py
```

---

## 🚨 Solução de Problemas

### **Erro: "Python não encontrado"**
```bash
# Instalar Python
# Windows: https://python.org
# macOS: brew install python3
# Ubuntu: sudo apt install python3
```

### **Erro: "Módulo não encontrado"**
```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### **Erro: "OpenAI API Key"**
```bash
# Verificar arquivo .env
# Adicionar OPENAI_API_KEY=sk-proj-...
```

### **Erro: "Streamlit não encontrado"**
```bash
# Instalar Streamlit
pip install streamlit
```

---

## 📱 Uso da Aplicação

### **1. Acessar Interface**
- Abra: http://localhost:8501
- Upload de arquivos XML/CSV
- Análise automática com IA

### **2. Configurar APIs**
- Vá para "Configurar APIs"
- Adicione sua chave OpenAI
- Salve configurações

### **3. Processar Arquivos**
- Upload de NF-e XML
- Upload de CSV
- Visualizar resultados
- Baixar relatórios

---

## 🔧 Desenvolvimento

### **Estrutura do Projeto**
```
OldNews-FiscalAI/
├── src/           # Código-fonte
├── ui/            # Interface Streamlit
├── tests/         # Testes
├── docs/          # Documentação
├── config/        # Configurações
└── scripts/       # Scripts de execução
```

### **Executar em Modo Desenvolvimento**
```bash
# Ativar debug
export DEBUG=True
streamlit run ui/app.py
```

---

## 📞 Suporte

### **Documentação**
- `README.md` - Visão geral
- `docs/` - Documentação detalhada
- `docs/ESTRUTURA_PROJETO.md` - Estrutura do projeto

### **Problemas Conhecidos**
- Modelo local requer 8GB+ RAM
- OpenAI API tem limites de uso
- Arquivos XML muito grandes podem ser lentos

### **Contato**
- Issues: GitHub Issues
- Documentação: `docs/`
- Logs: `logs/`

---

## ✅ Checklist de Instalação

- [ ] Python 3.11+ instalado
- [ ] Repositório clonado
- [ ] Ambiente virtual criado
- [ ] Dependências instaladas
- [ ] Arquivo .env configurado
- [ ] API Key OpenAI adicionada
- [ ] Aplicação executando
- [ ] Interface acessível
- [ ] Teste realizado

---

**Última atualização:** 29 de Outubro de 2025
