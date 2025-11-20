"""
Cache Monitoring Middleware

Tracks cache hit/miss rates, response times, memory usage, and cache key patterns
for comprehensive cache performance monitoring.
"""
import time
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import psutil
import os

logger = logging.getLogger(__name__)


class CacheMonitorMiddleware(MiddlewareMixin):
    """
    Middleware to monitor cache performance metrics including:
    - Hit/miss rates per endpoint
    - Response time improvements
    - Memory consumption
    - Cache key usage patterns
    """
    
    # In-memory storage for quick access (for current session)
    # In production, this could be stored in Redis or a separate metrics DB
    _metrics = {
        'hits': 0,
        'misses': 0,
        'total_requests': 0,
        'cache_time_saved': 0.0,  # milliseconds
        'endpoints': {},  # endpoint -> {hits, misses, avg_time_cached, avg_time_uncached}
        'cache_keys_accessed': set(),
        'memory_samples': [],
    }
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.enabled = getattr(settings, 'CACHE_MONITORING_ENABLED', True)
        self.process = psutil.Process(os.getpid())
    
    def process_request(self, request):
        """Store request start time and memory usage"""
        if not self.enabled:
            return None
        
        request._cache_monitor_start = time.time()
        request._cache_monitor_mem_start = self.process.memory_info().rss / 1024 / 1024  # MB
        request._cache_hit = False
        request._cache_keys_used = []
        
        return None
    
    def process_response(self, request, response):
        """Calculate and store cache performance metrics"""
        if not self.enabled:
            return response
        
        # Skip if request doesn't have monitoring attributes
        if not hasattr(request, '_cache_monitor_start'):
            return response
        
        elapsed_time = (time.time() - request._cache_monitor_start) * 1000  # ms
        mem_end = self.process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_end - request._cache_monitor_mem_start
        
        # Get endpoint path
        endpoint = request.path
        
        # Detect cache hit/miss by checking response attributes or headers
        cache_hit = getattr(request, '_cache_hit', False)
        cache_keys = getattr(request, '_cache_keys_used', [])
        
        # Update global metrics
        self._metrics['total_requests'] += 1
        if cache_hit:
            self._metrics['hits'] += 1
        else:
            self._metrics['misses'] += 1
        
        # Update endpoint-specific metrics
        if endpoint not in self._metrics['endpoints']:
            self._metrics['endpoints'][endpoint] = {
                'hits': 0,
                'misses': 0,
                'total_time_cached': 0.0,
                'total_time_uncached': 0.0,
                'count_cached': 0,
                'count_uncached': 0,
                'memory_used': [],
            }
        
        endpoint_metrics = self._metrics['endpoints'][endpoint]
        if cache_hit:
            endpoint_metrics['hits'] += 1
            endpoint_metrics['total_time_cached'] += elapsed_time
            endpoint_metrics['count_cached'] += 1
        else:
            endpoint_metrics['misses'] += 1
            endpoint_metrics['total_time_uncached'] += elapsed_time
            endpoint_metrics['count_uncached'] += 1
        
        endpoint_metrics['memory_used'].append(mem_used)
        
        # Track cache keys accessed
        for key in cache_keys:
            self._metrics['cache_keys_accessed'].add(key)
        
        # Store memory sample (keep last 1000)
        self._metrics['memory_samples'].append({
            'timestamp': time.time(),
            'memory_mb': mem_end,
            'endpoint': endpoint,
            'cache_hit': cache_hit,
        })
        if len(self._metrics['memory_samples']) > 1000:
            self._metrics['memory_samples'] = self._metrics['memory_samples'][-1000:]
        
        # Log detailed metrics for debugging (configurable)
        if settings.DEBUG and logger.isEnabledFor(logging.DEBUG):
            hit_rate = (self._metrics['hits'] / self._metrics['total_requests'] * 100) if self._metrics['total_requests'] > 0 else 0
            logger.debug(
                f"Cache Monitor: {endpoint} | "
                f"Hit: {cache_hit} | "
                f"Time: {elapsed_time:.2f}ms | "
                f"Mem: {mem_used:.2f}MB | "
                f"Overall Hit Rate: {hit_rate:.1f}%"
            )
        
        return response
    
    @classmethod
    def get_metrics(cls):
        """Get current cache monitoring metrics"""
        metrics = cls._metrics.copy()
        
        # Calculate derived metrics
        total = metrics['total_requests']
        if total > 0:
            metrics['hit_rate'] = (metrics['hits'] / total) * 100
            metrics['miss_rate'] = (metrics['misses'] / total) * 100
        else:
            metrics['hit_rate'] = 0
            metrics['miss_rate'] = 0
        
        # Calculate endpoint averages
        for endpoint, data in metrics['endpoints'].items():
            if data['count_cached'] > 0:
                data['avg_time_cached'] = data['total_time_cached'] / data['count_cached']
            else:
                data['avg_time_cached'] = 0
            
            if data['count_uncached'] > 0:
                data['avg_time_uncached'] = data['total_time_uncached'] / data['count_uncached']
            else:
                data['avg_time_uncached'] = 0
            
            # Calculate time saved
            if data['count_cached'] > 0 and data['avg_time_uncached'] > 0:
                data['time_saved_per_hit'] = data['avg_time_uncached'] - data['avg_time_cached']
                data['total_time_saved'] = data['time_saved_per_hit'] * data['count_cached']
            else:
                data['time_saved_per_hit'] = 0
                data['total_time_saved'] = 0
            
            # Calculate average memory
            if data['memory_used']:
                data['avg_memory_mb'] = sum(data['memory_used']) / len(data['memory_used'])
            else:
                data['avg_memory_mb'] = 0
        
        # Convert set to list for JSON serialization
        metrics['cache_keys_accessed'] = list(metrics['cache_keys_accessed'])
        metrics['total_cache_keys'] = len(metrics['cache_keys_accessed'])
        
        return metrics
    
    @classmethod
    def reset_metrics(cls):
        """Reset all metrics (useful for testing or periodic resets)"""
        cls._metrics = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'cache_time_saved': 0.0,
            'endpoints': {},
            'cache_keys_accessed': set(),
            'memory_samples': [],
        }
        logger.info("Cache monitoring metrics reset")
    
    @classmethod
    def mark_cache_hit(cls, request, cache_key):
        """Mark a request as a cache hit (call this from views when cache is used)"""
        if hasattr(request, '_cache_hit'):
            request._cache_hit = True
        if hasattr(request, '_cache_keys_used'):
            request._cache_keys_used.append(cache_key)
    
    @classmethod
    def mark_cache_miss(cls, request, cache_key):
        """Mark a request as a cache miss (call this from views when cache is not used)"""
        if hasattr(request, '_cache_hit'):
            request._cache_hit = False
        if hasattr(request, '_cache_keys_used'):
            request._cache_keys_used.append(cache_key)

