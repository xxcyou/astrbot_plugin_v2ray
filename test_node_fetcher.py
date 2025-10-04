#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V2Ray节点获取器测试脚本
用于测试v2ray_node_fetcher.py模块的功能
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from v2ray_node_fetcher import V2RayNodeFetcher

async def test_node_fetcher():
    """测试节点获取功能"""
    print("🚀 开始测试V2Ray节点获取器...")
    
    # 创建节点获取器实例
    fetcher = V2RayNodeFetcher()
    
    try:
        print("🔍 正在获取随机可用节点...")
        # 获取一个随机节点
        node = await fetcher.get_random_node()
        
        if node:
            print("✅ 成功获取到节点!")
            # 格式化并显示节点信息
            msg = fetcher.format_node_message(node)
            print(msg)
        else:
            print("❌ 未能获取到可用节点")
            print("可能的原因:")
            print("1. 网络连接问题")
            print("2. 订阅源不可用")
            print("3. 没有可用的节点")
            
    except Exception as e:
        print(f"⚠️ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

async def test_cache_mechanism():
    """测试缓存机制"""
    print("\nキャッシング 开始测试缓存机制...")
    
    fetcher = V2RayNodeFetcher()
    
    # 第一次获取节点
    print("⏱️ 第一次获取节点...")
    start_time = asyncio.get_event_loop().time()
    node1 = await fetcher.get_random_node()
    first_time = asyncio.get_event_loop().time() - start_time
    print(f"第一次获取耗时: {first_time:.2f}秒")
    
    if not node1:
        print("❌ 第一次获取节点失败，无法继续测试缓存机制")
        return
    
    # 第二次获取节点（应该使用缓存）
    print("⏱️ 第二次获取节点（应该使用缓存）...")
    start_time = asyncio.get_event_loop().time()
    node2 = await fetcher.get_random_node()
    second_time = asyncio.get_event_loop().time() - start_time
    print(f"第二次获取耗时: {second_time:.2f}秒")
    
    if node2:
        print("✅ 缓存机制测试完成")
        print(f"性能提升: {((first_time - second_time) / first_time * 100):.1f}%")
    else:
        print("❌ 第二次获取节点失败")

async def main():
    """主函数"""
    print("=" * 50)
    print("V2Ray节点获取器测试工具")
    print("=" * 50)
    
    # 测试节点获取功能
    await test_node_fetcher()
    
    # 测试缓存机制
    await test_cache_mechanism()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())