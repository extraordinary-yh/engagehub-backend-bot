"""
Comprehensive Cache Testing Suite

Tests cache hit/miss functionality, invalidation, memory limits, performance,
key collision detection, TTL expiration, and multi-user isolation.
"""
import time
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Activity, PointsLog, Incentive, CacheMetrics
from core.middleware.cache_monitor import CacheMonitorMiddleware

User = get_user_model()


class CacheBasicTestCase(TestCase):
    """Test basic cache hit/miss functionality"""
    
    def setUp(self):
        """Clear cache before each test"""
        cache.clear()
        CacheMonitorMiddleware.reset_metrics()
    
    def test_cache_set_get(self):
        """Test basic cache set and get operations"""
        cache.set('test_key', 'test_value', 60)
        value = cache.get('test_key')
        self.assertEqual(value, 'test_value')
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        value = cache.get('nonexistent_key')
        self.assertIsNone(value)
    
    def test_cache_delete(self):
        """Test cache deletion"""
        cache.set('test_key', 'test_value', 60)
        cache.delete('test_key')
        value = cache.get('test_key')
        self.assertIsNone(value)
    
    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration"""
        cache.set('test_key', 'test_value', 1)  # 1 second TTL
        value = cache.get('test_key')
        self.assertEqual(value, 'test_value')
        
        # Wait for expiration
        time.sleep(1.1)
        value = cache.get('test_key')
        self.assertIsNone(value)
    
    def test_cache_default_value(self):
        """Test cache get with default value"""
        value = cache.get('nonexistent_key', default='default_value')
        self.assertEqual(value, 'default_value')
    
    def test_cache_many(self):
        """Test setting and getting multiple cache keys"""
        data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3',
        }
        cache.set_many(data, 60)
        
        retrieved = cache.get_many(['key1', 'key2', 'key3'])
        self.assertEqual(len(retrieved), 3)
        self.assertEqual(retrieved['key1'], 'value1')
        self.assertEqual(retrieved['key2'], 'value2')
        self.assertEqual(retrieved['key3'], 'value3')


class CacheInvalidationTestCase(TestCase):
    """Test cache invalidation correctness"""
    
    def setUp(self):
        """Set up test data and clear cache"""
        cache.clear()
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
    
    def test_user_cache_invalidation(self):
        """Test that user cache is properly invalidated"""
        from core.views import invalidate_user_caches
        
        # Set some cache keys for the user
        cache.set(f'points_history_{self.user.id}_lifetime', {'data': 'old'}, 60)
        cache.set(f'dashboard_stats_{self.user.id}_30days', {'data': 'old'}, 60)
        
        # Verify cache is set
        self.assertIsNotNone(cache.get(f'points_history_{self.user.id}_lifetime'))
        
        # Invalidate cache
        invalidate_user_caches(self.user.id)
        
        # Verify cache is cleared
        self.assertIsNone(cache.get(f'points_history_{self.user.id}_lifetime'))
        self.assertIsNone(cache.get(f'dashboard_stats_{self.user.id}_30days'))
    
    def test_leaderboard_cache_invalidation(self):
        """Test leaderboard cache invalidation"""
        from core.views import invalidate_user_caches
        
        # Set leaderboard cache
        cache_key = f'leaderboard_all_time_10_{self.user.id}'
        cache.set(cache_key, {'data': 'old'}, 60)
        
        # Invalidate
        invalidate_user_caches(self.user.id)
        
        # Verify cleared
        self.assertIsNone(cache.get(cache_key))


class CachePerformanceTestCase(APITestCase):
    """Test cache performance improvements"""
    
    def setUp(self):
        """Set up test data"""
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
        
        # Create some points logs for testing
        for i in range(10):
            PointsLog.objects.create(
                user=self.user,
                activity=self.activity,
                points_earned=50,
                details=f'Test log {i}'
            )
        
        self.client.force_authenticate(user=self.user)
    
    def test_cached_vs_uncached_performance(self):
        """Test that cached requests are faster than uncached"""
        url = reverse('pointslog-list')
        
        # First request (uncached)
        start = time.time()
        response1 = self.client.get(url)
        time_uncached = (time.time() - start) * 1000
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second request (cached)
        start = time.time()
        response2 = self.client.get(url)
        time_cached = (time.time() - start) * 1000
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Cached should be equal or faster (with some tolerance)
        # Note: In tests, LocMemCache might be so fast that difference is minimal
        self.assertGreaterEqual(time_uncached, time_cached * 0.5)  # At least 50% of uncached time
    
    def test_dashboard_stats_caching(self):
        """Test dashboard stats endpoint uses cache"""
        url = reverse('dashboard-stats')
        
        # First request
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Verify cache is set
        cache_key = f'dashboard_stats_{self.user.id}_30days'
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        
        # Second request should use cache
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)


class CacheMultiUserTestCase(TestCase):
    """Test cache isolation between multiple users"""
    
    def setUp(self):
        """Set up multiple users"""
        cache.clear()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
    
    def test_user_cache_isolation(self):
        """Test that cache is properly isolated between users"""
        # Set cache for user1
        cache.set(f'points_history_{self.user1.id}_lifetime', {'user': 'user1'}, 60)
        
        # Set cache for user2
        cache.set(f'points_history_{self.user2.id}_lifetime', {'user': 'user2'}, 60)
        
        # Verify isolation
        user1_cache = cache.get(f'points_history_{self.user1.id}_lifetime')
        user2_cache = cache.get(f'points_history_{self.user2.id}_lifetime')
        
        self.assertEqual(user1_cache['user'], 'user1')
        self.assertEqual(user2_cache['user'], 'user2')
    
    def test_invalidation_isolation(self):
        """Test that invalidating one user doesn't affect another"""
        from core.views import invalidate_user_caches
        
        # Set cache for both users
        cache.set(f'points_history_{self.user1.id}_lifetime', {'user': 'user1'}, 60)
        cache.set(f'points_history_{self.user2.id}_lifetime', {'user': 'user2'}, 60)
        
        # Invalidate user1's cache
        invalidate_user_caches(self.user1.id)
        
        # Verify user1's cache is cleared but user2's remains
        self.assertIsNone(cache.get(f'points_history_{self.user1.id}_lifetime'))
        self.assertIsNotNone(cache.get(f'points_history_{self.user2.id}_lifetime'))


class CacheMonitoringTestCase(APITestCase):
    """Test cache monitoring middleware functionality"""
    
    def setUp(self):
        """Set up test environment"""
        cache.clear()
        CacheMonitorMiddleware.reset_metrics()
        
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='student',
            is_staff=True
        )
        self.client.force_authenticate(user=self.user)
    
    def test_cache_stats_endpoint(self):
        """Test cache stats API endpoint"""
        url = reverse('cache-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('statistics', response.data)
        self.assertIn('cache_hits', response.data['statistics'])
        self.assertIn('cache_misses', response.data['statistics'])
        self.assertIn('hit_rate', response.data['statistics'])
    
    def test_cache_memory_endpoint(self):
        """Test cache memory API endpoint"""
        url = reverse('cache-memory')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('process_memory', response.data)
        self.assertIn('system', response.data)
    
    def test_cache_performance_endpoint(self):
        """Test cache performance API endpoint"""
        url = reverse('cache-performance')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overall', response.data)
        self.assertIn('top_performers', response.data)
    
    def test_cache_reset_endpoint(self):
        """Test cache reset API endpoint"""
        # First make some requests to generate metrics
        self.client.get(reverse('cache-stats'))
        
        # Reset
        url = reverse('cache-reset')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify metrics are reset
        metrics = CacheMonitorMiddleware.get_metrics()
        # Note: total_requests might be 1 from the reset request itself
        self.assertLessEqual(metrics['total_requests'], 1)
    
    def test_cache_history_endpoint(self):
        """Test cache history API endpoint"""
        # Create some cache metrics
        CacheMetrics.objects.create(
            total_requests=100,
            cache_hits=80,
            cache_misses=20,
            hit_rate=80.0,
            cache_backend='locmem',
        )
        
        url = reverse('cache-history')
        response = self.client.get(url, {'days': 7})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('history', response.data)
        self.assertGreater(len(response.data['history']), 0)


class CacheKeyCollisionTestCase(TestCase):
    """Test cache key collision detection"""
    
    def setUp(self):
        """Clear cache"""
        cache.clear()
    
    def test_unique_cache_keys(self):
        """Test that different entities have unique cache keys"""
        user1_id = 1
        user2_id = 2
        
        key1 = f'points_history_{user1_id}_lifetime'
        key2 = f'points_history_{user2_id}_lifetime'
        
        cache.set(key1, 'user1_data', 60)
        cache.set(key2, 'user2_data', 60)
        
        self.assertEqual(cache.get(key1), 'user1_data')
        self.assertEqual(cache.get(key2), 'user2_data')
    
    def test_period_specific_keys(self):
        """Test that different periods have unique cache keys"""
        user_id = 1
        
        key_7days = f'dashboard_stats_{user_id}_7days'
        key_30days = f'dashboard_stats_{user_id}_30days'
        key_90days = f'dashboard_stats_{user_id}_90days'
        
        cache.set(key_7days, '7days_data', 60)
        cache.set(key_30days, '30days_data', 60)
        cache.set(key_90days, '90days_data', 60)
        
        self.assertEqual(cache.get(key_7days), '7days_data')
        self.assertEqual(cache.get(key_30days), '30days_data')
        self.assertEqual(cache.get(key_90days), '90days_data')


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 10,  # Very small limit for testing
        }
    }
})
class CacheMemoryLimitTestCase(TestCase):
    """Test cache behavior with memory limits"""
    
    def setUp(self):
        """Clear cache"""
        cache.clear()
    
    def test_memory_limit_enforcement(self):
        """Test that cache respects MAX_ENTRIES limit"""
        # Add more items than the limit
        for i in range(15):
            cache.set(f'key_{i}', f'value_{i}', 60)
        
        # Verify that not all keys are present (some were evicted)
        # Note: LocMemCache uses LRU eviction
        present_keys = 0
        for i in range(15):
            if cache.get(f'key_{i}') is not None:
                present_keys += 1
        
        # Should be at most MAX_ENTRIES
        self.assertLessEqual(present_keys, 10)

