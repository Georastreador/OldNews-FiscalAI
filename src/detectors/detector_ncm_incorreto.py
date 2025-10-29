"""
FiscalAI MVP - Detector de NCM Incorreto Intencional
Detecta uso intencional de NCM incorreto para redução de tributos
Usa abordagem híbrida: análise de impacto tributário + LLM para contexto
"""

import pandas as pd
import json
import os
from typing import Optional, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

from ..models import ItemNFe, NFe, DeteccaoFraude, TipoFraude

# Configuração de debug com proteção para produção
PRODUCTION_MODE = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true' and not PRODUCTION_MODE
DEBUG_LEVEL = int(os.getenv('FISCALAI_DEBUG_LEVEL', '1')) if DEBUG_MODE else 0

def debug_log(message: str, level: int = 1):
    """Função de debug temporária"""
    if DEBUG_MODE and level <= DEBUG_LEVEL:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # Log removido para evitar poluição do terminal


class DetectorNCMIncorreto:
    """
    Detecta uso intencional de NCM incorreto para redução de tributos
    
    Métodos de detecção:
    1. Comparação NCM predito vs declarado
    2. Análise de impacto tributário
    3. Verificação de compatibilidade descrição-NCM
    4. Análise contextual com LLM (casos complexos)
    """
    
    def __init__(self,
                 tabela_ncm: Optional[pd.DataFrame] = None,
                 tabela_tributacao: Optional[pd.DataFrame] = None,
                 llm: Optional[Any] = None):
        """
        Inicializa o detector
        
        Args:
            tabela_ncm: DataFrame com NCM e descrições oficiais
            tabela_tributacao: DataFrame com alíquotas por NCM
            llm: Instância do LLM para análise contextual
        """
        self.tabela_ncm = tabela_ncm if tabela_ncm is not None else self._criar_tabela_ncm_mock()
        self.tabela_tributacao = tabela_tributacao if tabela_tributacao is not None else self._criar_tabela_tributacao_mock()
        self.llm = llm
        
        # Thresholds
        self.threshold_confianca_minima = 0.7  # Confiança mínima da classificação
        self.threshold_economia_tributaria = 20  # 20% de economia
        self.threshold_compatibilidade = 0.3  # 30% de compatibilidade
        self.threshold_score_minimo = 40
        
        # Preparar vectorizer para similaridade de texto
        self.vectorizer = TfidfVectorizer(max_features=100)
        self._treinar_vectorizer()
    
    def detectar(self,
                 item: ItemNFe,
                 ncm_predito: str,
                 score_confianca_classificacao: float,
                 nfe: Optional[NFe] = None) -> Optional[DeteccaoFraude]:
        """
        Detecta NCM incorreto intencional
        
        Args:
            item: Item da NF-e
            ncm_predito: NCM predito pelo classificador
            score_confianca_classificacao: Confiança da predição (0-1)
            nfe: NF-e completa (opcional, para contexto adicional)
        
        Returns:
            DeteccaoFraude se houver suspeita, None caso contrário
        """
        # Validações de entrada
        if not item or not hasattr(item, 'ncm_declarado'):
            return None
        
        if not ncm_predito or not isinstance(ncm_predito, str):
            return None
        
        if not isinstance(score_confianca_classificacao, (int, float)) or score_confianca_classificacao < 0 or score_confianca_classificacao > 1:
            return None
        
        ncm_declarado = item.ncm_declarado
        
        # Validar NCMs
        if not ncm_declarado or not isinstance(ncm_declarado, str):
            return None
        
        debug_log(f"Analisando item {item.numero_item}: {item.descricao[:50]}...", 2)
        debug_log(f"NCM declarado: {ncm_declarado}, NCM predito: {ncm_predito}", 3)
        debug_log(f"Confiança da classificação: {score_confianca_classificacao:.2f}", 3)
        
        # 1. Verificar se há divergência
        if ncm_declarado == ncm_predito:
            debug_log("NCMs são iguais - sem divergência", 3)
            return None  # NCM correto
        
        # 2. Verificar confiança da predição
        if score_confianca_classificacao < self.threshold_confianca_minima:
            debug_log(f"Confiança baixa ({score_confianca_classificacao:.2f} < {self.threshold_confianca_minima}) - ignorando", 3)
            return None  # Baixa confiança, pode ser ambiguidade legítima
        
        # 3. Comparar impacto tributário
        debug_log("Calculando impacto tributário...", 3)
        impacto = self._calcular_impacto_tributario(
            ncm_declarado, ncm_predito, item.valor_total
        )
        debug_log(f"Impacto: economia R$ {impacto['economia_reais']:.2f} ({impacto['economia_percentual']:.1f}%)", 3)
        
        evidencias = []
        score = 0
        
        # Regra 1: NCM declarado tem tributação significativamente menor
        if impacto['economia_percentual'] > self.threshold_economia_tributaria:
            pontos = min(50, int(impacto['economia_percentual']))
            score += pontos
            evidencias.append(
                f"NCM declarado ({ncm_declarado}) tem tributação "
                f"{impacto['economia_percentual']:.1f}% menor que o NCM correto ({ncm_predito})"
            )
            evidencias.append(
                f"Economia tributária estimada: R$ {impacto['economia_reais']:.2f}"
            )
        
        # Regra 2: NCMs em categorias completamente diferentes
        if not self._ncms_mesma_categoria(ncm_declarado, ncm_predito):
            score += 30
            cat_declarado = self._get_categoria(ncm_declarado)
            cat_predito = self._get_categoria(ncm_predito)
            evidencias.append(
                f"NCM declarado ({cat_declarado}) e NCM correto ({cat_predito}) "
                f"pertencem a categorias distintas"
            )
        
        # Regra 3: Descrição incompatível com NCM declarado
        compatibilidade = self._verificar_compatibilidade_descricao_ncm(
            item.descricao, ncm_declarado
        )
        if compatibilidade < self.threshold_compatibilidade:
            score += 20
            evidencias.append(
                f"Descrição do produto incompatível com NCM declarado "
                f"(compatibilidade: {compatibilidade:.0%})"
            )
        
        # Regra 4: Alto valor de economia em termos absolutos
        if impacto['economia_reais'] > 5000:  # Mais de R$ 5.000
            score += 15
            evidencias.append(
                f"Alto valor absoluto de economia tributária: "
                f"R$ {impacto['economia_reais']:,.2f}"
            )
        
        # 4. Usar LLM para análise contextual (se disponível e score alto)
        justificativa = ""
        if self.llm and score >= 50:
            analise_llm = self._analisar_com_llm(
                item, ncm_declarado, ncm_predito, impacto
            )
            
            if analise_llm['suspeita_intencional']:
                score += 20
                evidencias.append(
                    "Análise contextual com IA indica possível intenção de fraude"
                )
                justificativa = analise_llm['justificativa']
            else:
                # LLM identificou possível razão legítima
                score -= 20
                justificativa = analise_llm['justificativa']
        else:
            justificativa = self._gerar_justificativa_basica(
                item, ncm_declarado, ncm_predito, impacto
            )
        
        # 5. Determinar se é fraude
        score = max(0, min(score, 100))
        
        if score >= self.threshold_score_minimo:
            return DeteccaoFraude(
                tipo_fraude=TipoFraude.NCM_INCORRETO,
                score=score,
                confianca=score_confianca_classificacao,
                evidencias=evidencias,
                justificativa=justificativa,
                metodo_deteccao="hybrid" if self.llm else "rule",
                item_numero=item.numero_item,
                dados_adicionais={
                    'ncm_declarado': ncm_declarado,
                    'ncm_correto': ncm_predito,
                    'economia_tributaria_reais': impacto['economia_reais'],
                    'economia_tributaria_percentual': impacto['economia_percentual'],
                    'aliquota_declarado': impacto['aliquota_declarado'],
                    'aliquota_correto': impacto['aliquota_correto'],
                    'compatibilidade_descricao': compatibilidade,
                }
            )
        
        return None
    
    def _calcular_impacto_tributario(self,
                                     ncm_declarado: str,
                                     ncm_correto: str,
                                     valor: float) -> Dict[str, float]:
        """Calcula diferença de tributação entre NCMs"""
        # Buscar alíquotas
        aliq_declarado = self._get_aliquota_total(ncm_declarado)
        aliq_correto = self._get_aliquota_total(ncm_correto)
        
        # Calcular impostos
        imposto_declarado = valor * aliq_declarado
        imposto_correto = valor * aliq_correto
        
        economia_reais = imposto_correto - imposto_declarado
        
        # Calcular economia percentual de forma mais robusta
        if imposto_correto > 0:
            economia_percentual = (economia_reais / imposto_correto) * 100
        elif aliq_correto > 0:
            # Se não há imposto correto mas há alíquota, calcular baseado na alíquota
            economia_percentual = ((aliq_correto - aliq_declarado) / aliq_correto) * 100
        else:
            economia_percentual = 0.0
        
        # Garantir que economia_percentual não seja negativa (caso NCM declarado tenha maior tributação)
        economia_percentual = max(0.0, economia_percentual)
        
        return {
            'aliquota_declarado': aliq_declarado,
            'aliquota_correto': aliq_correto,
            'imposto_declarado': imposto_declarado,
            'imposto_correto': imposto_correto,
            'economia_reais': economia_reais,
            'economia_percentual': economia_percentual,
        }
    
    def _get_aliquota_total(self, ncm: str) -> float:
        """Obtém alíquota total (IPI + II + PIS + COFINS) para um NCM"""
        if ncm not in self.tabela_tributacao.index:
            # Retornar alíquota média se NCM não encontrado
            return 0.15  # 15% como padrão
        
        row = self.tabela_tributacao.loc[ncm]
        return float(
            row.get('ipi', 0) + 
            row.get('ii', 0) + 
            row.get('pis', 0) + 
            row.get('cofins', 0)
        )
    
    def _ncms_mesma_categoria(self, ncm1: str, ncm2: str) -> bool:
        """Verifica se dois NCMs pertencem à mesma categoria (primeiros 4 dígitos)"""
        return ncm1[:4] == ncm2[:4]
    
    def _get_categoria(self, ncm: str) -> str:
        """Retorna descrição da categoria do NCM"""
        capitulo = ncm[:2]
        
        # Mapeamento de capítulos NCM (simplificado)
        capitulos = {
            '84': 'Máquinas e Equipamentos',
            '85': 'Equipamentos Elétricos e Eletrônicos',
            '39': 'Plásticos e suas Obras',
            '73': 'Obras de Ferro ou Aço',
            '94': 'Móveis e Mobiliário',
        }
        
        return capitulos.get(capitulo, f"Capítulo {capitulo}")
    
    def _verificar_compatibilidade_descricao_ncm(self,
                                                  descricao: str,
                                                  ncm: str) -> float:
        """
        Verifica compatibilidade entre descrição do produto e NCM
        
        Args:
            descricao: Descrição do produto
            ncm: Código NCM
        
        Returns:
            Score de compatibilidade (0-1)
        """
        if ncm not in self.tabela_ncm.index:
            return 0.5  # Sem dados para comparar
        
        descricao_oficial = self.tabela_ncm.loc[ncm, 'descricao']
        
        try:
            # Calcular similaridade usando TF-IDF
            vectors = self.vectorizer.transform([
                descricao.lower(),
                descricao_oficial.lower()
            ])
            similaridade = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return float(similaridade)
        except:
            # Fallback: comparação simples de palavras-chave
            palavras_descricao = set(descricao.lower().split())
            palavras_oficial = set(descricao_oficial.lower().split())
            
            if not palavras_oficial:
                return 0.5
            
            intersecao = palavras_descricao.intersection(palavras_oficial)
            return len(intersecao) / len(palavras_oficial)
    
    def _analisar_com_llm(self,
                         item: ItemNFe,
                         ncm_declarado: str,
                         ncm_predito: str,
                         impacto: Dict) -> Dict[str, Any]:
        """Usa LLM para análise contextual profunda"""
        
        desc_declarado = self.tabela_ncm.loc[ncm_declarado, 'descricao'] if ncm_declarado in self.tabela_ncm.index else "Não disponível"
        desc_predito = self.tabela_ncm.loc[ncm_predito, 'descricao'] if ncm_predito in self.tabela_ncm.index else "Não disponível"
        
        prompt = f"""Você é um auditor fiscal especialista em classificação NCM. Analise a seguinte situação:

PRODUTO DECLARADO:
- Descrição: {item.descricao}
- Quantidade: {item.quantidade} {item.unidade}
- Valor Unitário: R$ {item.valor_unitario:.2f}
- Valor Total: R$ {item.valor_total:.2f}

CLASSIFICAÇÃO NCM:
- NCM DECLARADO: {ncm_declarado}
  Descrição oficial: {desc_declarado}
  
- NCM CORRETO (predito por IA): {ncm_predito}
  Descrição oficial: {desc_predito}

IMPACTO TRIBUTÁRIO:
- Alíquota com NCM declarado: {impacto['aliquota_declarado']:.2%}
- Alíquota com NCM correto: {impacto['aliquota_correto']:.2%}
- Economia tributária: R$ {impacto['economia_reais']:.2f} ({impacto['economia_percentual']:.1f}%)

ANÁLISE SOLICITADA:
Com base nas informações acima, determine se o uso do NCM declarado foi:
1. Um erro honesto ou ambiguidade de classificação (legítimo)
2. Uma tentativa intencional de reduzir tributos (fraude)

Considere:
- A descrição do produto é compatível com ambos os NCMs?
- A diferença de tributação é significativa?
- Há justificativa técnica para a escolha do NCM declarado?

Responda APENAS em formato JSON válido:
{{
    "suspeita_intencional": true ou false,
    "confianca": 0.0 a 1.0,
    "justificativa": "explicação detalhada em português",
    "razao_principal": "motivo principal da conclusão"
}}"""
        
        try:
            response = self.llm.invoke(prompt)
            
            # Extrair conteúdo da resposta
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Tentar parsear JSON
            # Remover markdown se presente
            content = content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            elif content.startswith('```'):
                content = content.split('```')[1].split('```')[0]
            
            resultado = json.loads(content.strip())
            
            # Validar estrutura
            if not all(k in resultado for k in ['suspeita_intencional', 'confianca', 'justificativa']):
                raise ValueError("JSON incompleto")
            
            return resultado
            
        except Exception as e:
            # Fallback: análise baseada apenas em economia tributária
            return {
                "suspeita_intencional": impacto['economia_percentual'] > 30,
                "confianca": 0.6,
                "justificativa": (
                    f"Análise automática: Economia tributária de "
                    f"{impacto['economia_percentual']:.1f}% "
                    f"({'suspeita' if impacto['economia_percentual'] > 30 else 'aceitável'}). "
                    f"Erro ao processar análise contextual: {str(e)}"
                ),
                "razao_principal": "Análise automática por falha no LLM"
            }
    
    def _gerar_justificativa_basica(self,
                                    item: ItemNFe,
                                    ncm_declarado: str,
                                    ncm_predito: str,
                                    impacto: Dict) -> str:
        """Gera justificativa sem uso de LLM"""
        return (
            f"O produto '{item.descricao}' foi classificado com NCM {ncm_declarado}, "
            f"porém a análise indica que o NCM correto seria {ncm_predito}. "
            f"Esta divergência resulta em uma economia tributária de "
            f"R$ {impacto['economia_reais']:.2f} ({impacto['economia_percentual']:.1f}%), "
            f"o que pode indicar uso intencional de NCM incorreto para redução de base tributária. "
            f"A alíquota efetiva do NCM declarado é {impacto['aliquota_declarado']:.2%}, "
            f"enquanto o NCM correto teria alíquota de {impacto['aliquota_correto']:.2%}."
        )
    
    def _treinar_vectorizer(self):
        """Treina vectorizer com descrições da tabela NCM"""
        if not self.tabela_ncm.empty:
            descricoes = self.tabela_ncm['descricao'].tolist()
            try:
                self.vectorizer.fit(descricoes)
            except:
                pass  # Usar vectorizer não treinado
    
    def _criar_tabela_ncm_mock(self) -> pd.DataFrame:
        """Cria tabela NCM mock para testes"""
        data = {
            'ncm': [
                '85171231', '84713012', '85176255', '85044090', '39202090',
                '84713011', '85171210', '85176262', '85044021',
            ],
            'descricao': [
                'Telefones celulares (smartphones)',
                'Computadores portáteis (notebooks)',
                'Aparelhos para comutação de redes (roteadores)',
                'Carregadores de baterias',
                'Placas, folhas, películas de polímeros de propileno',
                'Computadores de mesa (desktops)',
                'Telefones celulares básicos',
                'Modems e roteadores WiFi',
                'Fontes de alimentação eletrônicas',
            ]
        }
        
        df = pd.DataFrame(data)
        df.set_index('ncm', inplace=True)
        return df
    
    def _criar_tabela_tributacao_mock(self) -> pd.DataFrame:
        """Cria tabela de tributação mock para testes"""
        data = {
            'ncm': [
                '85171231', '84713012', '85176255', '85044090', '39202090',
                '84713011', '85171210', '85176262', '85044021',
            ],
            'ipi': [0.15, 0.15, 0.15, 0.10, 0.05, 0.15, 0.12, 0.15, 0.10],
            'ii': [0.16, 0.16, 0.16, 0.12, 0.14, 0.16, 0.14, 0.16, 0.12],
            'pis': [0.0165, 0.0165, 0.0165, 0.0165, 0.0165, 0.0165, 0.0165, 0.0165, 0.0165],
            'cofins': [0.076, 0.076, 0.076, 0.076, 0.076, 0.076, 0.076, 0.076, 0.076],
        }
        
        df = pd.DataFrame(data)
        df.set_index('ncm', inplace=True)
        return df

