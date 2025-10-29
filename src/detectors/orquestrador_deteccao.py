"""
FiscalAI MVP - Orquestrador de Detecção de Fraudes
Consolida resultados de todos os detectores e gera análise final
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import time
import os

from ..models import (
    NFe, ResultadoAnalise, DeteccaoFraude, ClassificacaoNCM,
    NivelRisco, determinar_nivel_risco
)
from ..utils.result_cache import get_cache
from .fraud_optimizer import get_fraud_optimizer
from .detector_subfaturamento import DetectorSubfaturamento
from .detector_ncm_incorreto import DetectorNCMIncorreto
from .detector_triangulacao import DetectorTriangulacao
from .detector_fracionamento import DetectorFracionamento
from .detector_fornecedor_risco import DetectorFornecedorRisco
from .detector_anomalia_temporal import DetectorAnomaliaTemporal
from .detector_valor_inconsistente import DetectorValorInconsistente


# Configuração de debug com proteção para produção
PRODUCTION_MODE = os.getenv('FISCALAI_PRODUCTION', 'false').lower() == 'true'
DEBUG_MODE = os.getenv('FISCALAI_DEBUG', 'false').lower() == 'true' and not PRODUCTION_MODE
DEBUG_LEVEL = int(os.getenv('FISCALAI_DEBUG_LEVEL', '1')) if DEBUG_MODE else 0

def debug_log(message: str, level: int = 1):
    """Função de debug temporária"""
    if DEBUG_MODE and level <= DEBUG_LEVEL:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        # Log removido para evitar poluição do terminal


class OrquestradorDeteccaoFraudes:
    """
    Orquestra todos os detectores de fraude e consolida resultados
    
    Responsabilidades:
    1. Executar todos os detectores disponíveis
    2. Consolidar fraudes detectadas
    3. Calcular score de risco geral
    4. Gerar ações recomendadas
    5. Criar relatório final de análise
    """
    
    def __init__(self, detectores: Optional[Dict[str, Any]] = None):
        """
        Inicializa o orquestrador
        
        Args:
            detectores: Dict com instâncias dos detectores
                {
                    'subfaturamento': DetectorSubfaturamento(...),
                    'ncm_incorreto': DetectorNCMIncorreto(...),
                    'triangulacao': DetectorTriangulacao(...),
                }
                Se None, detectores serão criados com configuração padrão
        """
        if detectores is None:
            # Criar detectores com configuração padrão
            self.detectores = {
                'subfaturamento': DetectorSubfaturamento(),
                'ncm_incorreto': DetectorNCMIncorreto(),
                'triangulacao': DetectorTriangulacao(),
                'fracionamento': DetectorFracionamento(),
                'fornecedor_risco': DetectorFornecedorRisco(),
                'anomalia_temporal': DetectorAnomaliaTemporal(),
                'valor_inconsistente': DetectorValorInconsistente(),
            }
        else:
            self.detectores = detectores
    
    def analisar_nfe(self,
                     nfe: NFe,
                     classificacoes_ncm: Optional[Dict[int, ClassificacaoNCM]] = None) -> ResultadoAnalise:
        """
        Analisa uma NF-e completa para fraudes
        
        Args:
            nfe: NF-e a ser analisada
            classificacoes_ncm: Dict {numero_item: ClassificacaoNCM}
                                Resultado da classificação NCM dos itens
        
        Returns:
            ResultadoAnalise com todas as fraudes detectadas e análise consolidada
        """
        inicio = time.time()
        
        # Verificar cache primeiro
        cache = get_cache()
        cache_key = {
            'chave_acesso': nfe.chave_acesso,
            'valor_total': nfe.valor_total,
            'cnpj_emitente': nfe.cnpj_emitente,
            'classificacoes': {k: v.ncm_predito for k, v in (classificacoes_ncm or {}).items()}
        }
        
        cached_result = cache.get(cache_key)
        if cached_result:
            debug_log(f"Resultado encontrado no cache para NF-e: {nfe.chave_acesso}", 1)
            return cached_result
        
        debug_log(f"Iniciando análise da NF-e: {nfe.chave_acesso}", 1)
        debug_log(f"Detectores disponíveis: {list(self.detectores.keys())}", 2)
        debug_log(f"Classificações NCM disponíveis: {len(classificacoes_ncm) if classificacoes_ncm else 0}", 2)
        
        fraudes_detectadas: List[DeteccaoFraude] = []
        itens_suspeitos = set()
        
        # 1. Executar detectores tradicionais
        debug_log("Executando detectores tradicionais...", 1)
        fraudes_tradicionais = self._executar_detectores_tradicionais(nfe, classificacoes_ncm)
        fraudes_detectadas.extend(fraudes_tradicionais)
        debug_log(f"Fraudes detectadas por detectores tradicionais: {len(fraudes_tradicionais)}", 2)
        
        # 2. Executar otimizador de fraudes
        debug_log("Executando otimizador de fraudes...", 1)
        optimizer = get_fraud_optimizer()
        fraudes_otimizadas = optimizer.optimize_detection(nfe, classificacoes_ncm or {})
        fraudes_detectadas.extend(fraudes_otimizadas)
        debug_log(f"Fraudes detectadas pelo otimizador: {len(fraudes_otimizadas)}", 2)
        
        # Coletar itens suspeitos
        for fraude in fraudes_detectadas:
            if fraude.item_numero:
                itens_suspeitos.add(fraude.item_numero)
        
        # 3. Calcular score de risco geral
        score_geral = self._calcular_score_geral(fraudes_detectadas)
        nivel_risco = determinar_nivel_risco(score_geral)
        
        # 4. Gerar ações recomendadas
        acoes = self._gerar_acoes_recomendadas(fraudes_detectadas, nivel_risco, nfe)
        
        # 5. Calcular tempo de processamento
        tempo_processamento = time.time() - inicio
        
        # Criar resultado
        resultado = ResultadoAnalise(
            chave_acesso=nfe.chave_acesso,
            score_risco_geral=score_geral,
            nivel_risco=nivel_risco,
            fraudes_detectadas=fraudes_detectadas,
            itens_suspeitos=list(itens_suspeitos),
            acoes_recomendadas=acoes,
            timestamp_analise=datetime.now(),
            data_analise=datetime.now(),  # Adicionar data_analise para compatibilidade
            tempo_processamento_segundos=round(tempo_processamento, 2),
        )
        
        # Armazenar no cache
        cache.set(cache_key, resultado)
        debug_log(f"Resultado armazenado no cache para NF-e: {nfe.chave_acesso}", 2)
        
        return resultado
    
    def _executar_detectores_tradicionais(self, nfe: NFe, classificacoes_ncm: Optional[Dict[int, ClassificacaoNCM]]) -> List[DeteccaoFraude]:
        """
        Executa detectores tradicionais (NF-e e itens)
        
        Args:
            nfe: NF-e para análise
            classificacoes_ncm: Classificações NCM dos itens
            
        Returns:
            Lista de fraudes detectadas pelos detectores tradicionais
        """
        fraudes_detectadas = []
        
        # Executar detectores em nível de NF-e
        fraudes_nfe = self._executar_detectores_nfe(nfe)
        fraudes_detectadas.extend(fraudes_nfe)
        
        # Executar detectores em nível de item
        fraudes_itens = self._executar_detectores_itens(nfe, classificacoes_ncm)
        fraudes_detectadas.extend(fraudes_itens)
        
        return fraudes_detectadas
    
    def _executar_detectores_nfe(self, nfe: NFe) -> List[DeteccaoFraude]:
        """
        Executa detectores que analisam a NF-e como um todo
        
        Args:
            nfe: NF-e a ser analisada
        
        Returns:
            Lista de fraudes detectadas
        """
        fraudes = []
        
        # Detector de Triangulação
        if 'triangulacao' in self.detectores:
            try:
                debug_log("Executando detector de triangulação...", 3)
                fraude_tri = self.detectores['triangulacao'].detectar(nfe)
                if fraude_tri:
                    # Verificar se é uma lista ou item único
                    if isinstance(fraude_tri, list):
                        fraudes.extend(fraude_tri)
                        debug_log(f"Detector triangulação retornou {len(fraude_tri)} fraudes", 3)
                    else:
                        fraudes.append(fraude_tri)
                        debug_log("Detector triangulação retornou 1 fraude", 3)
                else:
                    debug_log("Detector triangulação não detectou fraudes", 3)
            except Exception as e:
                debug_log(f"ERRO no detector de triangulação: {e}", 1)
                print(f"Erro no detector de triangulação: {e}")
        
        # Detector de Fracionamento
        if 'fracionamento' in self.detectores:
            try:
                fraude_frac = self.detectores['fracionamento'].detectar(nfe)
                if fraude_frac:
                    if isinstance(fraude_frac, list):
                        fraudes.extend(fraude_frac)
                    else:
                        fraudes.append(fraude_frac)
            except Exception as e:
                print(f"Erro no detector de fracionamento: {e}")
        
        # Detector de Fornecedor Risco
        if 'fornecedor_risco' in self.detectores:
            try:
                fraude_forn = self.detectores['fornecedor_risco'].detectar(nfe)
                if fraude_forn:
                    if isinstance(fraude_forn, list):
                        fraudes.extend(fraude_forn)
                    else:
                        fraudes.append(fraude_forn)
            except Exception as e:
                print(f"Erro no detector de fornecedor risco: {e}")
        
        # Detector de Anomalia Temporal
        if 'anomalia_temporal' in self.detectores:
            try:
                fraude_temp = self.detectores['anomalia_temporal'].detectar(nfe)
                if fraude_temp:
                    if isinstance(fraude_temp, list):
                        fraudes.extend(fraude_temp)
                    else:
                        fraudes.append(fraude_temp)
            except Exception as e:
                print(f"Erro no detector de anomalia temporal: {e}")
        
        # Detector de Valor Inconsistente
        if 'valor_inconsistente' in self.detectores:
            try:
                fraude_valor = self.detectores['valor_inconsistente'].detectar(nfe)
                if fraude_valor:
                    if isinstance(fraude_valor, list):
                        fraudes.extend(fraude_valor)
                    else:
                        fraudes.append(fraude_valor)
            except Exception as e:
                print(f"Erro no detector de valor inconsistente: {e}")
        
        return fraudes
    
    def _executar_detectores_itens(self,
                                   nfe: NFe,
                                   classificacoes_ncm: Optional[Dict[int, ClassificacaoNCM]]) -> List[DeteccaoFraude]:
        """
        Executa detectores que analisam itens individuais
        
        Args:
            nfe: NF-e completa
            classificacoes_ncm: Classificações NCM dos itens
        
        Returns:
            Lista de fraudes detectadas
        """
        fraudes = []
        
        for item in nfe.itens:
            # Detector de Subfaturamento
            if 'subfaturamento' in self.detectores:
                try:
                    fraude_sub = self.detectores['subfaturamento'].detectar(item, nfe)
                    if fraude_sub:
                        fraudes.append(fraude_sub)
                except Exception as e:
                    print(f"Erro no detector de subfaturamento (item {item.numero_item}): {e}")
            
            # Detector de NCM Incorreto
            if 'ncm_incorreto' in self.detectores and classificacoes_ncm:
                if item.numero_item in classificacoes_ncm:
                    try:
                        class_info = classificacoes_ncm[item.numero_item]
                        fraude_ncm = self.detectores['ncm_incorreto'].detectar(
                            item,
                            class_info.ncm_predito,
                            class_info.confianca,
                            nfe
                        )
                        if fraude_ncm:
                            fraudes.append(fraude_ncm)
                    except Exception as e:
                        print(f"Erro no detector de NCM incorreto (item {item.numero_item}): {e}")
        
        return fraudes
    
    def _calcular_score_geral(self, fraudes: List[DeteccaoFraude]) -> float:
        """
        Calcula score de risco geral da NF-e
        
        Usa média ponderada dos scores individuais, com peso baseado na confiança.
        Aplica bônus por múltiplas fraudes (indicador mais forte).
        
        Args:
            fraudes: Lista de fraudes detectadas
        
        Returns:
            Score geral (0-100)
        """
        if not fraudes:
            return 0.0
        
        # Calcular média ponderada pela confiança
        score_ponderado = sum(f.score * f.confianca for f in fraudes)
        peso_total = sum(f.confianca for f in fraudes)
        
        if peso_total == 0:
            return 0.0
        
        score_medio = score_ponderado / peso_total
        
        # Bônus por múltiplas fraudes (indicador mais forte)
        if len(fraudes) >= 4:
            score_medio = min(score_medio * 1.3, 100)
        elif len(fraudes) == 3:
            score_medio = min(score_medio * 1.2, 100)
        elif len(fraudes) == 2:
            score_medio = min(score_medio * 1.1, 100)
        
        # Bônus por fraudes de tipos diferentes (mais grave)
        tipos_unicos = len(set(f.tipo_fraude for f in fraudes))
        if tipos_unicos >= 3:
            score_medio = min(score_medio * 1.15, 100)
        
        return round(score_medio, 2)
    
    def _gerar_acoes_recomendadas(self,
                                  fraudes: List[DeteccaoFraude],
                                  nivel: NivelRisco,
                                  nfe: NFe) -> List[str]:
        """
        Gera lista de ações recomendadas baseado nas fraudes detectadas
        
        Args:
            fraudes: Lista de fraudes detectadas
            nivel: Nível de risco determinado
            nfe: NF-e analisada
        
        Returns:
            Lista de ações recomendadas
        """
        acoes = []
        
        # Ações por nível de risco
        if nivel == NivelRisco.CRITICO:
            acoes.append("🚨 AÇÃO URGENTE: Bloquear processamento imediatamente")
            acoes.append("🚨 Acionar auditoria fiscal para investigação detalhada")
            acoes.append("🚨 Notificar gestor fiscal e departamento de compliance")
            acoes.append("🚨 Considerar comunicação à Receita Federal")
        
        elif nivel == NivelRisco.ALTO:
            acoes.append("⚠️ ATENÇÃO: Revisar manualmente antes de aprovar")
            acoes.append("⚠️ Solicitar documentação adicional do fornecedor")
            acoes.append("⚠️ Verificar histórico de transações com este fornecedor")
            acoes.append("⚠️ Escalar para supervisor fiscal")
        
        elif nivel == NivelRisco.MEDIO:
            acoes.append("⚡ ALERTA: Verificar pontos destacados abaixo")
            acoes.append("⚡ Validar informações com fornecedor")
            acoes.append("⚡ Registrar observação para monitoramento futuro")
        
        else:  # BAIXO
            acoes.append("✅ Processamento pode prosseguir normalmente")
            acoes.append("✅ Manter monitoramento de rotina")
        
        # Ações específicas por tipo de fraude
        from ..models import TipoFraude
        tipos_fraude = set(f.tipo_fraude for f in fraudes)
        
        if TipoFraude.SUBFATURAMENTO in tipos_fraude:
            acoes.append("💰 Solicitar cotações de mercado para validar preços declarados")
            acoes.append("💰 Verificar se há justificativa comercial para preços baixos")
        
        if TipoFraude.NCM_INCORRETO in tipos_fraude:
            acoes.append("📋 Consultar especialista em classificação fiscal NCM")
            acoes.append("📋 Verificar histórico de classificações do fornecedor")
            acoes.append("📋 Considerar reclassificação e ajuste tributário")
        
        if TipoFraude.TRIANGULACAO in tipos_fraude:
            acoes.append("🔄 Investigar relacionamento entre as partes envolvidas")
            acoes.append("🔄 Analisar fluxo completo de mercadorias")
            acoes.append("🔄 Verificar se há propósito comercial legítimo")
        
        # Ação para valores altos
        if nfe.valor_total > 100000:  # Mais de R$ 100.000
            acoes.append(f"💎 Alto valor envolvido (R$ {nfe.valor_total:,.2f}) - Atenção redobrada")
        
        return acoes
    
    def adicionar_detector(self, nome: str, detector: Any):
        """
        Adiciona um novo detector ao orquestrador
        
        Args:
            nome: Nome identificador do detector
            detector: Instância do detector
        """
        self.detectores[nome] = detector
    
    def remover_detector(self, nome: str):
        """
        Remove um detector do orquestrador
        
        Args:
            nome: Nome do detector a remover
        """
        if nome in self.detectores:
            del self.detectores[nome]
    
    def listar_detectores(self) -> List[str]:
        """
        Lista detectores ativos
        
        Returns:
            Lista com nomes dos detectores
        """
        return list(self.detectores.keys())
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas dos detectores
        
        Returns:
            Dict com estatísticas
        """
        stats = {
            'num_detectores': len(self.detectores),
            'detectores_ativos': self.listar_detectores(),
        }
        
        # Estatísticas específicas de cada detector
        if 'triangulacao' in self.detectores:
            try:
                stats['grafo_transacoes'] = self.detectores['triangulacao'].get_estatisticas_grafo()
            except:
                pass
        
        return stats

