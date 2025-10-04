import asyncio
import base64
import json
import re
import time
import random
from typing import List, Dict, Optional
import aiohttp
import socket
import platform
from astrbot.api import logger

class V2RayNodeFetcher:
    def __init__(self):
        # 缓存数据，存储节点信息和时间戳
        self.node_cache: List[Dict] = []
        self.cache_timestamp: float = 0
        self.cache_duration: int = 3600  # 1小时缓存时间
        
    async def fetch_subscription(self, url: str) -> Optional[str]:
        """获取订阅内容"""
        try:
            logger.info(f"获取订阅内容: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"订阅内容大小: {len(content)} 字符")
                        return content
                    else:
                        logger.warning(f"无法获取订阅内容，状态码: {response.status}")
        except Exception as e:
            logger.error(f"无法获取订阅内容: {e}")
        return None

    def decode_subscription(self, raw_data: str) -> List[str]:
        """解码Base64订阅内容"""
        try:
            # 尝试不同的解码方式
            try:
                decoded_data = base64.b64decode(raw_data).decode('utf-8')
            except Exception:
                # 如果标准解码失败，尝试URL安全的解码
                decoded_data = base64.urlsafe_b64decode(raw_data).decode('utf-8')
            
            lines = decoded_data.splitlines()
            # 只保留vmess://开头的行
            vmess_lines = [line for line in lines if line.startswith('vmess://')]
            logger.info(f"解码完成，找到 {len(vmess_lines)} 个节点")
            return vmess_lines
        except Exception as e:
            logger.error(f"订阅解码失败: {e}")
        return []

    async def check_host_connectivity(self, host: str, port: int = 80, timeout: int = 5) -> bool:
        """检查主机连通性（使用TCP连接而不是ping）"""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def check_node_validity(self, node_lines: List[str]) -> List[Dict]:
        """并发检查所有节点的可用性"""
        logger.info(f"开始检查 {len(node_lines)} 个节点的可用性...")
        valid_nodes = []
        
        # 如果节点数量太多，只检查前30个
        if len(node_lines) > 30:
            node_lines = node_lines[:30]
        
        # 创建并发任务
        tasks = []
        for i, line in enumerate(node_lines):
            try:
                # 提取并解码节点信息
                base64_content = line.replace('vmess://', '')
                node_data = json.loads(base64.b64decode(base64_content).decode('utf-8'))
                
                # 获取端口号，如果没有则默认使用80
                port = int(node_data.get('port', 80))
                
                # 添加连通性检查任务
                tasks.append((node_data, self.check_host_connectivity(node_data['add'], port, 5)))
            except Exception:
                # 解析失败直接跳过
                continue
        
        if not tasks:
            logger.warning("没有有效的节点任务需要检查")
            return []
        
        # 并发执行连通性检查
        check_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        # 收集可用节点
        for i, (node_data, _) in enumerate(tasks):
            if i < len(check_results):
                result = check_results[i]
                if result is True:
                    valid_nodes.append(node_data)
                
        logger.info(f"检查完成，找到 {len(valid_nodes)} 个可用节点")
        return valid_nodes

    def is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.node_cache:
            return False
        # 检查缓存是否在有效期内（1小时）
        return (time.time() - self.cache_timestamp) < self.cache_duration

    async def get_random_node(self) -> Optional[Dict]:
        """获取一个随机可用节点，带缓存机制"""
        # 检查缓存
        if self.is_cache_valid():
            # 从缓存中随机选择一个节点
            if self.node_cache:
                selected_node = random.choice(self.node_cache)
                logger.info(f"使用缓存节点: {selected_node.get('ps', 'N/A')}")
                return selected_node
            else:
                return None
        
        # 缓存过期或无缓存，重新获取数据
        logger.info("重新获取节点数据")
        subscription_url = 'https://gh.y4cc.cc/gh/https://raw.githubusercontent.com/a2470982985/getNode/main/v2ray.txt'
        
        # 1. 获取订阅
        raw_data = await self.fetch_subscription(subscription_url)
        if not raw_data:
            logger.error("无法获取订阅数据")
            return None
            
        # 2. 解码订阅
        node_lines = self.decode_subscription(raw_data)
        if not node_lines:
            logger.warning("未找到有效节点")
            return None
            
        # 3. 检查节点可用性
        valid_nodes = await self.check_node_validity(node_lines)
        if not valid_nodes:
            logger.error("当前没有可用节点")
            return None
            
        # 4. 缓存有效节点和时间戳
        self.node_cache = valid_nodes
        self.cache_timestamp = time.time()
        logger.info(f"缓存 {len(valid_nodes)} 个节点")
        
        # 5. 随机返回一个节点
        selected_node = random.choice(valid_nodes)
        logger.info(f"选择节点: {selected_node.get('ps', 'N/A')}")
        return selected_node

    def format_node_message(self, node: Dict) -> str:
        """格式化节点信息输出"""
        try:
            # 重新编码节点为vmess链接
            node_json = json.dumps(node, separators=(',', ':'))
            vmess_link = 'vmess://' + base64.b64encode(node_json.encode('utf-8')).decode('utf-8')
            
            msg = f"""
🟢 随机可用节点信息
━━━━━━━━━━━━━━━
📌 名称：{node.get('ps', '-')}
🌐 地址：{node.get('add', '-')}
🔢 端口：{node.get('port', '-')}
💻 类型：{node.get('type', '-')}
🆔 UUID：{node.get('id', '-')}
🎯 网络：{node.get('net', '-')}
📂 路径：{node.get('path', '-') or '-'}
🏠 Host：{node.get('host', '-') or '-'}
🔒 TLS：{node.get('tls', '-') or '-'}
📋 可复制 vmess 地址：

{vmess_link}
━━━━━━━━━━━━━━━
"""
            return msg
        except Exception as e:
            return f"⚠️ 格式化节点信息失败: {e}"