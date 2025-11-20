"""
Memory Profiling Utilities for Cache Operations

Tracks memory usage before/after cache operations, identifies memory-heavy cache keys,
detects memory leaks, and provides cache efficiency metrics.
"""
import time
import sys
import logging
from typing import Dict, List, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
import psutil
import os

logger = logging.getLogger(__name__)


class CacheMemoryProfiler:
    """
    Profile memory usage for cache operations and provide detailed analysis
    """
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.profiles = []
        self.key_sizes = {}
        self._baseline_memory = None
    
    def get_current_memory(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        mem_info = self.process.memory_info()
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': self.process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024,
        }
    
    def set_baseline(self):
        """Set baseline memory for comparison"""
        self._baseline_memory = self.get_current_memory()
        logger.info(f"Memory baseline set: {self._baseline_memory['rss_mb']:.2f} MB")
    
    def get_memory_delta(self) -> Optional[Dict[str, float]]:
        """Get memory change since baseline"""
        if self._baseline_memory is None:
            return None
        
        current = self.get_current_memory()
        return {
            'rss_delta_mb': current['rss_mb'] - self._baseline_memory['rss_mb'],
            'vms_delta_mb': current['vms_mb'] - self._baseline_memory['vms_mb'],
            'percent_delta': current['percent'] - self._baseline_memory['percent'],
        }
    
    def profile_cache_operation(self, operation: str, key: str, value=None) -> Dict:
        """
        Profile a cache operation and track memory usage
        
        Args:
            operation: Type of operation ('set', 'get', 'delete')
            key: Cache key
            value: Value being cached (for 'set' operations)
        
        Returns:
            Dictionary with profiling results
        """
        mem_before = self.get_current_memory()
        start_time = time.time()
        
        # Perform operation
        result = None
        if operation == 'set':
            cache.set(key, value, 3600)
            result = True
        elif operation == 'get':
            result = cache.get(key)
        elif operation == 'delete':
            result = cache.delete(key)
        
        elapsed_ms = (time.time() - start_time) * 1000
        mem_after = self.get_current_memory()
        
        # Calculate value size (approximate)
        value_size_bytes = 0
        if value is not None:
            try:
                value_size_bytes = sys.getsizeof(value)
            except:
                pass
        
        profile = {
            'operation': operation,
            'key': key,
            'timestamp': time.time(),
            'elapsed_ms': elapsed_ms,
            'value_size_bytes': value_size_bytes,
            'value_size_kb': value_size_bytes / 1024,
            'mem_before_mb': mem_before['rss_mb'],
            'mem_after_mb': mem_after['rss_mb'],
            'mem_delta_mb': mem_after['rss_mb'] - mem_before['rss_mb'],
            'success': result is not None if operation == 'get' else result,
        }
        
        self.profiles.append(profile)
        
        # Track key sizes
        if operation == 'set':
            self.key_sizes[key] = value_size_bytes
        
        return profile
    
    def get_heavy_keys(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Get the heaviest cache keys by size
        
        Args:
            top_n: Number of top keys to return
        
        Returns:
            List of (key, size_bytes) tuples
        """
        sorted_keys = sorted(
            self.key_sizes.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_keys[:top_n]
    
    def get_efficiency_metrics(self) -> Dict:
        """
        Calculate cache efficiency metrics
        
        Returns:
            Dictionary with efficiency metrics
        """
        if not self.profiles:
            return {
                'total_operations': 0,
                'avg_time_ms': 0,
                'total_memory_impact_mb': 0,
            }
        
        total_time = sum(p['elapsed_ms'] for p in self.profiles)
        total_memory = sum(p['mem_delta_mb'] for p in self.profiles)
        
        # Calculate per-operation statistics
        ops_by_type = {}
        for profile in self.profiles:
            op_type = profile['operation']
            if op_type not in ops_by_type:
                ops_by_type[op_type] = []
            ops_by_type[op_type].append(profile)
        
        op_stats = {}
        for op_type, profiles in ops_by_type.items():
            op_stats[op_type] = {
                'count': len(profiles),
                'avg_time_ms': sum(p['elapsed_ms'] for p in profiles) / len(profiles),
                'avg_memory_delta_mb': sum(p['mem_delta_mb'] for p in profiles) / len(profiles),
                'total_memory_delta_mb': sum(p['mem_delta_mb'] for p in profiles),
            }
        
        return {
            'total_operations': len(self.profiles),
            'avg_time_ms': total_time / len(self.profiles),
            'total_memory_impact_mb': total_memory,
            'operations_by_type': op_stats,
        }
    
    def detect_memory_leaks(self, threshold_mb: float = 10.0) -> Dict:
        """
        Detect potential memory leaks in cache operations
        
        Args:
            threshold_mb: Memory growth threshold to flag as potential leak
        
        Returns:
            Dictionary with leak detection results
        """
        if len(self.profiles) < 10:
            return {
                'leak_detected': False,
                'reason': 'Insufficient data for leak detection (need at least 10 operations)',
            }
        
        # Check memory growth trend
        recent_profiles = self.profiles[-20:]  # Last 20 operations
        memory_growth = recent_profiles[-1]['mem_after_mb'] - recent_profiles[0]['mem_before_mb']
        
        # Check for operations with unusually high memory delta
        high_memory_ops = [
            p for p in self.profiles
            if p['mem_delta_mb'] > threshold_mb
        ]
        
        leak_detected = memory_growth > threshold_mb or len(high_memory_ops) > 0
        
        return {
            'leak_detected': leak_detected,
            'memory_growth_mb': memory_growth,
            'high_memory_operations': len(high_memory_ops),
            'threshold_mb': threshold_mb,
            'details': high_memory_ops[:5] if high_memory_ops else [],
        }
    
    def get_cache_cost_analysis(self, db_query_time_ms: float = 100.0) -> Dict:
        """
        Analyze the cost-benefit of caching
        
        Args:
            db_query_time_ms: Average database query time to compare against
        
        Returns:
            Dictionary with cost analysis
        """
        if not self.profiles:
            return {'error': 'No profiles available'}
        
        # Filter get operations
        get_ops = [p for p in self.profiles if p['operation'] == 'get']
        set_ops = [p for p in self.profiles if p['operation'] == 'set']
        
        if not get_ops:
            return {'error': 'No cache get operations recorded'}
        
        avg_get_time = sum(p['elapsed_ms'] for p in get_ops) / len(get_ops)
        time_saved_per_hit = db_query_time_ms - avg_get_time
        
        # Calculate memory cost per saved millisecond
        total_memory_used = sum(self.key_sizes.values()) / 1024 / 1024  # MB
        total_time_saved = time_saved_per_hit * len(get_ops)
        
        memory_cost_per_ms = total_memory_used / total_time_saved if total_time_saved > 0 else 0
        
        return {
            'cache_get_operations': len(get_ops),
            'cache_set_operations': len(set_ops),
            'avg_cache_get_time_ms': round(avg_get_time, 2),
            'assumed_db_query_time_ms': db_query_time_ms,
            'time_saved_per_hit_ms': round(time_saved_per_hit, 2),
            'total_time_saved_ms': round(total_time_saved, 2),
            'total_memory_used_mb': round(total_memory_used, 2),
            'memory_cost_per_ms_saved': round(memory_cost_per_ms, 4),
            'efficiency_score': self._calculate_efficiency_score(
                time_saved_per_hit, memory_cost_per_ms
            ),
        }
    
    def _calculate_efficiency_score(self, time_saved_ms: float, memory_cost_per_ms: float) -> float:
        """
        Calculate an efficiency score (0-100) based on time saved vs memory cost
        
        Higher score = better efficiency
        """
        if time_saved_ms <= 0:
            return 0.0
        
        # Normalize: Higher time saved is better, lower memory cost is better
        time_score = min(100, (time_saved_ms / 10) * 100)  # 10ms+ saves = 100
        memory_score = max(0, 100 - (memory_cost_per_ms * 1000))  # Lower is better
        
        # Weighted average: 60% time savings, 40% memory efficiency
        efficiency = (time_score * 0.6) + (memory_score * 0.4)
        
        return round(efficiency, 2)
    
    def generate_report(self) -> str:
        """Generate a comprehensive memory profiling report"""
        report = []
        report.append("=" * 80)
        report.append("CACHE MEMORY PROFILING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Current memory status
        current_mem = self.get_current_memory()
        report.append(f"Current Memory Usage:")
        report.append(f"  RSS: {current_mem['rss_mb']:.2f} MB")
        report.append(f"  VMS: {current_mem['vms_mb']:.2f} MB")
        report.append(f"  Process: {current_mem['percent']:.2f}%")
        report.append(f"  Available: {current_mem['available_mb']:.2f} MB")
        report.append("")
        
        # Baseline comparison
        if self._baseline_memory:
            delta = self.get_memory_delta()
            report.append(f"Memory Change Since Baseline:")
            report.append(f"  RSS Delta: {delta['rss_delta_mb']:+.2f} MB")
            report.append(f"  VMS Delta: {delta['vms_delta_mb']:+.2f} MB")
            report.append("")
        
        # Efficiency metrics
        metrics = self.get_efficiency_metrics()
        report.append(f"Efficiency Metrics:")
        report.append(f"  Total Operations: {metrics['total_operations']}")
        report.append(f"  Average Time: {metrics['avg_time_ms']:.2f} ms")
        report.append(f"  Total Memory Impact: {metrics['total_memory_impact_mb']:+.2f} MB")
        report.append("")
        
        if 'operations_by_type' in metrics:
            report.append(f"Operations by Type:")
            for op_type, stats in metrics['operations_by_type'].items():
                report.append(f"  {op_type.upper()}:")
                report.append(f"    Count: {stats['count']}")
                report.append(f"    Avg Time: {stats['avg_time_ms']:.2f} ms")
                report.append(f"    Avg Memory Delta: {stats['avg_memory_delta_mb']:+.4f} MB")
            report.append("")
        
        # Heavy keys
        heavy_keys = self.get_heavy_keys(5)
        if heavy_keys:
            report.append(f"Top 5 Heaviest Cache Keys:")
            for key, size in heavy_keys:
                report.append(f"  {key}: {size / 1024:.2f} KB")
            report.append("")
        
        # Memory leak detection
        leak_analysis = self.detect_memory_leaks()
        report.append(f"Memory Leak Detection:")
        if leak_analysis['leak_detected']:
            report.append(f"  ⚠️  Potential leak detected!")
            report.append(f"  Memory Growth: {leak_analysis['memory_growth_mb']:.2f} MB")
            report.append(f"  High Memory Operations: {leak_analysis['high_memory_operations']}")
        else:
            report.append(f"  ✓ No leaks detected")
        report.append("")
        
        # Cost analysis
        cost_analysis = self.get_cache_cost_analysis()
        if 'error' not in cost_analysis:
            report.append(f"Cost-Benefit Analysis:")
            report.append(f"  Time Saved per Hit: {cost_analysis['time_saved_per_hit_ms']:.2f} ms")
            report.append(f"  Total Time Saved: {cost_analysis['total_time_saved_ms']:.2f} ms")
            report.append(f"  Total Memory Used: {cost_analysis['total_memory_used_mb']:.2f} MB")
            report.append(f"  Memory Cost per ms Saved: {cost_analysis['memory_cost_per_ms_saved']:.4f} MB/ms")
            report.append(f"  Efficiency Score: {cost_analysis['efficiency_score']}/100")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def reset(self):
        """Reset all profiling data"""
        self.profiles = []
        self.key_sizes = {}
        self._baseline_memory = None
        logger.info("Memory profiler reset")

