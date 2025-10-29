"""
FiscalAI MVP - Model Manager
Gerencia diferentes provedores de LLM (local e APIs)
"""

from typing import Optional, Dict, Any
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOpenAI, ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv

from ..models import LLMProvider, LLMConfig
from .local_model_manager import get_local_model_manager, create_local_llm_config

load_dotenv()


class LocalGGUFWrapper:
    """Wrapper para modelos GGUF locais compatível com LangChain"""
    
    def __init__(self, local_manager, model_name: str, config: LLMConfig):
        self.local_manager = local_manager
        self.model_name = model_name
        self.config = config
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """Chama o modelo local"""
        # Garantir que max_tokens seja definido e limitado para modelo local
        max_tokens = min(kwargs.get('max_tokens', self.config.max_tokens or 128), 128)
        temperature = kwargs.get('temperature', self.config.temperature)
        
        response = self.local_manager.generate_response(
            self.model_name, 
            prompt, 
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Limpar resposta para evitar repetições
        return self._clean_response(response)
    
    def _clean_response(self, response: str) -> str:
        """Limpa a resposta para evitar repetições e truncamentos"""
        if not response:
            return "Desculpe, não consegui gerar uma resposta."
        
        # Remover prefixos comuns que podem causar repetição
        prefixes_to_remove = [
            "ASSISTANT:",
            "RESPOSTA:",
            "RESPONSE:",
            "ANSWER:",
        ]
        
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Remover linhas duplicadas
        lines = response.split('\n')
        seen_lines = set()
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen_lines:
                seen_lines.add(line_stripped)
                cleaned_lines.append(line)
        
        response = '\n'.join(cleaned_lines)
        
        # Garantir que a resposta termine com ponto
        if response and not response.endswith(('.', '!', '?')):
            response += '.'
        
        return response.strip()
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """Método compatível com LangChain"""
        return self(prompt, **kwargs)
    
    def generate(self, prompts: list, **kwargs) -> list:
        """Gera respostas para múltiplos prompts"""
        return [self(prompt, **kwargs) for prompt in prompts]


class ModelManager:
    """
    Gerenciador centralizado de modelos de IA
    Suporta modelos locais (Ollama) e APIs comerciais
    """
    
    # Configurações padrão dos modelos
    MODELS = {
        "mistral-7b-gguf": {
            "provider": LLMProvider.LOCAL,
            "model": "mistral-7b-instruct-v0.1.Q4_K_M",
            "description": "Mistral 7B Instruct GGUF (Local - Privacidade Total)",
            "cost_per_1k_tokens": 0.0,
            "context_window": 4096,
            "privacy": "TOTAL",
            "type": "GGUF"
        },
        "mistral-7b-ollama": {
            "provider": LLMProvider.LOCAL,
            "model": "mistral:7b-instruct-q4_K_M",
            "description": "Mistral 7B Instruct (Ollama Local)",
            "cost_per_1k_tokens": 0.0,
            "context_window": 8192,
            "privacy": "LOCAL",
            "type": "OLLAMA"
        },
        "llama2-7b-ollama": {
            "provider": LLMProvider.LOCAL,
            "model": "llama2:7b-chat",
            "description": "Llama 2 7B Chat (Ollama Local)",
            "cost_per_1k_tokens": 0.0,
            "context_window": 4096,
            "privacy": "LOCAL",
            "type": "OLLAMA"
        },
        "gpt-4o-mini": {
            "provider": LLMProvider.OPENAI,
            "model": "gpt-4o-mini",
            "description": "GPT-4o Mini (OpenAI)",
            "cost_per_1k_tokens": 0.00015,  # $0.15 per 1M tokens
            "context_window": 128000,
            "privacy": "API",
            "type": "OPENAI"
        },
        "gpt-4o": {
            "provider": LLMProvider.OPENAI,
            "model": "gpt-4o",
            "description": "GPT-4o (OpenAI)",
            "cost_per_1k_tokens": 0.0025,  # $2.50 per 1M tokens
            "context_window": 128000,
        },
        "claude-3.5-sonnet": {
            "provider": LLMProvider.ANTHROPIC,
            "model": "claude-3-5-sonnet-20241022",
            "description": "Claude 3.5 Sonnet (Anthropic)",
            "cost_per_1k_tokens": 0.003,  # $3.00 per 1M tokens
            "context_window": 200000,
        },
        "gemini-1.5-pro": {
            "provider": LLMProvider.GOOGLE,
            "model": "gemini-1.5-pro",
            "description": "Gemini 1.5 Pro (Google)",
            "cost_per_1k_tokens": 0.00125,  # $1.25 per 1M tokens
            "context_window": 1000000,
        },
        "groq-mixtral": {
            "provider": LLMProvider.GROQ,
            "model": "mixtral-8x7b-32768",
            "description": "Mixtral 8x7B (Groq - Free Tier)",
            "cost_per_1k_tokens": 0.0,  # Free tier
            "context_window": 32768,
        },
    }
    
    def __init__(self, default_config: Optional[LLMConfig] = None):
        """
        Inicializa o gerenciador de modelos
        
        Args:
            default_config: Configuração padrão do LLM (opcional)
        """
        self.default_config = default_config or self._load_default_config()
        self._cache: Dict[str, Any] = {}
    
    def _load_default_config(self) -> LLMConfig:
        """Carrega configuração padrão das variáveis de ambiente"""
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "local")
        model = os.getenv("DEFAULT_LLM_MODEL", "mistral-7b-instruct-v0.1.Q4_K_M")
        
        return LLMConfig(
            provider=LLMProvider(provider),
            model=model,
            temperature=0.1,
            max_tokens=512,  # Definir max_tokens padrão para evitar respostas muito longas
        )
    
    def get_llm(self, 
                model_name: Optional[str] = None,
                config: Optional[LLMConfig] = None,
                **kwargs) -> Any:
        """
        Retorna instância do LLM configurado
        
        Args:
            model_name: Nome do modelo (chave do dict MODELS) ou None para usar padrão
            config: Configuração customizada do LLM
            **kwargs: Parâmetros adicionais para o LLM
        
        Returns:
            Instância do LLM configurado
        
        Raises:
            ValueError: Se o modelo não for encontrado ou configuração inválida
        """
        # Usar configuração fornecida ou padrão
        if config is None:
            if model_name and model_name in self.MODELS:
                model_config = self.MODELS[model_name]
                config = LLMConfig(
                    provider=model_config["provider"],
                    model=model_config["model"],
                    temperature=kwargs.get("temperature", 0.1),
                    max_tokens=kwargs.get("max_tokens", 256),  # Definir max_tokens padrão menor
                )
            else:
                config = self.default_config
        
        # Verificar cache
        cache_key = f"{config.provider}_{config.model}_{config.temperature}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Criar instância do LLM baseado no provider
        llm = self._create_llm_instance(config, **kwargs)
        
        # Cachear instância
        self._cache[cache_key] = llm
        
        return llm
    
    def _create_llm_instance(self, config: LLMConfig, **kwargs) -> Any:
        """
        Cria instância do LLM baseado na configuração
        
        Args:
            config: Configuração do LLM
            **kwargs: Parâmetros adicionais
        
        Returns:
            Instância do LLM
        
        Raises:
            ValueError: Se o provider não for suportado ou credenciais faltando
        """
        if config.provider == LLMProvider.LOCAL:
            # Verificar se é modelo GGUF ou Ollama
            model_name = config.model
            if self._is_gguf_model(model_name):
                return self._create_gguf_model(config, **kwargs)
            else:
                return self._create_ollama(config, **kwargs)
        
        elif config.provider == LLMProvider.OPENAI:
            return self._create_openai(config, **kwargs)
        
        elif config.provider == LLMProvider.ANTHROPIC:
            return self._create_anthropic(config, **kwargs)
        
        elif config.provider == LLMProvider.GOOGLE:
            return self._create_google(config, **kwargs)
        
        elif config.provider == LLMProvider.GROQ:
            return self._create_groq(config, **kwargs)
        
        else:
            raise ValueError(f"Provider não suportado: {config.provider}")
    
    def _is_gguf_model(self, model_name: str) -> bool:
        """Verifica se o modelo é GGUF baseado no nome"""
        return model_name.endswith('.gguf') or 'Q4_K_M' in model_name or 'Q8_0' in model_name
    
    def _create_gguf_model(self, config: LLMConfig, **kwargs) -> Any:
        """Cria instância de modelo GGUF local"""
        local_manager = get_local_model_manager()
        
        # Verificar se o modelo está disponível
        available_models = local_manager.list_available_models()
        model_found = None
        
        for model in available_models:
            if config.model in model['name'] or model['name'] in config.model:
                model_found = model['name']
                break
        
        if not model_found:
            raise ValueError(f"Modelo GGUF não encontrado: {config.model}")
        
        # Carregar o modelo
        if not local_manager.load_model(model_found):
            raise ValueError(f"Falha ao carregar modelo GGUF: {model_found}")
        
        # Retornar wrapper para LangChain
        return LocalGGUFWrapper(local_manager, model_found, config)
    
    def _create_ollama(self, config: LLMConfig, **kwargs) -> Ollama:
        """Cria instância do Ollama (modelo local)"""
        return Ollama(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url or "http://localhost:11434",
            **kwargs
        )
    
    def _create_openai(self, config: LLMConfig, **kwargs) -> ChatOpenAI:
        """Cria instância do OpenAI"""
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        
        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=api_key,
            max_tokens=config.max_tokens,
            request_timeout=60,  # Timeout de 60 segundos
            **kwargs
        )
    
    def _create_anthropic(self, config: LLMConfig, **kwargs) -> ChatAnthropic:
        """Cria instância do Anthropic Claude"""
        api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY não configurada")
        
        return ChatAnthropic(
            model=config.model,
            temperature=config.temperature,
            api_key=api_key,
            max_tokens=config.max_tokens or 4096,
            **kwargs
        )
    
    def _create_google(self, config: LLMConfig, **kwargs) -> ChatGoogleGenerativeAI:
        """Cria instância do Google Gemini"""
        api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY não configurada")
        
        return ChatGoogleGenerativeAI(
            model=config.model,
            temperature=config.temperature,
            google_api_key=api_key,
            max_tokens=config.max_tokens,
            **kwargs
        )
    
    def _create_groq(self, config: LLMConfig, **kwargs) -> ChatGroq:
        """Cria instância do Groq"""
        api_key = config.api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY não configurada")
        
        return ChatGroq(
            model=config.model,
            temperature=config.temperature,
            api_key=api_key,
            max_tokens=config.max_tokens,
            **kwargs
        )
    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Lista todos os modelos disponíveis com suas configurações
        
        Returns:
            Dict com informações dos modelos
        """
        models = self.MODELS.copy()
        
        # Adicionar modelos GGUF descobertos dinamicamente
        try:
            local_manager = get_local_model_manager()
            gguf_models = local_manager.list_available_models()
            
            for model in gguf_models:
                model_key = f"gguf-{model['name']}"
                models[model_key] = {
                    "provider": LLMProvider.LOCAL,
                    "model": model['name'],
                    "description": f"{model['name']} (GGUF Local - Privacidade Total)",
                    "cost_per_1k_tokens": 0.0,
                    "context_window": 4096,
                    "privacy": "TOTAL",
                    "type": "GGUF",
                    "size_mb": model['size_mb'],
                    "loaded": model['loaded']
                }
        except Exception as e:
            # Silenciar erro se llama-cpp-python não estiver disponível
            pass
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações sobre um modelo específico
        
        Args:
            model_name: Nome do modelo
        
        Returns:
            Dict com informações ou None se não encontrado
        """
        return self.MODELS.get(model_name)
    
    def estimate_cost(self, model_name: str, num_tokens: int) -> float:
        """
        Estima custo de uso de um modelo
        
        Args:
            model_name: Nome do modelo
            num_tokens: Número de tokens
        
        Returns:
            Custo estimado em reais (conversão aproximada)
        """
        model_info = self.get_model_info(model_name)
        if not model_info:
            return 0.0
        
        cost_usd = (num_tokens / 1000) * model_info["cost_per_1k_tokens"]
        cost_brl = cost_usd * 5.0  # Conversão aproximada USD -> BRL
        
        return cost_brl
    
    def clear_cache(self):
        """Limpa cache de instâncias de LLM"""
        self._cache.clear()


# Instância global do gerenciador (singleton)
_model_manager_instance: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """
    Retorna instância global do ModelManager (singleton)
    
    Returns:
        ModelManager instance
    """
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = ModelManager()
    return _model_manager_instance

