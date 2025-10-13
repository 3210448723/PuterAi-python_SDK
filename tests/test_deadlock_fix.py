#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死锁修复测试脚本

测试Token管理器和代理管理器是否已修复死锁问题
"""

import sys
import os

# 强制测试模式下使用独立 token_pool.test.json，避免污染生产池
os.environ.setdefault('TEST_MODE', '1')
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)


def test_token_manager_concurrency():
    """测试Token管理器的并发操作"""
    print("🧪 测试Token管理器并发操作...")
    
    try:
        from utils import get_token_manager
        token_manager = get_token_manager()
        
        # 添加一些测试Token
        test_tokens = [
            f"test_token_{i}_{''.join([chr(65 + (j % 26)) for j in range(20)])}" 
            for i in range(5)
        ]
        
        for i, token in enumerate(test_tokens):
            token_manager.add_token(token, is_primary=(i == 0))
        
        def worker_function(worker_id):
            """工作线程函数"""
            results = []
            
            for i in range(10):  # 每个线程执行10次操作
                try:
                    # 获取当前Token
                    current = token_manager.get_current_token()
                    if current:
                        results.append(f"Worker-{worker_id}: Got token {current[:12]}...")
                        
                        # 模拟使用Token
                        time.sleep(0.01)
                        
                        # 标记使用成功/失败
                        success = (i % 3) != 0  # 2/3的概率成功
                        token_manager.mark_token_used(current, success=success)
                        
                        if not success and (i % 5) == 0:  # 偶尔标记为无效
                            token_manager.mark_token_invalid(current, f"Test error from worker {worker_id}")
                    
                    # 获取统计信息
                    stats = token_manager.get_token_stats()
                    results.append(f"Worker-{worker_id}: Stats - {stats['active_tokens']} active")
                    
                    time.sleep(0.01)
                    
                except Exception as e:
                    results.append(f"Worker-{worker_id}: Error - {e}")
            
            return results
        
        # 使用多个线程并发执行
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_function, i) for i in range(8)]
            
            all_results = []
            for future in as_completed(futures, timeout=30):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"线程执行失败: {e}")
        
        # 输出结果
        logger.info(f"并发测试完成，总共执行了 {len(all_results)} 个操作")
        
        # 检查最终状态
        final_stats = token_manager.get_token_stats()
        logger.info(f"最终Token统计: {final_stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Token管理器并发测试失败: {e}")
        return False


def test_proxy_manager_concurrency():
    """测试代理管理器的并发操作"""
    print("🧪 测试代理管理器并发操作...")
    
    try:
        from utils import get_proxy_manager
        proxy_manager = get_proxy_manager()
        
        # 添加一些测试代理
        test_proxies = [
            (f"192.168.1.{100 + i}", f"808{i}") 
            for i in range(10)
        ]
        
        for ip, port in test_proxies:
            proxy_manager.add_proxy(ip, port, verified=True)
        
        def worker_function(worker_id):
            """工作线程函数"""
            results = []
            
            for i in range(5):  # 每个线程执行5次操作
                try:
                    # 获取可用代理
                    proxy = proxy_manager.get_available_proxy()
                    if proxy:
                        ip, port = proxy
                        results.append(f"Worker-{worker_id}: Got proxy {ip}:{port}")
                        
                        # 模拟使用代理
                        time.sleep(0.01)
                        
                        # 标记使用结果
                        success = (i % 2) == 0  # 50%的概率成功
                        proxy_manager.mark_proxy_used(ip, str(port), success=success)
                    
                    # 获取统计信息
                    stats = proxy_manager.get_proxy_stats()
                    results.append(f"Worker-{worker_id}: Stats - {stats['verified_proxies']} verified")
                    
                    time.sleep(0.01)
                    
                except Exception as e:
                    results.append(f"Worker-{worker_id}: Error - {e}")
            
            return results
        
        # 使用多个线程并发执行
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(worker_function, i) for i in range(6)]
            
            all_results = []
            for future in as_completed(futures, timeout=20):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"线程执行失败: {e}")
        
        # 输出结果
        logger.info(f"并发测试完成，总共执行了 {len(all_results)} 个操作")
        
        # 检查最终状态
        final_stats = proxy_manager.get_proxy_stats()
        logger.info(f"最终代理统计: {final_stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"代理管理器并发测试失败: {e}")
        return False


def test_mixed_operations():
    """测试混合操作（同时使用Token和代理管理器）"""
    print("🧪 测试混合并发操作...")
    
    try:
        from utils import get_token_manager, get_proxy_manager
        
        def mixed_worker(worker_id):
            """混合工作线程"""
            results = []
            token_manager = get_token_manager()
            proxy_manager = get_proxy_manager()
            
            for i in range(3):
                try:
                    # 交替操作Token和代理
                    if i % 2 == 0:
                        # Token操作
                        current = token_manager.get_current_token()
                        if current:
                            results.append(f"Mixed-{worker_id}: Token {current[:10]}...")
                            token_manager.mark_token_used(current, success=True)
                    else:
                        # 代理操作
                        proxy = proxy_manager.get_available_proxy()
                        if proxy:
                            ip, port = proxy
                            results.append(f"Mixed-{worker_id}: Proxy {ip}:{port}")
                            proxy_manager.mark_proxy_used(ip, str(port), success=True)
                    
                    time.sleep(0.02)
                    
                except Exception as e:
                    results.append(f"Mixed-{worker_id}: Error - {e}")
            
            return results
        
        # 并发执行混合操作
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(mixed_worker, i) for i in range(4)]
            
            all_results = []
            for future in as_completed(futures, timeout=15):
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"混合线程执行失败: {e}")
        
        logger.info(f"混合并发测试完成，总共执行了 {len(all_results)} 个操作")
        return True
        
    except Exception as e:
        logger.error(f"混合并发测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🔧 死锁修复测试")
    print("=" * 50)
    
    tests = [
        ("Token管理器并发测试", test_token_manager_concurrency),
        ("代理管理器并发测试", test_proxy_manager_concurrency),
        ("混合操作并发测试", test_mixed_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n开始 {test_name}...")
        start_time = time.time()
        
        try:
            if test_func():
                passed += 1
                duration = time.time() - start_time
                print(f"✅ {test_name} 通过 ({duration:.2f}s)")
            else:
                duration = time.time() - start_time
                print(f"❌ {test_name} 失败 ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} 异常: {e} ({duration:.2f}s)")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有并发测试通过，死锁问题已修复")
        return True
    else:
        print("❌ 部分测试失败，可能仍存在死锁问题")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
