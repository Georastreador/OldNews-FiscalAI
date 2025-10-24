"""
Módulo para exportação de relatórios em PDF
Implementa geração de relatórios executivos em formato PDF
"""

from datetime import datetime
from typing import Dict, List, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import os

from ..models.schemas import NFe, ResultadoAnalise, ClassificacaoNCM, DeteccaoFraude


class PDFExporter:
    """
    Classe para exportação de relatórios fiscais em PDF
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos customizados para o PDF"""
        
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        ))
        
        # Cabeçalho de seção
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.darkgreen
        ))
        
        # Texto normal
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        ))
        
        # Texto de alerta
        self.styles.add(ParagraphStyle(
            name='Alert',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.red,
            spaceAfter=6
        ))
        
        # Texto de sucesso
        self.styles.add(ParagraphStyle(
            name='Success',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.green,
            spaceAfter=6
        ))
    
    def export_relatorio_executivo(self, 
                                 nfe: NFe, 
                                 classificacoes: Dict[int, ClassificacaoNCM],
                                 resultado: ResultadoAnalise,
                                 output_path: str) -> str:
        """
        Exporta relatório executivo completo em PDF
        
        Args:
            nfe: Dados da NF-e
            classificacoes: Classificações NCM dos itens
            resultado: Resultado da análise de fraudes
            output_path: Caminho para salvar o PDF
            
        Returns:
            str: Caminho do arquivo PDF gerado
        """
        
        # Criar documento PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Construir conteúdo
        story = []
        
        # Cabeçalho
        story.extend(self._build_header())
        
        # Resumo executivo
        story.extend(self._build_resumo_executivo(nfe, resultado))
        
        # Dados da NF-e
        story.extend(self._build_dados_nfe(nfe))
        
        # Classificações NCM
        story.extend(self._build_classificacoes_ncm(classificacoes))
        
        # Análise de fraudes
        story.extend(self._build_analise_fraudes(resultado))
        
        # Recomendações
        story.extend(self._build_recomendacoes(resultado))
        
        # Rodapé
        story.extend(self._build_footer())
        
        # Gerar PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        return output_path
    
    def _build_header(self) -> List:
        """Constrói cabeçalho do relatório"""
        elements = []
        
        # Título principal
        elements.append(Paragraph("🚀 FiscalAI MVP", self.styles['CustomTitle']))
        elements.append(Paragraph("Sistema de Análise Fiscal Inteligente", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        # Data e hora
        now = datetime.now()
        elements.append(Paragraph(f"Relatório gerado em: {now.strftime('%d/%m/%Y às %H:%M:%S')}", 
                                 self.styles['CustomNormal']))
        elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_resumo_executivo(self, nfe: NFe, resultado: ResultadoAnalise) -> List:
        """Constrói seção de resumo executivo"""
        elements = []
        
        elements.append(Paragraph("📊 RESUMO EXECUTIVO", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        # Score de risco
        risco_color = self._get_risco_color(resultado.nivel_risco)
        elements.append(Paragraph(f"<b>Score de Risco:</b> {resultado.score_risco}/100", 
                                 self.styles['CustomNormal']))
        elements.append(Paragraph(f"<b>Nível de Risco:</b> <font color='{risco_color}'>{resultado.nivel_risco.upper()}</font>", 
                                 self.styles['CustomNormal']))
        elements.append(Spacer(1, 8))
        
        # Status geral
        if resultado.score_risco < 30:
            status_text = "✅ APROVADO - Processamento pode prosseguir normalmente"
            status_style = 'Success'
        elif resultado.score_risco < 60:
            status_text = "⚡ ATENÇÃO - Verificar pontos destacados"
            status_style = 'CustomNormal'
        elif resultado.score_risco < 85:
            status_text = "⚠️ REVISÃO OBRIGATÓRIA - Análise manual necessária"
            status_style = 'Alert'
        else:
            status_text = "🚨 BLOQUEIO IMEDIATO - Investigação completa necessária"
            status_style = 'Alert'
        
        elements.append(Paragraph(f"<b>Status:</b> {status_text}", self.styles[status_style]))
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_dados_nfe(self, nfe: NFe) -> List:
        """Constrói seção com dados da NF-e"""
        elements = []
        
        elements.append(Paragraph("📄 DADOS DA NOTA FISCAL", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        # Tabela com dados principais
        data = [
            ['Campo', 'Valor'],
            ['Número da NF-e', nfe.numero],
            ['Chave de Acesso', nfe.chave_acesso],
            ['Data de Emissão', nfe.data_emissao.strftime('%d/%m/%Y')],
            ['CNPJ Emitente', nfe.emitente.cnpj],
            ['Nome Emitente', nfe.emitente.nome],
            ['CNPJ Destinatário', nfe.destinatario.cnpj],
            ['Nome Destinatário', nfe.destinatario.nome],
            ['Valor Total', f"R$ {nfe.valor_total:,.2f}"],
            ['Quantidade de Itens', str(len(nfe.itens))]
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_classificacoes_ncm(self, classificacoes: Dict[int, ClassificacaoNCM]) -> List:
        """Constrói seção de classificações NCM"""
        elements = []
        
        elements.append(Paragraph("🏷️ CLASSIFICAÇÕES NCM", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        for item_id, classificacao in classificacoes.items():
            elements.append(Paragraph(f"<b>Item {item_id}:</b> {classificacao.descricao_produto}", 
                                     self.styles['CustomHeading2']))
            
            # Tabela de classificação
            data = [
                ['Aspecto', 'Valor'],
                ['NCM Declarado', classificacao.ncm_declarado],
                ['NCM Predito', classificacao.ncm_predito],
                ['Confiança', f"{classificacao.confianca:.1%}"],
                ['Status', '✅ Correto' if classificacao.ncm_declarado == classificacao.ncm_predito else '⚠️ Divergente']
            ]
            
            table = Table(data, colWidths=[2*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(table)
            
            # Justificativa
            if classificacao.justificativa:
                elements.append(Paragraph(f"<b>Justificativa:</b> {classificacao.justificativa}", 
                                         self.styles['CustomNormal']))
            
            elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_analise_fraudes(self, resultado: ResultadoAnalise) -> List:
        """Constrói seção de análise de fraudes"""
        elements = []
        
        elements.append(Paragraph("🔍 ANÁLISE DE FRAUDES", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        if not resultado.fraudes_detectadas:
            elements.append(Paragraph("✅ Nenhuma fraude detectada!", self.styles['Success']))
            elements.append(Paragraph("A NF-e passou por todos os testes de detecção de fraudes sem problemas identificados.", 
                                     self.styles['CustomNormal']))
        else:
            elements.append(Paragraph(f"⚠️ {len(resultado.fraudes_detectadas)} fraude(s) detectada(s):", 
                                     self.styles['Alert']))
            elements.append(Spacer(1, 8))
            
            for i, fraude in enumerate(resultado.fraudes_detectadas, 1):
                elements.append(Paragraph(f"<b>{i}. {fraude.tipo_fraude.value.upper()}</b>", 
                                         self.styles['CustomHeading2']))
                elements.append(Paragraph(f"<b>Score:</b> {fraude.score}/100", self.styles['CustomNormal']))
                elements.append(Paragraph(f"<b>Descrição:</b> {fraude.descricao}", self.styles['CustomNormal']))
                
                if fraude.evidencias:
                    elements.append(Paragraph(f"<b>Evidências:</b> {fraude.evidencias}", self.styles['CustomNormal']))
                
                elements.append(Spacer(1, 8))
        
        elements.append(Spacer(1, 12))
        return elements
    
    def _build_recomendacoes(self, resultado: ResultadoAnalise) -> List:
        """Constrói seção de recomendações"""
        elements = []
        
        elements.append(Paragraph("💡 RECOMENDAÇÕES", self.styles['CustomHeading1']))
        elements.append(Spacer(1, 12))
        
        # Gerar recomendações baseadas no nível de risco
        recomendacoes = self._gerar_recomendacoes_finais(resultado)
        
        for i, recomendacao in enumerate(recomendacoes, 1):
            elements.append(Paragraph(f"{i}. {recomendacao}", self.styles['CustomNormal']))
        
        elements.append(Spacer(1, 20))
        return elements
    
    def _build_footer(self) -> List:
        """Constrói rodapé do relatório"""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("⚠️ <b>Aviso Legal:</b> Este relatório é gerado automaticamente pelo FiscalAI MVP. "
                                 "Para decisões fiscais importantes, consulte sempre um especialista fiscal qualificado.", 
                                 self.styles['CustomNormal']))
        elements.append(Paragraph("Desenvolvido com ❤️ e IA - FiscalAI MVP", 
                                 self.styles['CustomNormal']))
        
        return elements
    
    def _gerar_recomendacoes_finais(self, resultado: ResultadoAnalise) -> List[str]:
        """Gera recomendações estratégicas finais"""
        recomendacoes = []
        
        if resultado.nivel_risco == "critico":
            recomendacoes.append("🚨 BLOQUEIO IMEDIATO: Não processar esta NF-e até investigação completa")
            recomendacoes.append("Acionar departamento jurídico e compliance")
            recomendacoes.append("Considerar auditoria completa do fornecedor")
        
        elif resultado.nivel_risco == "alto":
            recomendacoes.append("⚠️ REVISÃO OBRIGATÓRIA: Análise manual por especialista fiscal")
            recomendacoes.append("Solicitar esclarecimentos formais do fornecedor")
            recomendacoes.append("Registrar ocorrência para monitoramento futuro")
        
        elif resultado.nivel_risco == "medio":
            recomendacoes.append("⚡ ATENÇÃO: Verificar pontos destacados antes de aprovar")
            recomendacoes.append("Manter registro para análise de tendências")
        
        else:
            recomendacoes.append("✅ APROVADO: Processar normalmente")
            recomendacoes.append("Manter monitoramento de rotina")
        
        # Recomendações específicas
        if len(resultado.fraudes_detectadas) > 0:
            tipos_fraude = set(f.tipo_fraude.value for f in resultado.fraudes_detectadas)
            if "subfaturamento" in tipos_fraude:
                recomendacoes.append("💰 Validar preços com pesquisa de mercado")
            if "ncm_incorreto" in tipos_fraude:
                recomendacoes.append("📋 Solicitar reclassificação NCM do fornecedor")
            if "triangulacao" in tipos_fraude:
                recomendacoes.append("🔄 Investigar cadeia completa de transações")
        
        return recomendacoes
    
    def _get_risco_color(self, nivel_risco: str) -> str:
        """Retorna cor baseada no nível de risco"""
        cores = {
            "baixo": "green",
            "medio": "orange", 
            "alto": "red",
            "critico": "darkred"
        }
        return cores.get(nivel_risco.lower(), "black")
    
    def _add_page_number(self, canvas, doc):
        """Adiciona número da página"""
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.drawRightString(200*mm, 20*mm, text)
        canvas.restoreState()


# Função utilitária para exportação rápida
def exportar_relatorio_pdf(nfe: NFe, 
                          classificacoes: Dict[int, ClassificacaoNCM],
                          resultado: ResultadoAnalise,
                          output_path: str = None) -> str:
    """
    Função utilitária para exportação rápida de relatório PDF
    
    Args:
        nfe: Dados da NF-e
        classificacoes: Classificações NCM
        resultado: Resultado da análise
        output_path: Caminho opcional (se None, gera automaticamente)
        
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"relatorio_fiscal_{timestamp}.pdf"
    
    exporter = PDFExporter()
    return exporter.export_relatorio_executivo(nfe, classificacoes, resultado, output_path)
