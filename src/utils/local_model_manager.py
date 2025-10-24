"""
FiscalAI MVP - Gerenciador de Modelos Locais
Suporte para modelos GGUF (Mistral, Llama, etc.) com privacidade total
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python não está instalado. Modelos locais não estarão disponíveis.")

from ..models.schemas import LLMProvider, LLMConfig

logger = logging.getLogger(__name__)

class LocalModelManager:
    """Gerenciador de modelos locais GGUF"""
    
    def __init__(self, models_dir: str = None):
        """
        Inicializa o gerenciador de modelos locais
        
        Args:
            models_dir: Diretório onde estão os modelos GGUF
        """
        if models_dir is None:
            # Tentar encontrar o diretório models automaticamente
            current_dir = Path(__file__).parent
            possible_paths = [
                current_dir.parent.parent / "models",  # FiscalAI_MVP/models
                current_dir.parent.parent.parent / "models",  # ROC_FiscalAI/models
                Path("models"),  # Diretório atual
                Path("../models"),  # Um nível acima
            ]
            
            for path in possible_paths:
                if path.exists() and path.is_dir():
                    models_dir = str(path)
                    break
            
            if models_dir is None:
                models_dir = "models"  # Fallback
        
        self.models_dir = Path(models_dir)
        self.loaded_models: Dict[str, Llama] = {}
        self.model_configs: Dict[str, Dict[str, Any]] = {}
        
        # Configurações padrão para diferentes modelos
        self.default_configs = {
            "mistral-7b-instruct": {
                "context_length": 4096,
                "n_gpu_layers": -1,  # Usar GPU se disponível
                "n_threads": 8,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048,
                "stop": ["</s>", "[INST]", "[/INST]"]
            },
            "llama-2-7b-chat": {
                "context_length": 4096,
                "n_gpu_layers": -1,
                "n_threads": 8,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048,
                "stop": ["</s>", "[INST]", "[/INST]"]
            }
        }
        
        self._discover_models()
    
    def _discover_models(self):
        """Descobre modelos GGUF disponíveis no diretório"""
        if not self.models_dir.exists():
            logger.warning(f"Diretório de modelos não encontrado: {self.models_dir}")
            return
        
        for model_file in self.models_dir.glob("*.gguf"):
            model_name = model_file.stem
            self.model_configs[model_name] = {
                "path": str(model_file),
                "size_mb": model_file.stat().st_size / (1024 * 1024),
                "last_modified": datetime.fromtimestamp(model_file.stat().st_mtime)
            }
            
            # Aplica configuração padrão se disponível
            for config_name, config in self.default_configs.items():
                if config_name in model_name.lower():
                    self.model_configs[model_name].update(config)
                    break
        
        logger.info(f"Descobertos {len(self.model_configs)} modelos locais")
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """Lista modelos locais disponíveis"""
        models = []
        for name, config in self.model_configs.items():
            models.append({
                "name": name,
                "path": config["path"],
                "size_mb": config["size_mb"],
                "last_modified": config["last_modified"],
                "loaded": name in self.loaded_models
            })
        return models
    
    def load_model(self, model_name: str, **kwargs) -> bool:
        """
        Carrega um modelo GGUF
        
        Args:
            model_name: Nome do modelo
            **kwargs: Parâmetros adicionais para o modelo
            
        Returns:
            True se carregado com sucesso
        """
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama-cpp-python não está disponível")
            return False
        
        if model_name not in self.model_configs:
            logger.error(f"Modelo não encontrado: {model_name}")
            return False
        
        if model_name in self.loaded_models:
            logger.info(f"Modelo {model_name} já está carregado")
            return True
        
        try:
            model_path = self.model_configs[model_name]["path"]
            config = self.model_configs[model_name].copy()
            config.update(kwargs)
            
            logger.info(f"Carregando modelo local: {model_name}")
            logger.info(f"Caminho: {model_path}")
            logger.info(f"Tamanho: {config['size_mb']:.1f} MB")
            
            # Remove parâmetros não suportados pelo Llama
            llama_params = {k: v for k, v in config.items() 
                          if k not in ["path", "size_mb", "last_modified"]}
            
            model = Llama(
                model_path=model_path,
                **llama_params
            )
            
            self.loaded_models[model_name] = model
            logger.info(f"Modelo {model_name} carregado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo {model_name}: {e}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """Descarrega um modelo da memória"""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            logger.info(f"Modelo {model_name} descarregado")
            return True
        return False
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Retorna instância do modelo carregado"""
        return self.loaded_models.get(model_name)
    
    def generate_response(self, model_name: str, prompt: str, **kwargs) -> str:
        """
        Gera resposta usando modelo local
        
        Args:
            model_name: Nome do modelo
            prompt: Prompt para o modelo
            **kwargs: Parâmetros adicionais
            
        Returns:
            Resposta gerada
        """
        if model_name not in self.loaded_models:
            if not self.load_model(model_name):
                return "Erro: Modelo não pôde ser carregado"
        
        model = self.loaded_models[model_name]
        
        try:
            # Truncar prompt se muito longo (limite de contexto do modelo)
            max_context = 512  # Limite conservador para o modelo
            max_response_tokens = 100  # Reduzido para garantir espaço
            max_prompt_tokens = max_context - max_response_tokens - 50  # Margem de segurança
            
            # Estimar tokens (aproximadamente 3.5 caracteres por token para português)
            estimated_tokens = len(prompt) // 3.5
            
            if estimated_tokens > max_prompt_tokens:
                # Truncar prompt mantendo o final (mais relevante)
                chars_to_keep = max_prompt_tokens * 4
                original_length = len(prompt)
                truncated_prompt = prompt[-chars_to_keep:]
                # Adicionar indicador de truncamento
                prompt = f"[Contexto anterior truncado...]\n\n{truncated_prompt}"
                logger.warning(f"Prompt truncado de {original_length} para {len(truncated_prompt)} caracteres")
            
            # Parâmetros padrão
            default_params = {
                "max_tokens": max_response_tokens,  # Usar o valor calculado
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</s>", "[INST]", "[/INST]"]
            }
            default_params.update(kwargs)
            
            # Gera resposta
            response = model(prompt, **default_params)
            
            # Extrai texto da resposta
            if isinstance(response, dict) and "choices" in response:
                return response["choices"][0]["text"].strip()
            elif isinstance(response, str):
                return response.strip()
            else:
                return str(response).strip()
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro ao gerar resposta: {e}")
            
            # Tratar erro específico de contexto excedido
            if "exceed context window" in error_msg:
                return "❌ **Erro de contexto:** O prompt é muito longo para o modelo. Tente fazer uma pergunta mais específica ou resumir o contexto."
            elif "exceed batch size" in error_msg:
                return "❌ **Erro de processamento:** O modelo não conseguiu processar a solicitação. Tente novamente com uma pergunta mais simples."
            else:
                return f"❌ **Erro:** {error_msg}"
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Retorna informações detalhadas do modelo"""
        if model_name not in self.model_configs:
            return {}
        
        info = self.model_configs[model_name].copy()
        info["loaded"] = model_name in self.loaded_models
        info["provider"] = "LOCAL"
        info["privacy"] = "TOTAL"
        
        return info
    
    def estimate_memory_usage(self, model_name: str) -> Dict[str, float]:
        """Estima uso de memória do modelo"""
        if model_name not in self.model_configs:
            return {}
        
        size_mb = self.model_configs[model_name]["size_mb"]
        
        return {
            "model_size_mb": size_mb,
            "estimated_ram_mb": size_mb * 1.2,  # +20% overhead
            "estimated_vram_mb": size_mb * 0.8 if self._has_gpu() else 0
        }
    
    def _has_gpu(self) -> bool:
        """Verifica se há GPU disponível"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def cleanup(self):
        """Limpa todos os modelos carregados"""
        for model_name in list(self.loaded_models.keys()):
            self.unload_model(model_name)
        logger.info("Todos os modelos locais foram descarregados")

# Instância global do gerenciador
_local_model_manager = None

def get_local_model_manager() -> LocalModelManager:
    """Retorna instância global do gerenciador de modelos locais"""
    global _local_model_manager
    if _local_model_manager is None:
        _local_model_manager = LocalModelManager()
    return _local_model_manager

def create_local_llm_config(model_name: str) -> LLMConfig:
    """Cria configuração LLM para modelo local"""
    return LLMConfig(
        provider=LLMProvider.LOCAL,
        model_name=model_name,
        api_key="local",  # Não usado para modelos locais
        base_url="local",
        temperature=0.7,
        max_tokens=2048,
        timeout=60
    )

# Função de conveniência para usar em outros módulos
def get_local_llm(model_name: str = "mistral-7b-instruct-v0.1.Q4_K_M"):
    """
    Retorna instância de LLM local para uso com LangChain
    
    Args:
        model_name: Nome do modelo local
        
    Returns:
        Instância do modelo ou None se não disponível
    """
    if not LLAMA_CPP_AVAILABLE:
        return None
    
    manager = get_local_model_manager()
    
    if model_name not in manager.model_configs:
        logger.error(f"Modelo local não encontrado: {model_name}")
        return None
    
    if not manager.load_model(model_name):
        return None
    
    return manager.get_model(model_name)

if __name__ == "__main__":
    # Teste do gerenciador
    manager = LocalModelManager()
    
    print("🔍 Modelos locais disponíveis:")
    for model in manager.list_available_models():
        print(f"  • {model['name']} ({model['size_mb']:.1f} MB)")
    
    print("\n💾 Uso de memória estimado:")
    for model_name in manager.model_configs.keys():
        memory = manager.estimate_memory_usage(model_name)
        print(f"  • {model_name}: {memory['estimated_ram_mb']:.1f} MB RAM")
