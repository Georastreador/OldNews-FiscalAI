# 🔄 Refatoração de Orientação a Objeto - OldNews FiscalAI

## 📋 Resumo

Esta documentação descreve a refatoração completa da estrutura de orientação a objeto da aplicação OldNews FiscalAI, implementando princípios SOLID e boas práticas de OOP.

## ❌ Problemas Identificados na Estrutura Original

### 1. **Falta de Herança Adequada**
- Classes dos agentes não herdam de uma classe base comum
- Detectores não seguem um padrão de herança
- Parsers não compartilham interface comum

### 2. **Encapsulamento Inadequado**
- Muitos atributos públicos que deveriam ser privados
- Falta de propriedades (getters/setters)
- Acesso direto a atributos internos

### 3. **Falta de Interfaces/Abstrações**
- Não há interfaces definidas para agentes
- Detectores não implementam interface comum
- Parsers não seguem contrato comum

### 4. **Violação do Princípio da Responsabilidade Única**
- Classes com múltiplas responsabilidades
- Métodos muito longos e complexos

### 5. **Falta de Polimorfismo**
- Código duplicado entre classes similares
- Não há uso adequado de polimorfismo

## ✅ Solução Implementada

### 1. **Estrutura de Classes Base**

#### **Interfaces (`src/core/interfaces.py`)**
```python
class IAgent(ABC):
    @abstractmethod
    def executar(self, *args, **kwargs) -> Any: pass
    
    @abstractmethod
    def validar_entrada(self, *args, **kwargs) -> bool: pass
    
    @abstractmethod
    def obter_resultado(self) -> Any: pass

class IDetector(ABC):
    @abstractmethod
    def detectar(self, item: ItemNFe, nfe: NFe) -> Optional[DeteccaoFraude]: pass
    
    @abstractmethod
    def analisar_nfe(self, nfe: NFe, classificacoes: Optional[Dict[int, ClassificacaoNCM]] = None) -> List[DeteccaoFraude]: pass

class IParser(ABC):
    @abstractmethod
    def parse_file(self, file_path: str) -> Union[NFe, List[NFe], Tuple[Any, str, str]]: pass
```

#### **Classes Base (`src/core/base_*.py`)**
- `BaseAgent`: Classe base para todos os agentes
- `BaseDetector`: Classe base para todos os detectores
- `BaseParser`: Classe base para todos os parsers

### 2. **Princípios SOLID Implementados**

#### **S - Single Responsibility Principle**
- Cada classe tem uma única responsabilidade
- `Agente2Classificador`: apenas classificação NCM
- `DetectorSubfaturamento`: apenas detecção de subfaturamento

#### **O - Open/Closed Principle**
- Classes abertas para extensão, fechadas para modificação
- Novos detectores podem herdar de `BaseDetector`
- Novos agentes podem herdar de `BaseAgent`

#### **L - Liskov Substitution Principle**
- Subclasses podem substituir suas classes base
- `Agente2Classificador` pode ser usado onde `IAgent` é esperado

#### **I - Interface Segregation Principle**
- Interfaces específicas e focadas
- `IAgent`, `IDetector`, `IParser` são interfaces distintas

#### **D - Dependency Inversion Principle**
- Dependências de abstrações, não de implementações concretas
- Uso de interfaces em vez de classes concretas

### 3. **Encapsulamento Adequado**

#### **Atributos Privados**
```python
class BaseAgent:
    def __init__(self, llm: Any, role: str, goal: str, backstory: str):
        self._llm = llm  # Privado
        self._role = role  # Privado
        self._resultado = None  # Privado
```

#### **Propriedades (Getters/Setters)**
```python
@property
def llm(self) -> Any:
    """Obtém o modelo de linguagem"""
    return self._llm

@resultado.setter
def resultado(self, value: Any) -> None:
    """Define o resultado da execução"""
    self._resultado = value
```

#### **Validação Automática**
```python
@threshold_score_minimo.setter
def threshold_score_minimo(self, value: int) -> None:
    if not 0 <= value <= 100:
        raise ValueError("Threshold de score deve estar entre 0 e 100")
    self._threshold_score_minimo = value
```

### 4. **Herança e Polimorfismo**

#### **Herança de Classes Base**
```python
class Agente2Classificador(BaseAgent):
    def __init__(self, llm: Any, tabela_ncm: Optional[pd.DataFrame] = None):
        super().__init__(
            llm=llm,
            role="Especialista em Classificação Fiscal NCM",
            goal="Classificar produtos com código NCM correto",
            backstory="...",
            verbose=True,
            allow_delegation=False
        )
```

#### **Polimorfismo via Interfaces**
```python
def processar_agentes(agentes: List[IAgent], dados: Any) -> List[Any]:
    resultados = []
    for agente in agentes:
        resultado = agente.executar(dados)  # Polimorfismo
        resultados.append(resultado)
    return resultados
```

### 5. **Tratamento de Erros Robusto**

#### **Validação de Entrada**
```python
def validar_entrada(self, itens: List[ItemNFe]) -> bool:
    if not isinstance(itens, list):
        self._log_error("Itens deve ser uma lista")
        return False
    
    if len(itens) == 0:
        self._log_warning("Lista de itens vazia")
        return False
    
    # Validações específicas...
    return True
```

#### **Execução com Validação**
```python
def _executar_com_validacao(self, *args, **kwargs) -> Any:
    if not self._validar_llm():
        raise ValueError("LLM não está disponível")
    
    if not self.validar_entrada(*args, **kwargs):
        raise ValueError("Dados de entrada inválidos")
    
    try:
        resultado = self.executar(*args, **kwargs)
        self.resultado = resultado
        return resultado
    except Exception as e:
        self._log_error(f"Erro na execução: {str(e)}")
        raise
```

## 🚀 Como Usar a Nova Estrutura

### 1. **Criando um Novo Agente**

```python
from src.core.base_agent import BaseAgent
from src.core.interfaces import IAgent

class MeuNovoAgente(BaseAgent):
    def __init__(self, llm: Any, configuracao: str):
        super().__init__(
            llm=llm,
            role="Meu Papel",
            goal="Meu Objetivo",
            backstory="Minha História",
            verbose=True,
            allow_delegation=False
        )
        self._configuracao = configuracao
    
    def executar(self, dados: Any) -> Any:
        # Implementar lógica específica
        pass
    
    def validar_entrada(self, dados: Any) -> bool:
        # Implementar validação específica
        pass
```

### 2. **Criando um Novo Detector**

```python
from src.core.base_detector import BaseDetector
from src.core.interfaces import IDetector
from src.models import TipoFraude

class MeuNovoDetector(BaseDetector):
    def __init__(self, threshold_personalizado: int = 50):
        super().__init__(
            tipo_fraude=TipoFraude.MINHA_FRAUDE,
            threshold_score_minimo=threshold_personalizado
        )
    
    def detectar(self, item: ItemNFe, nfe: NFe) -> Optional[DeteccaoFraude]:
        # Implementar lógica de detecção
        pass
```

### 3. **Usando Polimorfismo**

```python
# Lista de agentes (polimorfismo)
agentes: List[IAgent] = [
    Agente2Classificador(llm=llm),
    MeuNovoAgente(llm=llm, configuracao="teste")
]

# Processar todos os agentes de forma uniforme
for agente in agentes:
    resultado = agente.executar(dados)
    print(f"Resultado de {agente.role}: {resultado}")
```

## 📊 Benefícios da Refatoração

### 1. **Manutenibilidade**
- Código mais organizado e fácil de manter
- Mudanças isoladas em classes específicas
- Redução de duplicação de código

### 2. **Extensibilidade**
- Fácil adição de novos agentes/detectores
- Herança de funcionalidades comuns
- Interfaces bem definidas

### 3. **Testabilidade**
- Classes com responsabilidades únicas
- Dependências injetadas
- Métodos pequenos e focados

### 4. **Robustez**
- Validação automática de entrada
- Tratamento de erros consistente
- Logging padronizado

### 5. **Performance**
- Cache inteligente
- Validação otimizada
- Reutilização de objetos

## 🔄 Migração da Estrutura Antiga

### 1. **Agentes Existentes**
- Refatorar para herdar de `BaseAgent`
- Implementar interface `IAgent`
- Adicionar validação de entrada
- Implementar logging adequado

### 2. **Detectores Existentes**
- Refatorar para herdar de `BaseDetector`
- Implementar interface `IDetector`
- Padronizar configuração de thresholds
- Adicionar validação de confiança

### 3. **Parsers Existentes**
- Refatorar para herdar de `BaseParser`
- Implementar interface `IParser`
- Padronizar validação de estrutura
- Adicionar cache de metadados

## 📝 Exemplos Práticos

Veja o arquivo `src/examples/oop_usage_example.py` para exemplos completos de uso da nova estrutura.

## 🎯 Próximos Passos

1. **Migrar Agentes Existentes**
   - Refatorar `Agente1Extrator`
   - Refatorar `Agente3Validador`
   - Refatorar `Agente4Orquestrador`
   - Refatorar `Agente5Interface`

2. **Migrar Detectores Existentes**
   - Refatorar todos os detectores para usar `BaseDetector`
   - Implementar interface `IDetector`
   - Padronizar configuração

3. **Migrar Parsers Existentes**
   - Refatorar parsers para usar `BaseParser`
   - Implementar interface `IParser`
   - Adicionar validação robusta

4. **Testes Unitários**
   - Criar testes para classes base
   - Testar interfaces
   - Validar polimorfismo

5. **Documentação**
   - Atualizar documentação da API
   - Criar guias de migração
   - Exemplos de uso avançado

## ✅ Conclusão

A refatoração implementa uma estrutura OOP robusta e escalável, seguindo princípios SOLID e boas práticas de desenvolvimento. A nova estrutura facilita manutenção, extensão e teste da aplicação, proporcionando uma base sólida para futuras funcionalidades.
