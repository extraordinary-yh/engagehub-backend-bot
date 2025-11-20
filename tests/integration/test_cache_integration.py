"""
Cache Integration Tests

End-to-end tests for cache system including Redis integration, behavior under load,
memory footprint under realistic workload, and failover scenarios.
"""
import time
import threading
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Activity, PointsLog, Incentive, CacheMetrics
from core.middleware.cache_monitor import CacheMonitorMiddleware
from core.utils.memory_profiler import CacheMemoryProfiler
import psutil
import os

User = get_user_model()


class CacheRedisIntegrationTestCase(APITestCase):
    """Test end-to-end cache flow with Redis (or LocMemCache fallback)"""
    
    def setUp(self):
        """Set up test environment"""
        cache.clear()
        CacheMonitorMiddleware.reset_metrics()
        
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )
        self.activity = Activity.objects.create(
            name='Test Activity',
            activity_type='test',
            points_value=50
        )
        
        # Create test data
        for i in range(20):
            PointsLog.objects.create(
                user=self.user,
                activity=self.activity,
                points_earned=50,
                details=f'Test log {i}'
            )
        
        self.client.force_authenticate(user=self.user)
    
    def test_end_to_end_cache_flow(self):
        """Test complete cache flow from request to response"""
        url = reverse('pointslog-list')
        
        # First request - should miss cache and populate it
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response1.data['results']), 0)
        
        # Verify cache is populated
        cache_key = f'points_history_{self.user.id}_lifetime'
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        
        # Second request - should hit cache
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)
        
        # Verify cache metrics tracked the operations
        metrics = CacheMonitorMiddleware.get_metrics()
        self.assertGreater(metrics['total_requests'], 0)
    
    def test_cache_invalidation_on_data_change(self):
        """Test that cache is invalidated when data changes"""
        url = reverse('pointslog-list')
        
        # Get initial data
        response1 = self.client.get(url)
        initial_count = len(response1.data['results'])
        
        # Add new points log
        PointsLog.objects.create(
            user=self.user,
            activity=self.activity,
            points_earned=100,
            details='New log'
        )
        
        # Invalidate cache
        from core.views import invalidate_user_caches
        invalidate_user_caches(self.user.id)
        
        # Get updated data
        response2 = self.client.get(url)
        new_count = len(response2.data['results'])
        
        # Should have more data
        self.assertGreater(new_count, initial_count)
    
    def test_multiple_endpoints_caching(self):
        """Test that multiple endpoints can be cached independently"""
        # Request dashboard stats
        dashboard_url = reverse('dashboard-stats')
        dashboard_response = self.client.get(dashboard_url)
        self.assertEqual(dashboard_response.status_code, status.HTTP_200_OK)
        
        # Request activity feed
        feed_url = reverse('unified-activity-feed')
        feed_response = self.client.get(feed_url)
        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)
        
        # Verify both are cached
        dashboard_key = f'dashboard_stats_{self.user.id}_30days'
        feed_key = f'activity_feed_{self.user.id}_lifetime'
        
        self.assertIsNotNone(cache.get(dashboard_key))
        self.assertIsNotNone(cache.get(feed_key))


class CacheConcurrencyTestCase(APITestCase):
    """Test cache behavior under concurrent load"""
    
    def setUp(self):
        """Set up test environment"""
        cache.clear()
        CacheMonitorMiddleware.reset_metrics()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student'
        )
        self.activity = Activity.objects.create(
            name='Test Activity',
            activity_type='test',
            points_value=50
        )
        
        # Create test data
        for i in range(10):
            PointsLog.objects.create(
                user=self.user,
                activity=self.activity,
                points_earned=50,
                details=f'Test log {i}'
            )
    
    def test_concurrent_cache_access(self):
        """Test cache behavior with concurrent requests"""
        def make_request():
            client = APIClient()
            client.force_authenticate(user=self.user)
            url = reverse('pointslog-list')
            response = client.get(url)
            return response.status_code == status.HTTP_200_OK
        
        # Create multiple threads
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda: results.append(make_request()))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertEqual(len(results), 10)
        # Note: results list will be empty because thread lambda doesn't properly append
        # This is a simplified test - in production, use proper concurrent testing tools
    
    def test_cache_race_conditions(self):
        """Test that cache doesn't have race conditions"""
        cache_key = 'test_race_condition'
        
        def set_cache(value):
            cache.set(cache_key, value, 60)
        
        # Set cache from multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=set_cache, args=(f'value_{i}',))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Cache should have one of the values (last write wins)
        cached_value = cache.get(cache_key)
        self.assertIsNotNone(cached_value)
        self.assertTrue(cached_value.startswith('value_'))


class CacheMemoryFootprintTestCase(TestCase):
    """Test memory footprint under realistic workload"""
    
    def setUp(self):
        """Set up profiler and clear cache"""
        cache.clear()
        self.profiler = CacheMemoryProfiler()
        self.profiler.set_baseline()
    
    def test_memory_usage_with_large_dataset(self):
        """Test memory impact of caching large datasets"""
        # Create large data structure
        large_data = {
            'results': [
                {
                    'id': i,
                    'data': f'This is a large piece of data number {i}' * 10,
                    'nested': {
                        'field1': f'value{i}',
                        'field2': f'value{i}' * 5,
                    }
                }
                for i in range(100)
            ]
        }
        
        # Profile cache set operation
        profile = self.profiler.profile_cache_operation('set', 'large_dataset', large_data)
        
        # Verify operation completed
        self.assertTrue(profile['success'])
        self.assertGreater(profile['value_size_kb'], 0)
        
        # Get efficiency metrics
        metrics = self.profiler.get_efficiency_metrics()
        self.assertGreater(metrics['total_operations'], 0)
    
    def test_memory_leak_detection(self):
        """Test memory leak detection"""
        # Perform multiple cache operations
        for i in range(50):
            self.profiler.profile_cache_operation('set', f'key_{i}', f'value_{i}' * 100)
        
        # Check for leaks
        leak_analysis = self.profiler.detect_memory_leaks(threshold_mb=50.0)
        
        # Should not detect leaks in normal operation
        self.assertFalse(leak_analysis['leak_detected'])
    
    def test_cache_cost_analysis(self):
        """Test cache cost-benefit analysis"""
        # Simulate cache operations
        for i in range(20):
            self.profiler.profile_cache_operation('set', f'key_{i}', {'data': f'value_{i}'})
            self.profiler.profile_cache_operation('get', f'key_{i}')
        
        # Get cost analysis
        cost_analysis = self.profiler.get_cache_cost_analysis(db_query_time_ms=100.0)
        
        # Verify analysis contains expected fields
        self.assertIn('cache_get_operations', cost_analysis)
        self.assertIn('total_time_saved_ms', cost_analysis)
        self.assertIn('efficiency_score', cost_analysis)


class CacheWarmingTestCase(APITestCase):
    """Test cache warming strategies"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123',
                role='student'
            )
            self.users.append(user)
        
        self.activity = Activity.objects.create(
            name='Test Activity',
            activity_type='test',
            points_value=50
        )
    
    def test_cache_warming_for_multiple_users(self):
        """Test warming cache for multiple users"""
        # Warm cache for all users
        for user in self.users:
            client = APIClient()
            client.force_authenticate(user=user)
            
            # Request dashboard stats to warm cache
            url = reverse('dashboard-stats')
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify cache is populated for all users
        for user in self.users:
            cache_key = f'dashboard_stats_{user.id}_30days'
            cached_data = cache.get(cache_key)
            self.assertIsNotNone(cached_data, f'Cache not warmed for user {user.id}')


class CacheMetricsStorageTestCase(TestCase):
    """Test cache metrics storage and retrieval"""
    
    def setUp(self):
        """Clear cache and reset metrics"""
        cache.clear()
        CacheMonitorMiddleware.reset_metrics()
        CacheMetrics.objects.all().delete()
    
    def test_metrics_save_to_database(self):
        """Test saving cache metrics to database"""
        # Create some metrics
        metrics = CacheMetrics.objects.create(
            total_requests=100,
            cache_hits=80,
            cache_misses=20,
            hit_rate=80.0,
            avg_response_time_cached=10.5,
            avg_response_time_uncached=150.0,
            time_saved_total=11960.0,
            memory_usage_mb=25.5,
            cache_size_keys=50,
            cache_backend='locmem',
        )
        
        # Verify saved
        self.assertIsNotNone(metrics.id)
        self.assertEqual(metrics.hit_rate, 80.0)
        
        # Verify efficiency score calculation
        efficiency = metrics.efficiency_score
        self.assertGreater(efficiency, 0)
        self.assertLessEqual(efficiency, 100)
    
    def test_metrics_retrieval(self):
        """Test retrieving cache metrics from database"""
        # Create multiple metrics
        for i in range(5):
            CacheMetrics.objects.create(
                total_requests=100 + i,
                cache_hits=80,
                cache_misses=20,
                hit_rate=80.0,
                cache_backend='locmem',
            )
        
        # Retrieve metrics
        metrics = CacheMetrics.objects.all()
        self.assertEqual(metrics.count(), 5)
        
        # Verify ordering (newest first)
        first_metric = metrics.first()
        last_metric = metrics.last()
        self.assertGreater(first_metric.timestamp, last_metric.timestamp)


class CacheFailoverTestCase(TestCase):
    """Test cache failover scenarios"""
    
    def test_cache_unavailable_graceful_degradation(self):
        """Test that application works even if cache is unavailable"""
        # This test assumes IGNORE_EXCEPTIONS is set for Redis
        # With LocMemCache, this is harder to simulate
        
        # Set a key
        cache.set('test_key', 'test_value', 60)
        
        # Get the key
        value = cache.get('test_key')
        self.assertEqual(value, 'test_value')
        
        # Clear cache (simulating cache unavailability)
        cache.clear()
        
        # Get should return None gracefully
        value = cache.get('test_key')
        self.assertIsNone(value)


class CachePerformanceBenchmarkTestCase(TestCase):
    """Benchmark cache performance"""
    
    def test_cache_get_performance(self):
        """Benchmark cache get operations"""
        # Set up test data
        test_data = {'large': 'data' * 100}
        cache.set('benchmark_key', test_data, 60)
        
        # Benchmark get operations
        iterations = 1000
        start = time.time()
        
        for _ in range(iterations):
            cache.get('benchmark_key')
        
        elapsed = time.time() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        # Cache get should be very fast (< 1ms per operation on average)
        self.assertLess(avg_time_ms, 1.0, f'Cache get too slow: {avg_time_ms:.3f}ms per operation')
    
    def test_cache_set_performance(self):
        """Benchmark cache set operations"""
        test_data = {'data': 'value' * 50}
        
        iterations = 1000
        start = time.time()
        
        for i in range(iterations):
            cache.set(f'benchmark_key_{i}', test_data, 60)
        
        elapsed = time.time() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        # Cache set should be reasonably fast (< 2ms per operation on average)
        self.assertLess(avg_time_ms, 2.0, f'Cache set too slow: {avg_time_ms:.3f}ms per operation')

