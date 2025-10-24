"""
FiscalAI MVP - FastAPI REST API
API REST para integração externa do sistema FiscalAI
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import tempfile
import os
import uuid
from datetime import datetime
import asyncio
from pathlib import Path

# Adicionar src ao path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import get_model_manager
from src.agents import (
    Agente1Extrator,
    Agente2Classificador,
    Agente3Validador,
    Agente4Orquestrador,
)
from src.models import LLMConfig, LLMProvider
from main import analisar_nfe, exportar_relatorio_pdf

# Configurar FastAPI
app = FastAPI(
    title="FiscalAI MVP API",
    description="API REST para análise fiscal inteligente de NF-e",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para API
class AnaliseRequest(BaseModel):
    """Request para análise de NF-e"""
    xml_content: str
    model_name: Optional[str] = "mistral-7b-local"
    export_pdf: Optional[bool] = False

class AnaliseResponse(BaseModel):
    """Response da análise"""
    success: bool
    analysis_id: str
    nfe_data: Optional[Dict[str, Any]] = None
    classifications: Optional[Dict[str, Any]] = None
    fraud_analysis: Optional[Dict[str, Any]] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    recommendations: Optional[List[str]] = None
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None

class ModelInfo(BaseModel):
    """Informações sobre modelo LLM"""
    name: str
    provider: str
    description: str
    cost_per_1k_tokens: float
    max_context: int
    available: bool

class HealthResponse(BaseModel):
    """Response de health check"""
    status: str
    timestamp: str
    version: str
    models_available: int

# Cache de análises em memória (em produção usar Redis/DB)
analyses_cache: Dict[str, Dict] = {}

@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint raiz"""
    return {
        "message": "FiscalAI MVP API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        model_manager = get_model_manager()
        available_models = len(model_manager.list_available_models())
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            models_available=available_models
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """Lista modelos LLM disponíveis"""
    try:
        model_manager = get_model_manager()
        models = model_manager.list_available_models()
        
        model_list = []
        for name, info in models.items():
            model_list.append(ModelInfo(
                name=name,
                provider=info['provider'].value,
                description=info['description'],
                cost_per_1k_tokens=info['cost_per_1k_tokens'],
                max_context=info.get('max_context', 0),
                available=True
            ))
        
        return model_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")

@app.post("/analyze", response_model=AnaliseResponse)
async def analyze_nfe(request: AnaliseRequest):
    """
    Analisa NF-e XML e retorna relatório completo
    
    Args:
        request: Dados da análise incluindo XML e configurações
        
    Returns:
        Relatório completo da análise
    """
    analysis_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    try:
        # Salvar XML temporariamente
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp_file:
            tmp_file.write(request.xml_content)
            tmp_path = tmp_file.name
        
        try:
            # Executar análise
            resultado = analisar_nfe(tmp_path, request.model_name)
            
            if not resultado["sucesso"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Análise falhou: {resultado.get('erro')}"
                )
            
            # Gerar PDF se solicitado
            pdf_path = None
            if request.export_pdf:
                try:
                    pdf_path = exportar_relatorio_pdf(
                        tmp_path, 
                        request.model_name,
                        f"relatorio_{analysis_id}.pdf"
                    )
                except Exception as e:
                    print(f"Erro ao gerar PDF: {e}")
            
            # Calcular tempo de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Cache do resultado
            analyses_cache[analysis_id] = {
                "timestamp": start_time.isoformat(),
                "result": resultado,
                "pdf_path": pdf_path
            }
            
            # Preparar response
            relatorio = resultado["relatorio"]
            
            return AnaliseResponse(
                success=True,
                analysis_id=analysis_id,
                nfe_data=relatorio.nfe.dict() if relatorio.nfe else None,
                classifications=relatorio.classificacoes_ncm,
                fraud_analysis=relatorio.resultado_analise.dict() if relatorio.resultado_analise else None,
                risk_score=relatorio.resultado_analise.score_risco if relatorio.resultado_analise else None,
                risk_level=relatorio.resultado_analise.nivel_risco.value if relatorio.resultado_analise else None,
                recommendations=relatorio.acoes_recomendadas,
                pdf_path=pdf_path,
                processing_time=processing_time
            )
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        return AnaliseResponse(
            success=False,
            analysis_id=analysis_id,
            error=str(e),
            processing_time=processing_time
        )

@app.post("/analyze/upload", response_model=AnaliseResponse)
async def analyze_nfe_upload(
    file: UploadFile = File(...),
    model_name: str = "mistral-7b-local",
    export_pdf: bool = False
):
    """
    Analisa NF-e XML via upload de arquivo
    
    Args:
        file: Arquivo XML da NF-e
        model_name: Nome do modelo LLM
        export_pdf: Se deve gerar PDF
        
    Returns:
        Relatório completo da análise
    """
    # Validar tipo de arquivo
    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser XML")
    
    # Ler conteúdo do arquivo
    xml_content = await file.read()
    
    try:
        xml_content_str = xml_content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Arquivo XML deve estar em UTF-8")
    
    # Criar request e processar
    request = AnaliseRequest(
        xml_content=xml_content_str,
        model_name=model_name,
        export_pdf=export_pdf
    )
    
    return await analyze_nfe(request)

@app.get("/analysis/{analysis_id}", response_model=AnaliseResponse)
async def get_analysis(analysis_id: str):
    """
    Recupera resultado de análise por ID
    
    Args:
        analysis_id: ID da análise
        
    Returns:
        Resultado da análise
    """
    if analysis_id not in analyses_cache:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    
    cached_data = analyses_cache[analysis_id]
    resultado = cached_data["result"]
    relatorio = resultado["relatorio"]
    
    return AnaliseResponse(
        success=True,
        analysis_id=analysis_id,
        nfe_data=relatorio.nfe.dict() if relatorio.nfe else None,
        classifications=relatorio.classificacoes_ncm,
        fraud_analysis=relatorio.resultado_analise.dict() if relatorio.resultado_analise else None,
        risk_score=relatorio.resultado_analise.score_risco if relatorio.resultado_analise else None,
        risk_level=relatorio.resultado_analise.nivel_risco.value if relatorio.resultado_analise else None,
        recommendations=relatorio.acoes_recomendadas,
        pdf_path=cached_data.get("pdf_path")
    )

@app.get("/analysis/{analysis_id}/pdf")
async def download_pdf(analysis_id: str):
    """
    Download do relatório PDF
    
    Args:
        analysis_id: ID da análise
        
    Returns:
        Arquivo PDF
    """
    if analysis_id not in analyses_cache:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    
    cached_data = analyses_cache[analysis_id]
    pdf_path = cached_data.get("pdf_path")
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF não encontrado")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"relatorio_fiscal_{analysis_id}.pdf"
    )

@app.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """
    Remove análise do cache
    
    Args:
        analysis_id: ID da análise
    """
    if analysis_id not in analyses_cache:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    
    # Remover PDF se existir
    cached_data = analyses_cache[analysis_id]
    pdf_path = cached_data.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        os.unlink(pdf_path)
    
    # Remover do cache
    del analyses_cache[analysis_id]
    
    return {"message": "Análise removida com sucesso"}

@app.get("/analyses", response_model=List[Dict[str, Any]])
async def list_analyses():
    """
    Lista todas as análises no cache
    
    Returns:
        Lista de análises
    """
    analyses_list = []
    for analysis_id, data in analyses_cache.items():
        analyses_list.append({
            "analysis_id": analysis_id,
            "timestamp": data["timestamp"],
            "has_pdf": data.get("pdf_path") is not None
        })
    
    return sorted(analyses_list, key=lambda x: x["timestamp"], reverse=True)

# Endpoints de estatísticas
@app.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """
    Estatísticas da API
    
    Returns:
        Estatísticas de uso
    """
    total_analyses = len(analyses_cache)
    
    # Contar análises por nível de risco
    risk_levels = {"baixo": 0, "medio": 0, "alto": 0, "critico": 0}
    frauds_detected = 0
    
    for data in analyses_cache.values():
        resultado = data["result"]
        if resultado["sucesso"]:
            relatorio = resultado["relatorio"]
            if relatorio.resultado_analise:
                risk_level = relatorio.resultado_analise.nivel_risco.value
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
                
                if relatorio.resultado_analise.fraudes_detectadas:
                    frauds_detected += len(relatorio.resultado_analise.fraudes_detectadas)
    
    return {
        "total_analyses": total_analyses,
        "risk_levels": risk_levels,
        "total_frauds_detected": frauds_detected,
        "cache_size": len(analyses_cache)
    }

# Middleware para logging
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware para logging de requests"""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds()
    
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
