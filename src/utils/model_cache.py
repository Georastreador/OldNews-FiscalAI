"""
FiscalAI MVP - Cache Persistente de Modelos
Sistema de cache inteligente para modelos LLM
"""

import os
import pickle
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import logging
import threading
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ModelCacheEntry:
    """Entrada do cache de modelo"""
    model_name: str
    model_type: str
    provider: str
    cache_key: str
    created_at: datetime
    last_accessed: datetime
    access_count: int
    model_size_mb: float
    load_time_seconds: float
    is_loaded: bool
    model_data: Optional[Any] = None

class ModelCache:
    """
    Cache persistente para modelos LLM
    
    Funcionalidades:
    - Cache em disco
    - Compressão de modelos
    - LRU eviction
    - Validação de integridade
    - Métricas de uso
    - Preload de modelos
    """
    
    def __init__(self, 
                 cache_dir: str = "model_cache",
                 max_size_mb: int = 2000,  # 2GB
                 max_entries: int = 50,
                 compression: bool = True):
        """
        Inicializa o cache de modelos
        
        Args:
            cache_dir: Diretório do cache
            max_size_mb: Tamanho máximo em MB
            max_entries: Número máximo de entradas
            compression: Se deve comprimir modelos
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.compression = compression
        
        # Cache em memória
        self.memory_cache: Dict[str, ModelCacheEntry] = {}
        self.lock = threading.RLock()
        
        # Arquivo de metadados
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()
        
        # Limpar cache expirado
        self._cleanup_expired()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Carrega metadados do cache"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar metadados do cache: {e}")
        return {}
    
    def _save_metadata(self):
        """Salva metadados do cache"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erro ao salvar metadados do cache: {e}")
    
    def _generate_cache_key(self, model_name: str, model_type: str, provider: str, config: Dict[str, Any]) -> str:
        """
        Gera chave de cache baseada na configuração do modelo
        
        Args:
            model_name: Nome do modelo
            model_type: Tipo do modelo
            provider: Provedor do modelo
            config: Configuração do modelo
            
        Returns:
            Chave de cache única
        """
        # Criar string de configuração
        config_str = json.dumps({
            'model_name': model_name,
            'model_type': model_type,
            'provider': provider,
            'config': config
        }, sort_keys=True)
        
        # Gerar hash
        hash_obj = hashlib.sha256(config_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Retorna caminho do arquivo de cache"""
        return self.cache_dir / f"{cache_key}.model"
    
    def _is_expired(self, entry: ModelCacheEntry, ttl_hours: int = 24) -> bool:
        """Verifica se entrada expirou"""
        ttl = timedelta(hours=ttl_hours)
        return datetime.now() - entry.last_accessed > ttl
    
    def _cleanup_expired(self):
        """Remove entradas expiradas"""
        with self.lock:
            expired_keys = []
            for cache_key, entry in self.memory_cache.items():
                if self._is_expired(entry):
                    expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                self._remove_entry(cache_key)
            
            if expired_keys:
                logger.info(f"Removidas {len(expired_keys)} entradas expiradas do cache de modelos")
    
    def _remove_entry(self, cache_key: str):
        """Remove entrada do cache"""
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            
            # Remover arquivo do disco
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo de cache {cache_key}: {e}")
            
            # Remover da memória
            del self.memory_cache[cache_key]
            
            # Atualizar metadados
            if cache_key in self.metadata:
                del self.metadata[cache_key]
    
    def _get_cache_size(self) -> int:
        """Calcula tamanho atual do cache em bytes"""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.model"):
            total_size += cache_file.stat().st_size
        return total_size
    
    def _evict_lru(self):
        """Remove entrada menos recentemente usada"""
        if not self.memory_cache:
            return
        
        # Encontrar entrada com menor last_accessed
        lru_key = min(self.memory_cache.keys(), 
                     key=lambda k: self.memory_cache[k].last_accessed)
        
        logger.info(f"Removendo modelo LRU: {lru_key}")
        self._remove_entry(lru_key)
    
    def _ensure_space(self, required_size: int):
        """Garante espaço suficiente no cache"""
        while (self._get_cache_size() + required_size > self.max_size_bytes or 
               len(self.memory_cache) >= self.max_entries):
            self._evict_lru()
    
    def get_model(self, 
                  model_name: str, 
                  model_type: str, 
                  provider: str, 
                  config: Dict[str, Any]) -> Optional[Any]:
        """
        Recupera modelo do cache
        
        Args:
            model_name: Nome do modelo
            model_type: Tipo do modelo
            provider: Provedor do modelo
            config: Configuração do modelo
            
        Returns:
            Modelo em cache ou None
        """
        with self.lock:
            cache_key = self._generate_cache_key(model_name, model_type, provider, config)
            
            # Verificar cache em memória
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                
                # Verificar se expirou
                if self._is_expired(entry):
                    self._remove_entry(cache_key)
                    return None
                
                # Atualizar estatísticas
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                
                logger.debug(f"Cache hit para modelo {model_name}")
                return entry.model_data
            
            # Verificar cache em disco
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    # Carregar do disco
                    with open(cache_path, 'rb') as f:
                        if self.compression:
                            import gzip
                            with gzip.GzipFile(fileobj=f, mode='rb') as gz:
                                model_data = pickle.load(gz)
                        else:
                            model_data = pickle.load(f)
                    
                    # Calcular tamanho
                    model_size = cache_path.stat().st_size / (1024 * 1024)  # MB
                    
                    # Criar entrada
                    entry = ModelCacheEntry(
                        model_name=model_name,
                        model_type=model_type,
                        provider=provider,
                        cache_key=cache_key,
                        created_at=datetime.now(),
                        last_accessed=datetime.now(),
                        access_count=1,
                        model_size_mb=model_size,
                        load_time_seconds=0.0,
                        is_loaded=True,
                        model_data=model_data
                    )
                    
                    # Adicionar ao cache em memória
                    self.memory_cache[cache_key] = entry
                    
                    logger.info(f"Modelo {model_name} carregado do cache em disco")
                    return model_data
                    
                except Exception as e:
                    logger.warning(f"Erro ao carregar modelo do cache: {e}")
                    # Remover arquivo corrompido
                    try:
                        cache_path.unlink()
                    except:
                        pass
            
            return None
    
    def put_model(self, 
                  model_name: str, 
                  model_type: str, 
                  provider: str, 
                  config: Dict[str, Any], 
                  model_data: Any) -> bool:
        """
        Armazena modelo no cache
        
        Args:
            model_name: Nome do modelo
            model_type: Tipo do modelo
            provider: Provedor do modelo
            config: Configuração do modelo
            model_data: Dados do modelo
            
        Returns:
            True se armazenado com sucesso
        """
        with self.lock:
            cache_key = self._generate_cache_key(model_name, model_type, provider, config)
            
            # Calcular tamanho estimado
            try:
                serialized = pickle.dumps(model_data)
                estimated_size = len(serialized)
            except Exception as e:
                logger.error(f"Erro ao serializar modelo {model_name}: {e}")
                return False
            
            # Garantir espaço
            self._ensure_space(estimated_size)
            
            try:
                # Salvar no disco
                cache_path = self._get_cache_path(cache_key)
                with open(cache_path, 'wb') as f:
                    if self.compression:
                        import gzip
                        with gzip.GzipFile(fileobj=f, mode='wb') as gz:
                            pickle.dump(model_data, gz)
                    else:
                        pickle.dump(model_data, f)
                
                # Calcular tamanho real
                actual_size = cache_path.stat().st_size / (1024 * 1024)  # MB
                
                # Criar entrada
                entry = ModelCacheEntry(
                    model_name=model_name,
                    model_type=model_type,
                    provider=provider,
                    cache_key=cache_key,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    access_count=0,
                    model_size_mb=actual_size,
                    load_time_seconds=0.0,
                    is_loaded=True,
                    model_data=model_data
                )
                
                # Adicionar ao cache em memória
                self.memory_cache[cache_key] = entry
                
                # Atualizar metadados
                self.metadata[cache_key] = {
                    'model_name': model_name,
                    'model_type': model_type,
                    'provider': provider,
                    'created_at': entry.created_at.isoformat(),
                    'size_mb': actual_size
                }
                self._save_metadata()
                
                logger.info(f"Modelo {model_name} armazenado no cache ({actual_size:.2f} MB)")
                return True
                
            except Exception as e:
                logger.error(f"Erro ao armazenar modelo {model_name} no cache: {e}")
                return False
    
    def preload_models(self, model_configs: List[Dict[str, Any]]):
        """
        Pré-carrega modelos especificados
        
        Args:
            model_configs: Lista de configurações de modelos
        """
        logger.info(f"Iniciando preload de {len(model_configs)} modelos")
        
        for config in model_configs:
            try:
                model_name = config['model_name']
                model_type = config['model_type']
                provider = config['provider']
                
                # Verificar se já está em cache
                if self.get_model(model_name, model_type, provider, config):
                    logger.debug(f"Modelo {model_name} já está em cache")
                    continue
                
                # Aqui você implementaria o carregamento real do modelo
                # Por enquanto, apenas log
                logger.info(f"Preload de {model_name} seria executado aqui")
                
            except Exception as e:
                logger.error(f"Erro no preload do modelo {config}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        with self.lock:
            total_entries = len(self.memory_cache)
            total_size = self._get_cache_size()
            
            # Calcular estatísticas de acesso
            access_counts = [entry.access_count for entry in self.memory_cache.values()]
            avg_access = sum(access_counts) / total_entries if total_entries > 0 else 0
            
            # Modelos por provedor
            providers = {}
            for entry in self.memory_cache.values():
                provider = entry.provider
                if provider not in providers:
                    providers[provider] = 0
                providers[provider] += 1
            
            return {
                'total_entries': total_entries,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                'usage_percentage': round((total_size / self.max_size_bytes) * 100, 2),
                'avg_access_count': round(avg_access, 2),
                'providers': providers,
                'compression_enabled': self.compression
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Alias para get_stats() - compatibilidade com código existente"""
        return self.get_stats()
    
    def cleanup_expired(self):
        """Método público para limpeza de cache expirado"""
        self._cleanup_expired()
    
    def clear_cache(self):
        """Limpa todo o cache"""
        with self.lock:
            # Remover todos os arquivos
            for cache_file in self.cache_dir.glob("*.model"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Erro ao remover {cache_file}: {e}")
            
            # Limpar memória
            self.memory_cache.clear()
            self.metadata.clear()
            self._save_metadata()
            
            logger.info("Cache de modelos limpo")
    
    def cleanup_old_models(self, days_old: int = 7):
        """Remove modelos antigos"""
        with self.lock:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            old_entries = []
            
            for cache_key, entry in self.memory_cache.items():
                if entry.last_accessed < cutoff_date:
                    old_entries.append(cache_key)
            
            for cache_key in old_entries:
                self._remove_entry(cache_key)
            
            if old_entries:
                logger.info(f"Removidos {len(old_entries)} modelos antigos")


# Instância global do cache
_model_cache_instance: Optional[ModelCache] = None

def get_model_cache() -> ModelCache:
    """Retorna instância global do cache de modelos"""
    global _model_cache_instance
    if _model_cache_instance is None:
        _model_cache_instance = ModelCache()
    return _model_cache_instance

def cache_model(model_name: str, model_type: str, provider: str, 
                config: Dict[str, Any], model_data: Any) -> bool:
    """Função de conveniência para armazenar modelo"""
    return get_model_cache().put_model(model_name, model_type, provider, config, model_data)

def get_cached_model(model_name: str, model_type: str, provider: str, 
                    config: Dict[str, Any]) -> Optional[Any]:
    """Função de conveniência para recuperar modelo"""
    return get_model_cache().get_model(model_name, model_type, provider, config)

def get_model_cache_stats() -> Dict[str, Any]:
    """Função de conveniência para obter estatísticas"""
    return get_model_cache().get_stats()

def clear_model_cache():
    """Função de conveniência para limpar cache"""
    get_model_cache().clear_cache()
