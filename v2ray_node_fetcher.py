import asyncio
import base64
import json
import re
import time
import random
from typing import List, Dict, Optional
import aiohttp
import subprocess
import platform

class V2RayNodeFetcher:
    def __init__(self):
        # 缓存数据，存储节点信息和时间戳
        self.node_cache: List[Dict] = []
        self.cache_timestamp: float = 0
        self.cache_duration: int = 3600  # 1小时缓存时间
        
    async def fetch_subscription(self, url: str) -> Optional[str]:
        """获取订阅内容"""
        try:
            print(f"正在获取订阅内容: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"订阅响应状态码: {response.status}")
                    if response.status == 200:
                        content = await response.text()
                        print(f"订阅内容大小: {len(content)} 字符")
                        return content
                    else:
                        print(f"⚠️ 无法获取订阅内容，状态码: {response.status}")
        except Exception as e:
            print(f"⚠️ 无法获取订阅内容，请检查网络: {e}")
        return None

    def decode_subscription(self, raw_data: str) -> List[str]:
        """解码Base64订阅内容"""
        try:
            print("正在解码订阅内容...")
            decoded_data = base64.b64decode(raw_data).decode('utf-8')
            lines = decoded_data.splitlines()
            # 只保留vmess://开头的行
            vmess_lines = [line for line in lines if line.startswith('vmess://')]
            print(f"解码完成，找到 {len(vmess_lines)} 个节点")
            return vmess_lines
        except Exception as e:
            print(f"⚠️ 订阅解码失败: {e}")
        return []

    async def ping_host(self, host: str) -> bool:
        """Ping主机检查连通性"""
        try:
            # 根据操作系统选择ping命令
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", host]  # Windows: -w 2000ms超时
            else:
                cmd = ["ping", "-c", "1", "-W", "2", host]     # Unix/Linux: -W 2s超时
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await process.communicate()
            result = process.returncode == 0
            print(f"Ping {host}: {'成功' if result else '失败'}")
            return result
        except Exception as e:
            print(f"Ping {host} 失败: {e}")
            return False

    async def check_node_validity(self, node_lines: List[str]) -> List[Dict]:
        """并发检查所有节点的可用性"""
        print(f"开始检查 {len(node_lines)} 个节点的可用性...")
        valid_nodes = []
        
        # 创建并发任务
        tasks = []
        for i, line in enumerate(node_lines):
            try:
                # 提取并解码节点信息
                base64_content = line.replace('vmess://', '')
                node_data = json.loads(base64.b64decode(base64_content).decode('utf-8'))
                tasks.append((node_data, self.ping_host(node_data['add'])))
                # 限制并发数量，避免过多的ping请求
                if i >= 20:  # 只检查前20个节点
                    print("达到最大检查节点数限制(20个)，跳过剩余节点")
                    break
            except Exception as e:
                print(f"解析第 {i+1} 个节点失败: {e}")
                # 解析失败直接跳过
                continue
        
        if not tasks:
            print("没有有效的节点任务需要检查")
            return []
        
        print(f"开始并发ping {len(tasks)} 个节点...")
        # 并发执行ping检查
        ping_results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
        
        # 收集可用节点
        for i, (node_data, _) in enumerate(tasks):
            if i < len(ping_results):
                result = ping_results[i]
                if result is True:
                    valid_nodes.append(node_data)
                    print(f"节点 {node_data.get('ps', 'N/A')} 可用")
                elif isinstance(result, Exception):
                    print(f"节点 {node_data.get('ps', 'N/A')} 检查时出现异常: {result}")
                
        print(f"检查完成，找到 {len(valid_nodes)} 个可用节点")
        return valid_nodes

    def is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.node_cache:
            print("缓存为空")
            return False
        # 检查缓存是否在有效期内（1小时）
        is_valid = (time.time() - self.cache_timestamp) < self.cache_duration
        print(f"缓存有效性检查: {'有效' if is_valid else '已过期'}")
        return is_valid

    async def get_random_node(self) -> Optional[Dict]:
        """获取一个随机可用节点，带缓存机制"""
        print("开始获取随机节点...")
        # 检查缓存
        if self.is_cache_valid():
            print("使用缓存的节点数据")
            # 从缓存中随机选择一个节点
            if self.node_cache:
                selected_node = random.choice(self.node_cache)
                print(f"从缓存中选择节点: {selected_node.get('ps', 'N/A')}")
                return selected_node
            else:
                print("缓存为空")
                return None
        
        # 缓存过期或无缓存，重新获取数据
        print("重新获取节点数据")
        subscription_url = 'https://raw.githubusercontent.com/a2470982985/getNode/main/v2ray.txt'
        
        # 1. 获取订阅
        raw_data = await self.fetch_subscription(subscription_url)
        if not raw_data:
            print("无法获取订阅数据")
            return None
            
        # 2. 解码订阅
        node_lines = self.decode_subscription(raw_data)
        if not node_lines:
            print("⚠️ 未找到有效节点")
            return None
            
        # 3. 检查节点可用性
        valid_nodes = await self.check_node_validity(node_lines)
        if not valid_nodes:
            print("❌ 当前没有可用节点")
            return None
            
        # 4. 缓存有效节点和时间戳
        self.node_cache = valid_nodes
        self.cache_timestamp = time.time()
        print(f"缓存 {len(valid_nodes)} 个节点")
        
        # 5. 随机返回一个节点
        selected_node = random.choice(valid_nodes)
        print(f"选择节点: {selected_node.get('ps', 'N/A')}")
        return selected_node

    def format_node_message(self, node: Dict) -> str:
        """格式化节点信息输出"""
        try:
            # 重新编码节点为vmess链接
            node_json = json.dumps(node, separators=(',', ':'))
            vmess_link = 'vmess://' + base64.b64encode(node_json.encode('utf-8')).decode('utf-8')
            
            msg = f"""
🟢 随机可用节点信息(我希望原封不动输出)
━━━━━━━━━━━━━━━━━━
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
━━━━━━━━━━━━━━━━━━
"""
            return msg
        except Exception as e:
            return f"⚠️ 格式化节点信息失败: {e}"