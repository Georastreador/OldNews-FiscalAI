"""
FiscalAI MVP - Processador Assíncrono
Processamento paralelo de múltiplos arquivos para melhor performance
"""

import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import threading
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)

@dataclass
class ProcessingTask:
    """Tarefa de processamento"""
    task_id: str
    file_path: str
    file_type: str
    priority: int = 0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class ProcessingResult:
    """Resultado do processamento"""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    processing_time: float = 0.0
    memory_used: int = 0

class AsyncProcessor:
    """
    Processador assíncrono para múltiplos arquivos
    
    Funcionalidades:
    - Processamento paralelo
    - Fila de prioridades
    - Pool de workers
    - Monitoramento de progresso
    - Retry automático
    """
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 100):
        """
        Inicializa o processador assíncrono
        
        Args:
            max_workers: Número máximo de workers paralelos
            max_queue_size: Tamanho máximo da fila
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_queue = Queue(maxsize=max_queue_size)
        self.results = {}
        self.workers = []
        self.running = False
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'total_time': 0.0
        }
        
        # Thread pool para processamento
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Lock para thread safety
        self.lock = threading.Lock()
    
    def start(self):
        """Inicia o processador"""
        if self.running:
            logger.warning("Processador já está rodando")
            return
        
        self.running = True
        logger.info(f"Processador assíncrono iniciado com {self.max_workers} workers")
    
    def stop(self):
        """Para o processador"""
        self.running = False
        
        # Aguardar workers terminarem
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5.0)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Processador assíncrono parado")
    
    def add_task(self, task: ProcessingTask) -> bool:
        """
        Adiciona tarefa à fila de processamento
        
        Args:
            task: Tarefa para processar
            
        Returns:
            True se adicionada com sucesso
        """
        try:
            self.task_queue.put(task, block=False)
            logger.debug(f"Tarefa {task.task_id} adicionada à fila")
            return True
        except:
            logger.error(f"Falha ao adicionar tarefa {task.task_id} - fila cheia")
            return False
    
    def add_tasks(self, tasks: List[ProcessingTask]) -> int:
        """
        Adiciona múltiplas tarefas à fila
        
        Args:
            tasks: Lista de tarefas
            
        Returns:
            Número de tarefas adicionadas com sucesso
        """
        added_count = 0
        for task in tasks:
            if self.add_task(task):
                added_count += 1
        
        logger.info(f"Adicionadas {added_count}/{len(tasks)} tarefas à fila")
        return added_count
    
    def process_async(self, 
                     files: List[Dict[str, Any]], 
                     processor_func: Callable,
                     progress_callback: Optional[Callable] = None) -> List[ProcessingResult]:
        """
        Processa múltiplos arquivos de forma assíncrona
        
        Args:
            files: Lista de arquivos para processar
            processor_func: Função de processamento
            progress_callback: Callback para progresso
            
        Returns:
            Lista de resultados
        """
        # Criar tarefas
        tasks = []
        for i, file_info in enumerate(files):
            task = ProcessingTask(
                task_id=f"task_{i}_{int(time.time())}",
                file_path=file_info.get('path', ''),
                file_type=file_info.get('type', 'unknown'),
                priority=file_info.get('priority', 0)
            )
            tasks.append(task)
        
        # Adicionar tarefas à fila
        self.add_tasks(tasks)
        
        # Processar tarefas
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as tarefas
            future_to_task = {
                executor.submit(self._process_single_task, task, processor_func): task
                for task in tasks
            }
            
            # Coletar resultados conforme completam
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Atualizar estatísticas
                    with self.lock:
                        self.stats['total_processed'] += 1
                        if result.success:
                            self.stats['successful'] += 1
                        else:
                            self.stats['failed'] += 1
                        self.stats['total_time'] += result.processing_time
                    
                    # Callback de progresso
                    if progress_callback:
                        progress_callback(len(results), len(tasks), result)
                        
                except Exception as e:
                    logger.error(f"Erro ao processar tarefa {task.task_id}: {e}")
                    results.append(ProcessingResult(
                        task_id=task.task_id,
                        success=False,
                        error=str(e)
                    ))
        
        return results
    
    def _process_single_task(self, task: ProcessingTask, processor_func: Callable) -> ProcessingResult:
        """
        Processa uma única tarefa
        
        Args:
            task: Tarefa para processar
            processor_func: Função de processamento
            
        Returns:
            Resultado do processamento
        """
        start_time = time.time()
        task.status = "running"
        task.started_at = datetime.now()
        
        try:
            # Processar arquivo
            result = processor_func(task.file_path, task.file_type)
            
            # Calcular tempo de processamento
            processing_time = time.time() - start_time
            
            # Atualizar tarefa
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result
            
            return ProcessingResult(
                task_id=task.task_id,
                success=True,
                result=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            # Atualizar tarefa com erro
            task.status = "failed"
            task.completed_at = datetime.now()
            task.error = str(e)
            
            processing_time = time.time() - start_time
            
            logger.error(f"Erro ao processar {task.file_path}: {e}")
            
            return ProcessingResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do processador"""
        with self.lock:
            return {
                'total_processed': self.stats['total_processed'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'success_rate': (
                    self.stats['successful'] / self.stats['total_processed'] * 100
                    if self.stats['total_processed'] > 0 else 0
                ),
                'avg_processing_time': (
                    self.stats['total_time'] / self.stats['total_processed']
                    if self.stats['total_processed'] > 0 else 0
                ),
                'queue_size': self.task_queue.qsize(),
                'max_workers': self.max_workers
            }
    
    def clear_queue(self):
        """Limpa a fila de tarefas pendentes"""
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except Empty:
                break
        
        logger.info("Fila de tarefas limpa")


class BatchProcessor:
    """
    Processador em lote para arquivos CSV múltiplos
    
    Funcionalidades:
    - Processamento em lotes
    - Agregação de resultados
    - Relatórios consolidados
    """
    
    def __init__(self, processor: AsyncProcessor):
        """
        Inicializa o processador em lote
        
        Args:
            processor: Instância do processador assíncrono
        """
        self.processor = processor
        self.batch_results = []
    
    def process_csv_batch(self, 
                         csv_files: List[str], 
                         processor_func: Callable,
                         batch_size: int = 10) -> Dict[str, Any]:
        """
        Processa lote de arquivos CSV
        
        Args:
            csv_files: Lista de caminhos dos arquivos CSV
            processor_func: Função de processamento
            batch_size: Tamanho do lote
            
        Returns:
            Resultado consolidado do lote
        """
        logger.info(f"Processando lote de {len(csv_files)} arquivos CSV")
        
        # Preparar arquivos para processamento
        files = []
        for i, csv_file in enumerate(csv_files):
            files.append({
                'path': csv_file,
                'type': 'csv',
                'priority': i % batch_size  # Distribuir prioridades
            })
        
        # Processar em lotes
        all_results = []
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i + batch_size]
            batch_results = self.processor.process_async(
                batch_files, 
                processor_func
            )
            all_results.extend(batch_results)
            
            logger.info(f"Lote {i//batch_size + 1} processado: {len(batch_results)} arquivos")
        
        # Consolidar resultados
        consolidated_result = self._consolidate_results(all_results)
        
        logger.info(f"Processamento em lote concluído: {len(all_results)} arquivos processados")
        return consolidated_result
    
    def _consolidate_results(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """
        Consolida resultados de múltiplos arquivos
        
        Args:
            results: Lista de resultados
            
        Returns:
            Resultado consolidado
        """
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        # Estatísticas gerais
        stats = {
            'total_files': len(results),
            'successful_files': len(successful_results),
            'failed_files': len(failed_results),
            'success_rate': len(successful_results) / len(results) * 100 if results else 0,
            'total_processing_time': sum(r.processing_time for r in results),
            'avg_processing_time': sum(r.processing_time for r in results) / len(results) if results else 0
        }
        
        # Agregar dados dos resultados bem-sucedidos
        aggregated_data = {
            'total_nfes': 0,
            'total_frauds': 0,
            'total_items': 0,
            'avg_risk_score': 0.0,
            'fraud_types': {},
            'risk_levels': {}
        }
        
        for result in successful_results:
            if result.result:
                # Agregar dados do resultado
                if hasattr(result.result, 'total_nfes'):
                    aggregated_data['total_nfes'] += result.result.total_nfes
                if hasattr(result.result, 'total_frauds'):
                    aggregated_data['total_frauds'] += result.result.total_frauds
                if hasattr(result.result, 'total_items'):
                    aggregated_data['total_items'] += result.result.total_items
        
        return {
            'stats': stats,
            'aggregated_data': aggregated_data,
            'individual_results': results,
            'failed_files': [r.task_id for r in failed_results]
        }


# Instâncias globais
_async_processor: Optional[AsyncProcessor] = None
_batch_processor: Optional[BatchProcessor] = None

def get_async_processor() -> AsyncProcessor:
    """Retorna instância global do processador assíncrono"""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncProcessor()
        _async_processor.start()
    return _async_processor

def get_batch_processor() -> BatchProcessor:
    """Retorna instância global do processador em lote"""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor(get_async_processor())
    return _batch_processor

def shutdown_processors():
    """Para todos os processadores"""
    global _async_processor, _batch_processor
    
    if _async_processor:
        _async_processor.stop()
        _async_processor = None
    
    _batch_processor = None
