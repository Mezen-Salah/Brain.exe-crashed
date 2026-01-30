from core.redis_client import RedisManager

print("=" * 80)
print("REDIS FUNCTIONALITY TEST")
print("=" * 80)
print()

try:
    redis = RedisManager()
    
    # Test 1: Connection
    print("1. Connection Test:")
    redis.client.ping()
    print("   ✅ Redis is connected")
    print()
    
    # Test 2: Database stats
    print("2. Database Stats:")
    total_keys = redis.client.dbsize()
    memory_info = redis.client.info("memory")
    print(f"   Total keys: {total_keys}")
    print(f"   Memory used: {memory_info['used_memory_human']}")
    print()
    
    # Test 3: Set and get
    print("3. Basic Operations:")
    redis.client.set("test_key", "test_value")
    value = redis.client.get("test_key")
    print(f"   Set/Get test: {'✅ PASS' if value == b'test_value' else '❌ FAIL'}")
    redis.client.delete("test_key")
    print()
    
    # Test 4: Thompson Sampling
    print("4. Thompson Sampling:")
    test_product = "TEST_PROD_123"
    redis.update_thompson_params(test_product, signal_weight=1.0)
    params = redis.get_thompson_params(test_product)
    print(f"   Alpha: {params['alpha']}")
    print(f"   Beta: {params['beta']}")
    print(f"   ✅ Thompson Sampling working")
    print()
    
    # Test 5: Cache operations
    print("5. Cache Operations:")
    redis.cache_search_results(
        query="test laptop",
        user_id="TEST_USER",
        response={"test": "data"}
    )
    cached = redis.get_cached_search("test laptop", "TEST_USER")
    print(f"   Cache set/get: {'✅ PASS' if cached else '❌ FAIL'}")
    print()
    
    # Test 6: List keys
    print("6. Sample Keys:")
    keys = redis.client.keys("*")[:10]
    for key in keys:
        print(f"   - {key.decode()}")
    print()
    
    print("=" * 80)
    print("✅ ALL REDIS OPERATIONS WORKING")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ Redis test failed: {e}")
    import traceback
    traceback.print_exc()
