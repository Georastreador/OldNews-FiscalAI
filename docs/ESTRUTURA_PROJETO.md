# 📁 Estrutura do Projeto OldNews-FiscalAI

**Última atualização:** 29 de Outubro de 2025

---

## 📂 Estrutura de Diretórios

```
OldNews-FiscalAI/
├── config/                 # Arquivos de configuração
│   ├── app_config.py
│   ├── production.env.example
│   ├── pytest.ini
│   └── pyrightconfig.json
│
├── data/                   # Dados e amostras
│   ├── samples/            # Arquivos XML/CSV de exemplo
│   ├── tables/             # Tabelas de dados
│   └── validation/         # Dados de validação
│
├── docs/                   # Documentação
│   ├── corrections/        # Correções implementadas
│   ├── reports/            # Relatórios e análises
│   ├── GUIA_CONFIGURACAO_OPENAI.md
│   └── README.md
│
├── logs/                   # Logs da aplicação
│
├── models/                 # Modelos de IA locais
│   ├── mistral-7b-instruct-v0.1.Q4_K_M.gguf
│   └── README.md
│
├── scripts/                # Scripts de execução
│   ├── run_api.sh
│   ├── start_app.sh
│   └── start_fiscalai.sh
│
├── src/                    # Código-fonte principal
│   ├── agents/             # Agentes de IA
│   ├── api/                # API REST
│   ├── core/               # Classes base
│   ├── database/           # Banco de dados
│   ├── detectors/          # Detectores de fraude
│   ├── models/             # Modelos Pydantic
│   ├── security/           # Segurança
│   ├── utils/              # Utilitários
│   └── ...
│
├── tests/                  # Testes
│   ├── integration/        # Testes de integração
│   ├── unit/               # Testes unitários
│   ├── test_openai.py      # Teste com OpenAI
│   ├── test_performance.py # Teste de performance
│   └── README.md
│
├── ui/                     # Interface Streamlit
│   └── app.py
│
├── venv/                   # Ambiente virtual Python
│
├── LICENSE                  # Licença MIT
├── README.md               # Documentação principal
├── requirements.txt        # Dependências Python
└── main.py                 # Ponto de entrada principal
```

---

## 📋 Descrição dos Diretórios

### **config/**
Arquivos de configuração do projeto:
- `app_config.py` - Configurações da aplicação
- `production.env.example` - Exemplo de variáveis de ambiente
- `pytest.ini` - Configuração do pytest
- `pyrightconfig.json` - Configuração do Pyright (type checker)

### **data/**
Dados utilizados pela aplicação:
- `samples/` - Arquivos XML/CSV de exemplo para testes
- `tables/` - Tabelas de dados auxiliares
- `validation/` - Dados para validação e métricas

### **docs/**
Documentação completa do projeto:
- `corrections/` - Relatórios de correções implementadas
- `reports/` - Relatórios de testes, análises e auditorias
- `GUIA_CONFIGURACAO_OPENAI.md` - Guia de configuração da API OpenAI
- `README.md` - Documentação geral

### **scripts/**
Scripts de execução e automação:
- `run_api.sh` - Inicia a API REST
- `start_app.sh` - Inicia a aplicação Streamlit
- `start_fiscalai.sh` - Script de inicialização completo

### **src/**
Código-fonte principal organizado por módulos:

#### **agents/**
Agentes de IA baseados em CrewAI:
- `agente1_extrator.py` - Extração de dados
- `agente2_classificador.py` - Classificação de NCM
- `agente3_validador.py` - Validação e detecção de fraudes
- `agente4_orquestrador.py` - Orquestração do fluxo

#### **detectors/**
Detectores de fraudes especializados:
- `detector_ncm_incorreto.py`
- `detector_subfaturamento.py`
- `detector_triangulacao.py`
- `orquestrador_deteccao.py`

#### **utils/**
Utilitários diversos:
- `xml_parser_robusto.py` - Parser XML robusto
- `csv_encoding_detector.py` - Detecção de encoding CSV
- `nfse_multiple_parser.py` - Parser para múltiplas NFS-e
- `ncm_cfop_reader.py` - Leitor de tabelas NCM/CFOP

### **tests/**
Testes automatizados:
- `integration/` - Testes de integração
- `unit/` - Testes unitários
- `test_openai.py` - Teste com API OpenAI
- `test_performance.py` - Testes de performance

---

## 🗑️ Arquivos Removidos/Organizados

Durante a organização, os seguintes arquivos foram movidos ou removidos:

### **Movidos:**
- ✅ `test_openai.py` → `tests/test_openai.py`
- ✅ `start_app.sh` → `scripts/start_app.sh`
- ✅ `start_fiscalai.sh` → `scripts/start_fiscalai.sh`
- ✅ `RELATORIO_TESTES_COMPLETOS.md` → `docs/reports/RELATORIO_TESTES_COMPLETOS.md`
- ✅ `OldNews-FiscalAI.md` → `docs/reports/OldNews-FiscalAI.md`
- ✅ `ncm_cfop_reader.py` → `src/utils/ncm_cfop_reader.py`

### **Removidos (Duplicatas):**
- ❌ `pyrightconfig.json` (mantido em `config/`)
- ❌ `pytest.ini` (mantido em `config/`)
- ❌ `production.env.example` (mantido em `config/`)

### **Limpeza:**
- 🧹 Cache Python (`__pycache__/`) limpo
- 🧹 Arquivos `.pyc` removidos

---

## 📝 Convenções de Organização

### **Regras Gerais:**
1. **Código-fonte** → `src/`
2. **Testes** → `tests/`
3. **Scripts** → `scripts/`
4. **Documentação** → `docs/`
5. **Configuração** → `config/`
6. **Dados** → `data/`

### **Padrões de Nomenclatura:**
- **Arquivos Python:** `snake_case.py`
- **Scripts Shell:** `snake_case.sh`
- **Documentação:** `UPPER_SNAKE_CASE.md`
- **Configuração:** `snake_case.ext`

---

## 🚀 Como Usar a Estrutura

### **Executar Aplicação:**
```bash
# Usando scripts organizados
./scripts/start_app.sh
./scripts/run_api.sh
```

### **Executar Testes:**
```bash
# Testes unitários
pytest tests/unit/

# Testes de integração
pytest tests/integration/

# Teste específico
python tests/test_openai.py
```

### **Acessar Documentação:**
- Leia `README.md` para overview geral
- Consulte `docs/` para documentação detalhada
- Veja `docs/reports/` para relatórios e análises

---

## ✅ Checklist de Organização

- [x] Arquivos de teste movidos para `tests/`
- [x] Scripts movidos para `scripts/`
- [x] Documentação organizada em `docs/`
- [x] Configuração centralizada em `config/`
- [x] Duplicatas removidas
- [x] Cache Python limpo
- [x] Estrutura documentada

---

**Última organização realizada em 29 de Outubro de 2025**
