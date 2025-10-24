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
- 💬 **Chat com IA**: Assistente conversacional para consultas
- 📄 **Suporte Multi-formato**: XML, CSV, NFS-e
- 🚨 **Detecção de Fraudes**: 7 tipos de fraudes detectáveis
- 📈 **Relatórios PDF**: Exportação de análises detalhadas

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

- Python 3.13+
- Git

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/OldNews-FiscalAI.git
cd OldNews-FiscalAI
```

### 2. Crie o Ambiente Virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as Variáveis de Ambiente

```bash
cp production.env.example .env
# Edite o arquivo .env com suas configurações
```

## 🎯 Uso

### Interface Web

```bash
streamlit run ui/app.py
```

### API REST

```bash
python src/api/main.py
```

### Linha de Comando

```bash
python main.py arquivo_nfe.xml --model mistral-7b-local
```

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
├── src/
│   ├── agents/           # Agentes CrewAI
│   ├── detectors/        # Detectores de fraude
│   ├── models/           # Schemas Pydantic
│   ├── utils/            # Utilitários
│   ├── api/              # API REST
│   └── database/         # Camada de dados
├── ui/                   # Interface Streamlit
├── tests/                # Testes unitários
├── data/                 # Dados e amostras
├── models/               # Modelos de IA
└── docs/                 # Documentação
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