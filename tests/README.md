# 🧪 Testes - OldNews FiscalAI

Esta pasta contém todos os testes do projeto OldNews FiscalAI.

## 📁 Estrutura

### 🔬 **unit/**
Testes unitários para componentes individuais do sistema.

- `test_performance.py` - Testes de performance do sistema
- Outros testes unitários conforme necessário

### 🔗 **integration/**
Testes de integração para verificar funcionamento conjunto dos componentes.

- Testes de integração entre agentes
- Testes de fluxo completo de análise
- Testes de API e interface

## 🚀 **Como Executar Testes**

### **Testes Unitários**
```bash
# Executar todos os testes unitários
python -m pytest tests/unit/ -v

# Executar teste específico
python -m pytest tests/unit/test_performance.py -v
```

### **Testes de Integração**
```bash
# Executar todos os testes de integração
python -m pytest tests/integration/ -v
```

### **Todos os Testes**
```bash
# Executar todos os testes
python -m pytest tests/ -v

# Com cobertura
python -m pytest tests/ --cov=src --cov-report=html
```

## 📋 **Tipos de Teste**

### **Testes Unitários**
- ✅ Testes de parsers XML/CSV
- ✅ Testes de detectores de fraude
- ✅ Testes de agentes individuais
- ✅ Testes de validação de dados
- ✅ Testes de performance

### **Testes de Integração**
- ✅ Testes de fluxo completo de análise
- ✅ Testes de interface web
- ✅ Testes de API REST
- ✅ Testes de múltiplas notas
- ✅ Testes de diferentes tipos de documento

## 🎯 **Cobertura de Testes**

O objetivo é manter uma cobertura de testes de pelo menos **80%** para:
- Código crítico (parsers, detectores, agentes)
- Lógica de negócio
- Validações de dados
- Tratamento de erros

## 📝 **Convenções**

### **Nomenclatura**
- **Testes unitários**: `test_*.py`
- **Testes de integração**: `test_integration_*.py`
- **Testes de performance**: `test_performance_*.py`

### **Estrutura de Teste**
```python
def test_nome_do_teste():
    """Descrição do que o teste verifica"""
    # Arrange
    setup_data = criar_dados_teste()
    
    # Act
    resultado = funcao_sob_teste(setup_data)
    
    # Assert
    assert resultado == resultado_esperado
```

## 🔧 **Configuração**

### **Dependências de Teste**
```bash
pip install pytest pytest-cov pytest-mock
```

### **Variáveis de Ambiente**
Crie um arquivo `.env.test` para testes:
```env
# Configurações específicas para testes
TEST_MODE=true
MOCK_LLM=true
```

## 📊 **Relatórios**

### **Cobertura HTML**
```bash
python -m pytest tests/ --cov=src --cov-report=html
# Abra htmlcov/index.html no navegador
```

### **Relatório XML**
```bash
python -m pytest tests/ --cov=src --cov-report=xml
# Gera coverage.xml para CI/CD
```

## 🚨 **Testes Críticos**

### **Deve Sempre Passar**
- ✅ Parser de múltiplas NFS-e
- ✅ Detecção de codificação CSV
- ✅ Validação de CNPJ/CPF
- ✅ Detecção de fraudes básicas
- ✅ Interface web carrega

### **Performance Esperada**
- ✅ Análise de NF-e única: < 30 segundos
- ✅ Análise de múltiplas NFS-e: < 2 minutos
- ✅ Upload de arquivo: < 5 segundos
- ✅ Geração de relatório: < 10 segundos

---

**📅 Última atualização:** 24 de Janeiro de 2025  
**👨‍💻 Mantido por:** Equipe OldNews FiscalAI
