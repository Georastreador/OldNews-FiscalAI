# 🚀 OldNews FiscalAI

**Sistema Inteligente de Análise Fiscal de NF-e**

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.50.0-red.svg)](https://streamlit.io)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.203.1-green.svg)](https://crewai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Visão Geral

O **OldNews FiscalAI** é um sistema avançado de análise fiscal que utiliza inteligência artificial para detectar fraudes em Notas Fiscais Eletrônicas (NF-e) e documentos fiscais relacionados. O sistema emprega uma arquitetura multi-agente com CrewAI para análise inteligente e detecção de padrões suspeitos.

## ✨ Funcionalidades

- 🔍 **Análise Inteligente**: Detecção automática de fraudes fiscais
- 🤖 **Sistema Multi-Agente**: 5 agentes especializados com CrewAI
- 📊 **Dashboard Interativo**: Interface web moderna com Streamlit
- 💬 **Chat Inteligente V2**: Assistente conversacional com consultas diretas aos dados brutos
- 🔒 **Interface de Privacidade**: Escolha entre modelos locais (100% privado) ou APIs externas
- 📄 **Suporte Multi-formato**: XML, CSV, NFS-e com processamento de múltiplas NFs
- 🚨 **Detecção de Fraudes**: 7 tipos de fraudes detectáveis
- 📈 **Relatórios TXT**: Exportação de análises detalhadas em formato texto
- 🔒 **Validação XML Schema**: Verificação de conformidade com schemas oficiais
- ⚡ **Cache Inteligente**: Sistema de cache para otimização de performance
- 🛡️ **Segurança Avançada**: Headers de segurança, rate limiting e auditoria
- 🚀 **Scripts de Execução**: Instalação e execução automatizada para usuários não-técnicos

## 🏗️ Arquitetura

### Sistema Multi-Agente

```
OldNews FiscalAI/
├── 🤖 Agente 1: Extrator de Dados
├── 🏷️ Agente 2: Classificador NCM
├── ✅ Agente 3: Validador Fiscal
├── 🎯 Agente 4: Orquestrador
└── 💬 Agente 5: Interface Conversacional
```

### Detectores de Fraude

- **Subfaturamento**: Detecção de valores abaixo do mercado
- **NCM Incorreto**: Classificação fiscal inadequada
- **Triangulação**: Operações suspeitas entre empresas
- **Fracionamento**: Divisão artificial de operações
- **Fornecedor de Risco**: Análise de histórico de fornecedores
- **Anomalia Temporal**: Padrões temporais suspeitos
- **Valor Inconsistente**: Inconsistências nos cálculos

## 🚀 Instalação

### Pré-requisitos

- Python 3.11+ (recomendado: 3.13)
- Git
- 8GB RAM (mínimo)
- 10GB espaço livre

### ⚡ Instalação Rápida

#### **Opção 1: Script Automático (Recomendado para Usuários Não-Técnicos)**

```bash
# 1. Clone o repositório
git clone https://github.com/Georastreador/OldNews-FiscalAI.git
cd OldNews-FiscalAI

# 2. Execute o script automático
# Linux/macOS:
./executar_aplicacao.sh

# Windows:
INICIAR_APLICACAO.bat
# ou
INICIAR_APLICACAO.ps1
```

**O script automático:**
- ✅ Cria e ativa o ambiente virtual
- ✅ Instala todas as dependências
- ✅ Configura arquivos .env automaticamente
- ✅ Verifica portas e processos
- ✅ Inicia a aplicação automaticamente

#### **Opção 2: Manual (Para Desenvolvedores)**

```bash
# 1. Clone o repositório
git clone https://github.com/Georastreador/OldNews-FiscalAI.git
cd OldNews-FiscalAI

# 2. Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp config/env.example .env
# Edite o arquivo .env com suas configurações

# Para OpenAI (recomendado)
export OPENAI_API_KEY="sua_chave_aqui"
```

## 🎯 Uso

### 🚀 Início Rápido (Recomendado)

```bash
# Execução automática completa
./executar_aplicacao.sh
```

### Interface Web

```bash
# Linux/macOS
./run_ui.sh

# Windows
INICIAR_APLICACAO.bat
# ou
INICIAR_APLICACAO.ps1
```

### API REST

```bash
./run_api.sh
```

### Manual

```bash
source venv/bin/activate
streamlit run ui/app.py
```

### Linha de Comando

```bash
python main.py arquivo_nfe.xml --model mistral-7b-local
```

## 💬 Chat Inteligente V2

O sistema inclui um assistente conversacional avançado que pode responder consultas diretas sobre os dados carregados:

### Exemplos de Consultas

- **"Quantas NFs foram analisadas?"**
- **"Qual o valor total das NFs?"**
- **"Quantas NFs estão entre R$ 500 e R$ 1000?"**
- **"Quais fraudes foram detectadas?"**
- **"Quantos itens tem cada NF?"**
- **"Quais CNPJs estão nas NFs?"**
- **"Qual o período das NFs?"**

### Interface de Privacidade

- 🏠 **Modelo Local**: 100% privado, gratuito, offline
- 🌐 **API Externa**: Modelos avançados (OpenAI, Anthropic, Google, Groq)
- 🔄 **Troca Fácil**: Botão de reinicialização para mudar de modelo

## 📊 Exemplo de Uso

```python
from src.agents import Agente4Orquestrador
from src.utils import get_model_manager

# Configurar modelo
model_manager = get_model_manager()
llm = model_manager.get_llm("mistral-7b-local")

# Criar orquestrador
orquestrador = Agente4Orquestrador(llm)

# Analisar NF-e
relatorio = orquestrador.executar_fluxo_completo(
    xml_path="nfe_exemplo.xml"
)

print(f"Score de Risco: {relatorio.resultado_analise.score_risco_geral}")
print(f"Fraudes Detectadas: {len(relatorio.resultado_analise.fraudes_detectadas)}")
```

## 🛠️ Tecnologias

- **Python 3.13** - Linguagem principal
- **Streamlit** - Interface web
- **CrewAI** - Sistema multi-agente
- **FastAPI** - API REST
- **Pydantic** - Validação de dados
- **LangChain** - Integração com LLMs
- **Mistral 7B** - Modelo de IA local
- **Pandas** - Processamento de dados
- **NetworkX** - Análise de grafos

## 📁 Estrutura do Projeto

```
OldNews-FiscalAI/
├── src/                  # Código fonte principal
│   ├── agents/           # Agentes CrewAI (5 agentes especializados)
│   ├── detectors/        # Detectores de fraude (7 tipos)
│   ├── models/           # Schemas Pydantic
│   ├── utils/            # Utilitários e helpers
│   ├── api/              # API REST com FastAPI
│   ├── database/         # Camada de dados
│   ├── security/         # Módulos de segurança
│   ├── analysis/         # Análises temporais
│   ├── calibration/      # Calibração de thresholds
│   ├── learning/         # Sistema de aprendizado
│   ├── ml/               # Machine Learning
│   ├── training/         # Treinamento de modelos
│   └── validation/       # Validações
├── ui/                   # Interface Streamlit
├── tests/                # Testes unitários e integração
├── data/                 # Dados e amostras
│   ├── samples/          # Arquivos de exemplo
│   ├── tables/           # Tabelas de referência
│   └── validation/       # Dados de validação
├── models/               # Modelos de IA locais
├── config/               # Configurações e exemplos
│   ├── env.example       # Exemplo de variáveis de ambiente
│   └── production.env.example
├── docs/                 # Documentação
├── scripts/              # Scripts de execução
├── cache/                # Cache de resultados
├── logs/                 # Logs do sistema
├── security/             # Schemas e auditoria
├── executar_aplicacao.sh # Script principal de execução
├── run_ui.sh            # Script para interface web
├── run_api.sh           # Script para API REST
├── INICIAR_APLICACAO.bat # Script Windows
├── INICIAR_APLICACAO.ps1 # Script PowerShell
├── requirements.txt      # Dependências Python
├── requirements_working.txt # Versões funcionais
└── README.md            # Este arquivo
```

## 🔧 Configuração

### Modelos de IA Suportados

- **Local**: Mistral 7B (GGUF)
- **OpenAI**: GPT-3.5, GPT-4
- **Anthropic**: Claude
- **Google**: Gemini
- **Groq**: Llama, Mixtral

### Variáveis de Ambiente

```env
# OpenAI
OPENAI_API_KEY=your_key_here

# Anthropic
ANTHROPIC_API_KEY=your_key_here

# Google
GOOGLE_API_KEY=your_key_here

# Groq
GROQ_API_KEY=your_key_here
```

## 📈 Performance

- **Tempo de Análise**: ~30-60 segundos por NF-e
- **Precisão**: 95%+ na detecção de fraudes
- **Suporte**: Até 1000 itens por NF-e
- **Concorrência**: Análise paralela de múltiplas NF-e
- **Cache**: Redução de 70% no tempo de reprocessamento
- **Validação**: Verificação XML Schema em <5 segundos
- **Chat V2**: Respostas instantâneas com acesso direto aos dados

## 🧪 Testes

```bash
# Executar testes
pytest tests/

# Teste de performance
python tests/test_performance.py

# Teste de integridade
python -c "from src.models import *; print('✅ OK')"
```

## 📚 Documentação

### **Guias Principais**
- [🚀 Scripts de Execução](SCRIPTS_EXECUCAO.md) - Como usar todos os scripts
- [🪟 Como Usar no Windows](COMO_USAR_WINDOWS.md) - Guia completo para Windows
- [🔒 Interface de Privacidade](INTERFACE_PRIVACIDADE.md) - Configuração de modelos

### **Documentação Técnica**
- [📖 Guia de Instalação](docs/installation.md)
- [🎯 Guia de Uso](docs/usage.md)
- [🔧 Configuração Avançada](docs/configuration.md)
- [🤖 Agentes](docs/agents.md)
- [🚨 Detectores](docs/detectors.md)
- [📊 API](docs/api.md)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- **Ricardo Croce** - *Desenvolvimento Principal* - [GitHub](https://github.com/Georastreador)

## 🙏 Agradecimentos

- CrewAI pela framework multi-agente
- Streamlit pela interface web
- Comunidade Python pelo suporte
- Contribuidores do projeto

## 📞 Suporte

- 📧 Email: ursodecasaco@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/seu-usuario/OldNews-FiscalAI/issues)
- 💬 Discussões: [GitHub Discussions](https://github.com/seu-usuario/OldNews-FiscalAI/discussions)

---

**Desenvolvido com ❤️ para análise fiscal inteligente**

[⬆ Voltar ao topo](#-oldnews-fiscalai)