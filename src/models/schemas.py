"""
OldNews FiscalAI - Data Models and Schemas
Pydantic models for type validation and data structures
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ===== Enums =====

class TipoFraude(str, Enum):
    """Tipos de fraude detectáveis pelo sistema"""
    SUBFATURAMENTO = "subfaturamento"
    NCM_INCORRETO = "ncm_incorreto"
    TRIANGULACAO = "triangulacao"
    FRACIONAMENTO = "fracionamento"
    FORNECEDOR_RISCO = "fornecedor_risco"
    ANOMALIA_TEMPORAL = "anomalia_temporal"
    VALOR_INCONSISTENTE = "valor_inconsistente"


class NivelRisco(str, Enum):
    """Níveis de risco fiscal"""
    BAIXO = "baixo"          # 0-30
    MEDIO = "medio"          # 31-60
    ALTO = "alto"            # 61-85
    CRITICO = "critico"      # 86-100


class StatusProcessamento(str, Enum):
    """Status de processamento da NF-e"""
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"
    BLOQUEADO = "bloqueado"


class LLMProvider(str, Enum):
    """Provedores de LLM suportados"""
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    TOGETHER = "together"


# ===== NF-e Models =====

class ItemNFe(BaseModel):
    """Item individual de uma Nota Fiscal Eletrônica"""
    numero_item: int = Field(..., ge=1, description="Número sequencial do item")
    descricao: str = Field(..., min_length=1, description="Descrição do produto")
    ncm_declarado: str = Field(..., min_length=8, max_length=8, description="NCM declarado (8 dígitos)")
    ncm_predito: Optional[str] = Field(None, min_length=8, max_length=8, description="NCM predito pelo classificador")
    cfop: str = Field(..., min_length=4, max_length=4, description="Código Fiscal de Operações (4 dígitos)")
    quantidade: float = Field(..., gt=0, description="Quantidade do produto")
    valor_unitario: float = Field(..., ge=0, description="Valor unitário em reais")
    valor_total: float = Field(..., ge=0, description="Valor total do item em reais")
    unidade: str = Field(..., description="Unidade de medida (UN, KG, etc)")
    
    # Campos adicionais opcionais
    codigo_produto: Optional[str] = None
    ean: Optional[str] = None
    ncm_confianca: Optional[float] = Field(None, ge=0, le=1, description="Confiança da classificação NCM")
    
    @validator('ncm_declarado', 'ncm_predito')
    def validar_ncm(cls, v):
        """Valida formato do NCM (8 dígitos numéricos)"""
        if v and not v.isdigit():
            raise ValueError('NCM deve conter apenas dígitos')
        return v
    
    @validator('cfop')
    def validar_cfop(cls, v):
        """Valida formato do CFOP (4 dígitos numéricos)"""
        if not v.isdigit():
            raise ValueError('CFOP deve conter apenas dígitos')
        return v
    
    @validator('valor_total')
    def validar_valor_total(cls, v, values):
        """Valida se valor_total = quantidade * valor_unitario (com tolerância)"""
        if 'quantidade' in values and 'valor_unitario' in values:
            esperado = values['quantidade'] * values['valor_unitario']
            if abs(v - esperado) > 0.01:  # Tolerância de 1 centavo
                raise ValueError(f'Valor total inconsistente: esperado {esperado:.2f}, recebido {v:.2f}')
        return v


class NFe(BaseModel):
    """Nota Fiscal Eletrônica completa"""
    chave_acesso: str = Field(..., min_length=44, max_length=44, description="Chave de acesso da NF-e (44 dígitos)")
    numero: str = Field(..., description="Número da NF-e")
    serie: str = Field(..., description="Série da NF-e")
    data_emissao: datetime = Field(..., description="Data e hora de emissão")
    
    # Partes envolvidas
    cnpj_emitente: str = Field(..., description="CNPJ do emitente")
    razao_social_emitente: Optional[str] = None
    cnpj_destinatario: str = Field(..., description="CNPJ do destinatário")
    razao_social_destinatario: Optional[str] = None
    
    # Valores
    valor_total: float = Field(..., ge=0, description="Valor total da NF-e")
    valor_produtos: float = Field(..., ge=0, description="Valor total dos produtos")
    valor_impostos: Optional[float] = Field(None, ge=0, description="Valor total de impostos")
    
    # Itens
    itens: List[ItemNFe] = Field(..., min_items=1, description="Lista de itens da NF-e")
    
    # Metadados
    status: StatusProcessamento = Field(default=StatusProcessamento.PENDENTE)
    data_processamento: Optional[datetime] = None
    
    # Informações sobre tipo de documento (para compatibilidade com NFS-e)
    tipo_documento: Optional[str] = Field(None, description="Tipo de documento: 'nfe', 'nfse', 'cte', 'mdfe'")
    descricao_documento: Optional[str] = Field(None, description="Descrição do tipo de documento")
    
    @validator('chave_acesso')
    def validar_chave_acesso(cls, v):
        """Valida formato da chave de acesso (44 dígitos numéricos)"""
        if not v.isdigit():
            raise ValueError('Chave de acesso deve conter apenas dígitos')
        return v
    
    @validator('cnpj_emitente', 'cnpj_destinatario')
    def validar_cnpj(cls, v):
        """Valida formato básico do CNPJ"""
        cnpj_limpo = v.replace('.', '').replace('/', '').replace('-', '')
        if not cnpj_limpo.isdigit() or len(cnpj_limpo) != 14:
            raise ValueError('CNPJ deve ter 14 dígitos')
        return v


# ===== Fraud Detection Models =====

class DeteccaoFraude(BaseModel):
    """Resultado de detecção de fraude para um item ou NF-e"""
    tipo_fraude: TipoFraude = Field(..., description="Tipo de fraude detectada")
    score: float = Field(..., ge=0, le=100, description="Score de risco (0-100)")
    confianca: float = Field(..., ge=0, le=1, description="Confiança na detecção (0-1)")
    evidencias: List[str] = Field(..., min_items=1, description="Lista de evidências encontradas")
    justificativa: str = Field(..., min_length=10, description="Justificativa detalhada da detecção")
    metodo_deteccao: str = Field(..., description="Método usado: rule, statistical, ai, hybrid")
    
    # Campos opcionais
    item_numero: Optional[int] = Field(None, description="Número do item afetado (se aplicável)")
    dados_adicionais: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais da análise")
    
    # Campos para compatibilidade com código existente
    descricao: Optional[str] = Field(None, description="Descrição da fraude (para compatibilidade)")
    item_id: Optional[int] = Field(None, description="ID do item (para compatibilidade)")


class ResultadoAnalise(BaseModel):
    """Resultado completo da análise de fraudes de uma NF-e"""
    chave_acesso: str = Field(..., min_length=44, max_length=44)
    score_risco_geral: float = Field(..., ge=0, le=100, description="Score de risco consolidado")
    nivel_risco: NivelRisco = Field(..., description="Nível de risco determinado")
    
    # Fraudes detectadas
    fraudes_detectadas: List[DeteccaoFraude] = Field(default_factory=list)
    itens_suspeitos: List[int] = Field(default_factory=list, description="Números dos itens suspeitos")
    
    # Ações recomendadas
    acoes_recomendadas: List[str] = Field(default_factory=list)
    
    # Metadados
    timestamp_analise: datetime = Field(default_factory=datetime.now)
    tempo_processamento_segundos: Optional[float] = None
    modelo_utilizado: Optional[str] = None
    
    # Campos para compatibilidade com código existente
    data_analise: Optional[datetime] = Field(None, description="Data da análise (para compatibilidade)")
    resultado_analise: Optional[Dict[str, Any]] = Field(None, description="Resultado da análise (para compatibilidade)")
    
    @property
    def tem_fraudes(self) -> bool:
        """Verifica se há fraudes detectadas"""
        return len(self.fraudes_detectadas) > 0
    
    @property
    def fraudes_por_tipo(self) -> Dict[str, int]:
        """Conta fraudes por tipo"""
        contagem = {}
        for fraude in self.fraudes_detectadas:
            tipo = fraude.tipo_fraude.value
            contagem[tipo] = contagem.get(tipo, 0) + 1
        return contagem


# ===== Classification Models =====

class ClassificacaoNCM(BaseModel):
    """Resultado de classificação NCM para um produto"""
    numero_item: int
    descricao_produto: str
    ncm_predito: str = Field(..., min_length=8, max_length=8)
    ncm_declarado: Optional[str] = Field(None, min_length=8, max_length=8)
    confianca: float = Field(..., ge=0, le=1)
    justificativa: Optional[str] = None
    alternativas: Optional[List[Dict[str, Any]]] = Field(None, description="NCMs alternativos com scores")
    
    @property
    def diverge(self) -> bool:
        """Verifica se há divergência entre predito e declarado"""
        return self.ncm_declarado is not None and self.ncm_predito != self.ncm_declarado


# ===== LLM Configuration Models =====

class LLMConfig(BaseModel):
    """Configuração do modelo de linguagem"""
    provider: LLMProvider = Field(default=LLMProvider.LOCAL)
    model: str = Field(..., description="Nome do modelo")
    temperature: float = Field(default=0.1, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    api_key: Optional[str] = Field(None, description="API key (se necessário)")
    base_url: Optional[str] = Field(None, description="Base URL customizada")
    
    class Config:
        use_enum_values = True


# ===== Report Models =====

class RelatorioFiscal(BaseModel):
    """Relatório fiscal consolidado"""
    nfe: NFe
    resultado_analise: ResultadoAnalise
    classificacoes_ncm: List[ClassificacaoNCM]
    
    # Resumo executivo
    resumo_executivo: Optional[str] = None
    recomendacoes_finais: List[str] = Field(default_factory=list)
    
    # Metadados do relatório
    data_geracao: datetime = Field(default_factory=datetime.now)
    versao_sistema: str = Field(default="1.0.0-MVP")
    
    @property
    def status_geral(self) -> str:
        """Retorna status geral da NF-e"""
        if self.resultado_analise.nivel_risco == NivelRisco.CRITICO:
            return "🚨 BLOQUEADO - Ação Urgente Necessária"
        elif self.resultado_analise.nivel_risco == NivelRisco.ALTO:
            return "⚠️ ATENÇÃO - Revisão Manual Obrigatória"
        elif self.resultado_analise.nivel_risco == NivelRisco.MEDIO:
            return "⚡ ALERTA - Verificação Recomendada"
        else:
            return "✅ APROVADO - Conformidade OK"


# ===== Database Models (for persistence) =====

class NFePersistencia(BaseModel):
    """Modelo para persistência de NF-e no banco de dados"""
    id: Optional[int] = None
    chave_acesso: str
    dados_nfe: Dict[str, Any]  # JSON da NFe
    resultado_analise: Optional[Dict[str, Any]] = None  # JSON do ResultadoAnalise
    data_criacao: datetime = Field(default_factory=datetime.now)
    data_atualizacao: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


# ===== Utility Functions =====

def determinar_nivel_risco(score: float) -> NivelRisco:
    """Determina nível de risco baseado no score"""
    if score >= 86:
        return NivelRisco.CRITICO
    elif score >= 61:
        return NivelRisco.ALTO
    elif score >= 31:
        return NivelRisco.MEDIO
    else:
        return NivelRisco.BAIXO


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ para exibição (XX.XXX.XXX/XXXX-XX)"""
    cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
    if len(cnpj_limpo) != 14:
        return cnpj
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"


def formatar_ncm(ncm: str) -> str:
    """Formata NCM para exibição (XXXX.XX.XX)"""
    if len(ncm) != 8:
        return ncm
    return f"{ncm[:4]}.{ncm[4:6]}.{ncm[6:]}"

