"""
Cache Statistics API Endpoints

Provides real-time cache performance metrics, memory usage, and effectiveness analysis.
"""
import time
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from core.middleware.cache_monitor import CacheMonitorMiddleware
from core.models import CacheMetrics
import psutil
import os


class CacheStatsView(APIView):
    """Get real-time cache hit/miss rates and statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return current cache statistics"""
        metrics = CacheMonitorMiddleware.get_metrics()
        
        return Response({
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'cache_backend': settings.CACHES['default']['BACKEND'],
            'monitoring_enabled': settings.CACHE_MONITORING_ENABLED,
            'statistics': {
                'total_requests': metrics['total_requests'],
                'cache_hits': metrics['hits'],
                'cache_misses': metrics['misses'],
                'hit_rate': round(metrics['hit_rate'], 2),
                'miss_rate': round(metrics['miss_rate'], 2),
            },
            'endpoints': self._format_endpoint_stats(metrics['endpoints']),
            'cache_info': {
                'total_keys': metrics['total_cache_keys'],
                'sample_keys': metrics['cache_keys_accessed'][:20],  # Show first 20 keys
            }
        })
    
    def _format_endpoint_stats(self, endpoints):
        """Format endpoint statistics for response"""
        formatted = []
        for endpoint, data in endpoints.items():
            formatted.append({
                'endpoint': endpoint,
                'hits': data['hits'],
                'misses': data['misses'],
                'hit_rate': round((data['hits'] / (data['hits'] + data['misses']) * 100) if (data['hits'] + data['misses']) > 0 else 0, 2),
                'avg_time_cached_ms': round(data.get('avg_time_cached', 0), 2),
                'avg_time_uncached_ms': round(data.get('avg_time_uncached', 0), 2),
                'time_saved_ms': round(data.get('total_time_saved', 0), 2),
                'avg_memory_mb': round(data.get('avg_memory_mb', 0), 2),
            })
        
        # Sort by total requests (hits + misses)
        formatted.sort(key=lambda x: x['hits'] + x['misses'], reverse=True)
        return formatted


class CacheMemoryView(APIView):
    """Get memory usage breakdown for cache"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return memory usage statistics"""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        metrics = CacheMonitorMiddleware.get_metrics()
        memory_samples = metrics.get('memory_samples', [])
        
        # Calculate memory statistics
        if memory_samples:
            recent_samples = memory_samples[-100:]  # Last 100 samples
            avg_memory = sum(s['memory_mb'] for s in recent_samples) / len(recent_samples)
            max_memory = max(s['memory_mb'] for s in recent_samples)
            min_memory = min(s['memory_mb'] for s in recent_samples)
        else:
            avg_memory = mem_info.rss / 1024 / 1024
            max_memory = avg_memory
            min_memory = avg_memory
        
        # Try to get cache-specific memory info (Redis)
        cache_memory = None
        if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
            try:
                redis_client = cache.client.get_client()
                info = redis_client.info('memory')
                cache_memory = {
                    'used_memory_mb': info.get('used_memory', 0) / 1024 / 1024,
                    'used_memory_peak_mb': info.get('used_memory_peak', 0) / 1024 / 1024,
                    'total_system_memory_mb': info.get('total_system_memory', 0) / 1024 / 1024,
                    'maxmemory_mb': info.get('maxmemory', 0) / 1024 / 1024,
                }
            except:
                pass
        
        return Response({
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'process_memory': {
                'rss_mb': round(mem_info.rss / 1024 / 1024, 2),
                'vms_mb': round(mem_info.vms / 1024 / 1024, 2),
                'percent': round(process.memory_percent(), 2),
            },
            'cache_memory': cache_memory,
            'statistics': {
                'avg_memory_mb': round(avg_memory, 2),
                'max_memory_mb': round(max_memory, 2),
                'min_memory_mb': round(min_memory, 2),
                'samples_count': len(memory_samples),
            },
            'system': {
                'total_memory_mb': round(psutil.virtual_memory().total / 1024 / 1024, 2),
                'available_memory_mb': round(psutil.virtual_memory().available / 1024 / 1024, 2),
                'used_percent': psutil.virtual_memory().percent,
            }
        })


class CacheKeysView(APIView):
    """Get active cache keys and their details"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return information about active cache keys"""
        metrics = CacheMonitorMiddleware.get_metrics()
        
        # Try to get detailed key info from Redis
        key_details = []
        if hasattr(cache, 'client') and hasattr(cache.client, 'get_client'):
            try:
                redis_client = cache.client.get_client()
                key_prefix = settings.CACHES['default'].get('KEY_PREFIX', 'engagehub')
                
                # Get all keys matching our prefix
                pattern = f"{key_prefix}:*"
                keys = redis_client.keys(pattern)
                
                for key in keys[:100]:  # Limit to first 100 keys
                    try:
                        ttl = redis_client.ttl(key)
                        memory = redis_client.memory_usage(key) if hasattr(redis_client, 'memory_usage') else None
                        
                        key_details.append({
                            'key': key.decode('utf-8') if isinstance(key, bytes) else key,
                            'ttl_seconds': ttl,
                            'memory_bytes': memory,
                        })
                    except:
                        continue
            except:
                pass
        
        return Response({
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'total_keys': metrics['total_cache_keys'],
            'keys_accessed': metrics['cache_keys_accessed'][:50],  # First 50 accessed keys
            'key_details': key_details[:50],  # First 50 with details
        })


class CachePerformanceView(APIView):
    """Get performance comparison between cached and uncached requests"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return performance comparison metrics"""
        metrics = CacheMonitorMiddleware.get_metrics()
        
        # Calculate overall performance improvements
        total_time_saved = 0
        total_cached_time = 0
        total_uncached_time = 0
        
        for endpoint, data in metrics['endpoints'].items():
            total_time_saved += data.get('total_time_saved', 0)
            total_cached_time += data.get('total_time_cached', 0)
            total_uncached_time += data.get('total_time_uncached', 0)
        
        # Calculate average improvement
        if total_uncached_time > 0 and total_cached_time > 0:
            improvement_percent = ((total_uncached_time - total_cached_time) / total_uncached_time) * 100
        else:
            improvement_percent = 0
        
        # Get top performing endpoints
        top_performers = []
        for endpoint, data in metrics['endpoints'].items():
            if data.get('count_cached', 0) > 0:
                top_performers.append({
                    'endpoint': endpoint,
                    'time_saved_ms': round(data.get('total_time_saved', 0), 2),
                    'avg_cached_ms': round(data.get('avg_time_cached', 0), 2),
                    'avg_uncached_ms': round(data.get('avg_time_uncached', 0), 2),
                    'improvement_percent': round(
                        ((data.get('avg_time_uncached', 0) - data.get('avg_time_cached', 0)) / data.get('avg_time_uncached', 1)) * 100,
                        2
                    ) if data.get('avg_time_uncached', 0) > 0 else 0,
                    'cached_requests': data.get('count_cached', 0),
                })
        
        top_performers.sort(key=lambda x: x['time_saved_ms'], reverse=True)
        
        return Response({
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'overall': {
                'total_time_saved_ms': round(total_time_saved, 2),
                'total_time_saved_seconds': round(total_time_saved / 1000, 2),
                'improvement_percent': round(improvement_percent, 2),
                'avg_cached_time_ms': round(total_cached_time / max(metrics['hits'], 1), 2),
                'avg_uncached_time_ms': round(total_uncached_time / max(metrics['misses'], 1), 2),
            },
            'top_performers': top_performers[:10],  # Top 10 endpoints
        })


class CacheResetView(APIView):
    """Reset cache monitoring metrics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Reset all cache monitoring metrics"""
        if not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Admin permissions required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Save current metrics to database before resetting
        metrics = CacheMonitorMiddleware.get_metrics()
        
        CacheMetrics.objects.create(
            total_requests=metrics['total_requests'],
            cache_hits=metrics['hits'],
            cache_misses=metrics['misses'],
            hit_rate=metrics['hit_rate'],
            avg_response_time_cached=sum(
                e.get('avg_time_cached', 0) for e in metrics['endpoints'].values()
            ) / max(len(metrics['endpoints']), 1),
            avg_response_time_uncached=sum(
                e.get('avg_time_uncached', 0) for e in metrics['endpoints'].values()
            ) / max(len(metrics['endpoints']), 1),
            time_saved_total=sum(
                e.get('total_time_saved', 0) for e in metrics['endpoints'].values()
            ),
            cache_size_keys=metrics['total_cache_keys'],
            endpoint_stats=metrics['endpoints'],
            cache_backend=settings.CACHES['default']['BACKEND'],
        )
        
        # Reset metrics
        CacheMonitorMiddleware.reset_metrics()
        
        return Response({
            'success': True,
            'message': 'Cache monitoring metrics have been reset and saved to database'
        })


class CacheHistoryView(APIView):
    """Get historical cache metrics from database"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Return historical cache metrics"""
        # Get time range from query params
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        metrics = CacheMetrics.objects.filter(timestamp__gte=start_date).order_by('-timestamp')
        
        history = []
        for metric in metrics:
            history.append({
                'timestamp': metric.timestamp.isoformat(),
                'total_requests': metric.total_requests,
                'hit_rate': metric.hit_rate,
                'cache_hits': metric.cache_hits,
                'cache_misses': metric.cache_misses,
                'time_saved_ms': metric.time_saved_total,
                'efficiency_score': metric.efficiency_score,
                'cache_size_keys': metric.cache_size_keys,
            })
        
        return Response({
            'success': True,
            'period_days': days,
            'count': len(history),
            'history': history,
        })

