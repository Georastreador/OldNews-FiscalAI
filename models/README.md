# 🤖 Modelos de IA - OldNews FiscalAI

Este diretório contém os modelos de inteligência artificial utilizados pelo sistema.

## 📋 Modelos Suportados

### 🏠 Modelos Locais

#### Mistral 7B Instruct
- **Arquivo**: `mistral-7b-instruct-v0.1.Q4_K_M.gguf`
- **Tamanho**: ~4.1GB
- **Formato**: GGUF (Quantizado)
- **Uso**: Análise de texto e classificação NCM

**Download:**
```bash
# Baixar modelo (não incluído no repositório por tamanho)
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf
```

### ☁️ Modelos em Nuvem

#### OpenAI
- **GPT-3.5-turbo**: Análise rápida e econômica
- **GPT-4**: Análise avançada e precisa
- **Configuração**: Via variável `OPENAI_API_KEY`

#### Anthropic
- **Claude-3-sonnet**: Análise equilibrada
- **Claude-3-opus**: Análise mais avançada
- **Configuração**: Via variável `ANTHROPIC_API_KEY`

#### Google
- **Gemini-pro**: Análise multimodal
- **Configuração**: Via variável `GOOGLE_API_KEY`

#### Groq
- **Llama-2-70b**: Análise rápida
- **Mixtral-8x7b**: Análise eficiente
- **Configuração**: Via variável `GROQ_API_KEY`

## ⚙️ Configuração

### 1. Modelo Local

```python
from src.utils.model_manager import get_model_manager

# Configurar modelo local
model_manager = get_model_manager()
llm = model_manager.get_llm("mistral-7b-local")
```

### 2. Modelo em Nuvem

```python
# Configurar OpenAI
llm = model_manager.get_llm("gpt-3.5-turbo")

# Configurar Anthropic
llm = model_manager.get_llm("claude-3-sonnet")

# Configurar Google
llm = model_manager.get_llm("gemini-pro")

# Configurar Groq
llm = model_manager.get_llm("llama-2-70b")
```

## 📊 Comparação de Modelos

| Modelo | Velocidade | Precisão | Custo | Privacidade |
|--------|------------|----------|-------|-------------|
| Mistral 7B Local | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| GPT-3.5-turbo | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| GPT-4 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Claude-3-sonnet | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Gemini-pro | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Llama-2-70b (Groq) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

## 🔧 Requisitos de Sistema

### Modelo Local (Mistral 7B)
- **RAM**: Mínimo 8GB, recomendado 16GB
- **Armazenamento**: 5GB livres
- **CPU**: Qualquer processador moderno
- **GPU**: Opcional, acelera inferência

### Modelos em Nuvem
- **Internet**: Conexão estável
- **API Keys**: Configuradas corretamente
- **Rate Limits**: Respeitar limites da API

## 🚀 Performance

### Tempos de Análise (NF-e típica)
- **Mistral 7B Local**: 30-60 segundos
- **GPT-3.5-turbo**: 10-20 segundos
- **GPT-4**: 20-40 segundos
- **Claude-3-sonnet**: 15-30 segundos
- **Gemini-pro**: 10-25 segundos
- **Llama-2-70b (Groq)**: 5-15 segundos

## 📝 Notas Importantes

1. **Modelos Locais**: Oferecem máxima privacidade mas requerem mais recursos
2. **Modelos em Nuvem**: Mais rápidos mas enviam dados para terceiros
3. **Custos**: Modelos em nuvem têm custos por token
4. **Rate Limits**: APIs têm limites de requisições por minuto
5. **Backup**: Sempre mantenha backup dos modelos locais

## 🔄 Atualizações

Para atualizar modelos:

```bash
# Atualizar dependências
pip install --upgrade -r requirements.txt

# Baixar novo modelo local
wget [URL_DO_NOVO_MODELO]

# Testar novo modelo
python -c "from src.utils.model_manager import get_model_manager; print('✅ OK')"
```

---

**Para mais informações, consulte a [documentação completa](../docs/configuration.md)**
