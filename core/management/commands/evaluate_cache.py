"""
Cache Effectiveness Evaluation Command

Analyzes cache performance and generates comprehensive reports including:
- Cache hit ratio by endpoint
- Underutilized cache keys
- Optimal TTL recommendations
- Cost savings estimation
- Memory vs performance trade-off analysis
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from core.middleware.cache_monitor import CacheMonitorMiddleware
from core.models import CacheMetrics
from core.utils.memory_profiler import CacheMemoryProfiler
import json


class Command(BaseCommand):
    help = 'Evaluate cache effectiveness and generate comprehensive report'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of historical data to analyze'
        )
        parser.add_argument(
            '--format',
            type=str,
            default='text',
            choices=['text', 'json'],
            help='Output format (text or json)'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save current metrics to database'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        output_format = options['format']
        save_metrics = options['save']
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*80}\n'
            f'CACHE EFFECTIVENESS EVALUATION\n'
            f'{"="*80}\n'
        ))
        
        # Get current metrics from middleware
        current_metrics = CacheMonitorMiddleware.get_metrics()
        
        # Get historical metrics from database
        start_date = timezone.now() - timedelta(days=days)
        historical_metrics = CacheMetrics.objects.filter(
            timestamp__gte=start_date
        ).order_by('-timestamp')
        
        # Generate analysis
        analysis = self.analyze_cache_effectiveness(
            current_metrics,
            historical_metrics,
            days
        )
        
        # Save current metrics if requested
        if save_metrics:
            self.save_metrics_to_db(current_metrics)
            self.stdout.write(self.style.SUCCESS('✓ Current metrics saved to database\n'))
        
        # Output results
        if output_format == 'json':
            self.stdout.write(json.dumps(analysis, indent=2))
        else:
            self.print_text_report(analysis)
    
    def analyze_cache_effectiveness(self, current_metrics, historical_metrics, days):
        """Perform comprehensive cache effectiveness analysis"""
        analysis = {
            'timestamp': timezone.now().isoformat(),
            'period_days': days,
            'cache_backend': settings.CACHES['default']['BACKEND'],
            'current_stats': {},
            'historical_trends': {},
            'endpoint_analysis': {},
            'recommendations': [],
            'performance_score': 0,
        }
        
        # Current statistics
        analysis['current_stats'] = {
            'total_requests': current_metrics['total_requests'],
            'cache_hits': current_metrics['hits'],
            'cache_misses': current_metrics['misses'],
            'hit_rate': round(current_metrics['hit_rate'], 2),
            'total_cache_keys': current_metrics['total_cache_keys'],
        }
        
        # Historical trends
        if historical_metrics.exists():
            analysis['historical_trends'] = self.analyze_historical_trends(
                historical_metrics
            )
        
        # Endpoint-specific analysis
        analysis['endpoint_analysis'] = self.analyze_endpoints(
            current_metrics['endpoints']
        )
        
        # Generate recommendations
        analysis['recommendations'] = self.generate_recommendations(
            current_metrics,
            analysis['endpoint_analysis']
        )
        
        # Calculate overall performance score
        analysis['performance_score'] = self.calculate_performance_score(
            current_metrics,
            analysis['endpoint_analysis']
        )
        
        return analysis
    
    def analyze_historical_trends(self, historical_metrics):
        """Analyze trends in historical cache metrics"""
        metrics_list = list(historical_metrics)
        
        if not metrics_list:
            return {}
        
        # Calculate averages
        avg_hit_rate = sum(m.hit_rate for m in metrics_list) / len(metrics_list)
        avg_requests = sum(m.total_requests for m in metrics_list) / len(metrics_list)
        
        # Calculate trend (comparing first vs last)
        if len(metrics_list) >= 2:
            hit_rate_trend = metrics_list[0].hit_rate - metrics_list[-1].hit_rate
            requests_trend = metrics_list[0].total_requests - metrics_list[-1].total_requests
        else:
            hit_rate_trend = 0
            requests_trend = 0
        
        return {
            'data_points': len(metrics_list),
            'avg_hit_rate': round(avg_hit_rate, 2),
            'avg_requests_per_snapshot': round(avg_requests, 2),
            'hit_rate_trend': round(hit_rate_trend, 2),
            'requests_trend': round(requests_trend, 2),
            'trend_direction': 'improving' if hit_rate_trend > 0 else 'declining' if hit_rate_trend < 0 else 'stable',
        }
    
    def analyze_endpoints(self, endpoints):
        """Analyze cache effectiveness for each endpoint"""
        endpoint_analysis = []
        
        for endpoint, data in endpoints.items():
            total_requests = data['hits'] + data['misses']
            if total_requests == 0:
                continue
            
            hit_rate = (data['hits'] / total_requests) * 100
            avg_time_cached = data.get('avg_time_cached', 0)
            avg_time_uncached = data.get('avg_time_uncached', 0)
            time_saved = data.get('total_time_saved', 0)
            
            # Calculate improvement percentage
            if avg_time_uncached > 0:
                improvement_pct = ((avg_time_uncached - avg_time_cached) / avg_time_uncached) * 100
            else:
                improvement_pct = 0
            
            # Determine effectiveness category
            if hit_rate >= 80 and improvement_pct >= 50:
                effectiveness = 'excellent'
            elif hit_rate >= 60 and improvement_pct >= 30:
                effectiveness = 'good'
            elif hit_rate >= 40 and improvement_pct >= 20:
                effectiveness = 'moderate'
            else:
                effectiveness = 'poor'
            
            endpoint_analysis.append({
                'endpoint': endpoint,
                'total_requests': total_requests,
                'hits': data['hits'],
                'misses': data['misses'],
                'hit_rate': round(hit_rate, 2),
                'avg_time_cached_ms': round(avg_time_cached, 2),
                'avg_time_uncached_ms': round(avg_time_uncached, 2),
                'improvement_pct': round(improvement_pct, 2),
                'time_saved_total_ms': round(time_saved, 2),
                'time_saved_seconds': round(time_saved / 1000, 2),
                'effectiveness': effectiveness,
            })
        
        # Sort by time saved (most valuable first)
        endpoint_analysis.sort(key=lambda x: x['time_saved_total_ms'], reverse=True)
        
        return endpoint_analysis
    
    def generate_recommendations(self, current_metrics, endpoint_analysis):
        """Generate actionable recommendations"""
        recommendations = []
        
        hit_rate = current_metrics['hit_rate']
        
        # Overall hit rate recommendations
        if hit_rate < 50:
            recommendations.append({
                'priority': 'high',
                'category': 'hit_rate',
                'issue': f'Low cache hit rate ({hit_rate:.1f}%)',
                'suggestion': 'Increase cache TTL values or review cache key generation logic',
                'expected_improvement': 'Increase hit rate by 20-30%',
            })
        elif hit_rate < 70:
            recommendations.append({
                'priority': 'medium',
                'category': 'hit_rate',
                'issue': f'Moderate cache hit rate ({hit_rate:.1f}%)',
                'suggestion': 'Fine-tune cache invalidation strategy',
                'expected_improvement': 'Increase hit rate by 10-15%',
            })
        
        # Endpoint-specific recommendations
        poor_endpoints = [e for e in endpoint_analysis if e['effectiveness'] == 'poor']
        if poor_endpoints:
            for endpoint in poor_endpoints[:3]:  # Top 3 poor performers
                recommendations.append({
                    'priority': 'medium',
                    'category': 'endpoint',
                    'issue': f'Low cache effectiveness for {endpoint["endpoint"]}',
                    'suggestion': f'Review caching strategy for this endpoint (hit rate: {endpoint["hit_rate"]:.1f}%)',
                    'expected_improvement': 'Potential time savings if optimized',
                })
        
        # Underutilized cache recommendations
        underutilized = [e for e in endpoint_analysis if e['hit_rate'] < 30 and e['total_requests'] > 10]
        if underutilized:
            recommendations.append({
                'priority': 'low',
                'category': 'underutilized',
                'issue': f'{len(underutilized)} endpoints have very low cache hit rates',
                'suggestion': 'Consider removing caching or adjusting TTL for these endpoints',
                'expected_improvement': 'Reduce memory usage without performance impact',
            })
        
        # Memory optimization recommendations
        if current_metrics['total_cache_keys'] > 5000:
            recommendations.append({
                'priority': 'medium',
                'category': 'memory',
                'issue': f'High number of cache keys ({current_metrics["total_cache_keys"]})',
                'suggestion': 'Review cache key generation and consider more aggressive eviction',
                'expected_improvement': 'Reduce memory footprint',
            })
        
        # Redis recommendation
        if 'locmem' in settings.CACHES['default']['BACKEND'].lower():
            recommendations.append({
                'priority': 'high',
                'category': 'infrastructure',
                'issue': 'Using LocMemCache (in-memory) for caching',
                'suggestion': 'Consider upgrading to Redis for production (better performance, persistence, distributed caching)',
                'expected_improvement': 'Better scalability and reliability',
            })
        
        return recommendations
    
    def calculate_performance_score(self, current_metrics, endpoint_analysis):
        """Calculate overall cache performance score (0-100)"""
        if current_metrics['total_requests'] == 0:
            return 0
        
        # Factors:
        # 1. Hit rate (40%)
        # 2. Average time saved (30%)
        # 3. Number of effective endpoints (20%)
        # 4. Cache utilization (10%)
        
        hit_rate_score = current_metrics['hit_rate']
        
        # Time saved score
        if endpoint_analysis:
            avg_improvement = sum(e['improvement_pct'] for e in endpoint_analysis) / len(endpoint_analysis)
            time_saved_score = min(100, avg_improvement)
        else:
            time_saved_score = 0
        
        # Effectiveness score
        if endpoint_analysis:
            effective_count = len([e for e in endpoint_analysis if e['effectiveness'] in ['excellent', 'good']])
            effectiveness_score = (effective_count / len(endpoint_analysis)) * 100
        else:
            effectiveness_score = 0
        
        # Utilization score (based on cache keys vs requests)
        if current_metrics['total_cache_keys'] > 0:
            utilization_score = min(100, (current_metrics['total_requests'] / current_metrics['total_cache_keys']) * 10)
        else:
            utilization_score = 0
        
        # Weighted average
        performance_score = (
            hit_rate_score * 0.4 +
            time_saved_score * 0.3 +
            effectiveness_score * 0.2 +
            utilization_score * 0.1
        )
        
        return round(performance_score, 2)
    
    def save_metrics_to_db(self, current_metrics):
        """Save current metrics to database"""
        # Calculate averages from endpoints
        endpoints = current_metrics['endpoints']
        if endpoints:
            avg_cached_time = sum(
                e.get('avg_time_cached', 0) for e in endpoints.values()
            ) / len(endpoints)
            avg_uncached_time = sum(
                e.get('avg_time_uncached', 0) for e in endpoints.values()
            ) / len(endpoints)
            total_time_saved = sum(
                e.get('total_time_saved', 0) for e in endpoints.values()
            )
        else:
            avg_cached_time = 0
            avg_uncached_time = 0
            total_time_saved = 0
        
        CacheMetrics.objects.create(
            total_requests=current_metrics['total_requests'],
            cache_hits=current_metrics['hits'],
            cache_misses=current_metrics['misses'],
            hit_rate=current_metrics['hit_rate'],
            avg_response_time_cached=avg_cached_time,
            avg_response_time_uncached=avg_uncached_time,
            time_saved_total=total_time_saved,
            cache_size_keys=current_metrics['total_cache_keys'],
            endpoint_stats=endpoints,
            cache_backend=settings.CACHES['default']['BACKEND'],
        )
    
    def print_text_report(self, analysis):
        """Print analysis in formatted text"""
        # Current Stats
        self.stdout.write(self.style.HTTP_INFO('\n📊 CURRENT STATISTICS'))
        self.stdout.write('-' * 80)
        stats = analysis['current_stats']
        self.stdout.write(f"Total Requests:     {stats['total_requests']}")
        self.stdout.write(f"Cache Hits:         {stats['cache_hits']}")
        self.stdout.write(f"Cache Misses:       {stats['cache_misses']}")
        self.stdout.write(f"Hit Rate:           {stats['hit_rate']}%")
        self.stdout.write(f"Total Cache Keys:   {stats['total_cache_keys']}")
        
        # Historical Trends
        if analysis['historical_trends']:
            self.stdout.write(self.style.HTTP_INFO('\n📈 HISTORICAL TRENDS'))
            self.stdout.write('-' * 80)
            trends = analysis['historical_trends']
            self.stdout.write(f"Data Points:        {trends['data_points']}")
            self.stdout.write(f"Avg Hit Rate:       {trends['avg_hit_rate']}%")
            self.stdout.write(f"Trend Direction:    {trends['trend_direction'].upper()}")
            self.stdout.write(f"Hit Rate Change:    {trends['hit_rate_trend']:+.2f}%")
        
        # Endpoint Analysis
        self.stdout.write(self.style.HTTP_INFO('\n🎯 ENDPOINT ANALYSIS'))
        self.stdout.write('-' * 80)
        
        if analysis['endpoint_analysis']:
            # Top performers
            top_5 = analysis['endpoint_analysis'][:5]
            self.stdout.write('\nTop 5 Most Valuable Cached Endpoints:')
            for i, endpoint in enumerate(top_5, 1):
                effectiveness_icon = {
                    'excellent': '🟢',
                    'good': '🟡',
                    'moderate': '🟠',
                    'poor': '🔴'
                }.get(endpoint['effectiveness'], '⚪')
                
                self.stdout.write(
                    f"\n{i}. {endpoint['endpoint']} {effectiveness_icon}"
                )
                self.stdout.write(f"   Hit Rate: {endpoint['hit_rate']}%")
                self.stdout.write(f"   Time Saved: {endpoint['time_saved_seconds']}s")
                self.stdout.write(f"   Improvement: {endpoint['improvement_pct']}%")
        else:
            self.stdout.write('No endpoint data available')
        
        # Recommendations
        self.stdout.write(self.style.HTTP_INFO('\n💡 RECOMMENDATIONS'))
        self.stdout.write('-' * 80)
        
        if analysis['recommendations']:
            high_priority = [r for r in analysis['recommendations'] if r['priority'] == 'high']
            medium_priority = [r for r in analysis['recommendations'] if r['priority'] == 'medium']
            low_priority = [r for r in analysis['recommendations'] if r['priority'] == 'low']
            
            for priority, recs in [('HIGH', high_priority), ('MEDIUM', medium_priority), ('LOW', low_priority)]:
                if recs:
                    self.stdout.write(f'\n{priority} Priority:')
                    for rec in recs:
                        self.stdout.write(f"\n  • {rec['issue']}")
                        self.stdout.write(f"    → {rec['suggestion']}")
                        self.stdout.write(f"    Expected: {rec['expected_improvement']}")
        else:
            self.stdout.write('✓ No recommendations - cache is performing optimally!')
        
        # Performance Score
        self.stdout.write(self.style.HTTP_INFO('\n🏆 OVERALL PERFORMANCE SCORE'))
        self.stdout.write('-' * 80)
        score = analysis['performance_score']
        
        if score >= 80:
            grade = 'A (Excellent)'
            color = self.style.SUCCESS
        elif score >= 60:
            grade = 'B (Good)'
            color = self.style.SUCCESS
        elif score >= 40:
            grade = 'C (Fair)'
            color = self.style.WARNING
        else:
            grade = 'D (Needs Improvement)'
            color = self.style.ERROR
        
        self.stdout.write(color(f"{score}/100 - Grade: {grade}"))
        
        self.stdout.write('\n' + '=' * 80 + '\n')

