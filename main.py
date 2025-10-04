from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from .v2ray_node_fetcher import V2RayNodeFetcher

@register("v2ray_nodes", "xxcyou", "一个用于获取 V2Ray 节点的插件", "1.0.6", "https://github.com/xxcyou/astrbot_plugin_v2ray")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.node_fetcher = V2RayNodeFetcher()
        
        # 处理配置参数
        self.config = config
        if self.config:
            self.is_tool_enabled = self.config.get("enable_node_tool", True)
        else:
            self.is_tool_enabled = True

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("V2Ray节点工具插件已加载。")
        logger.info(f" - 工具启用状态: {self.is_tool_enabled}")
        
        if not self.is_tool_enabled:
            logger.warning("V2Ray节点工具当前已被禁用，将不会注册函数工具。")
    
    # 注册 MCP 工具的装饰器。当用户需要节点或者偷群主节点时调用此函数。
    @filter.llm_tool(name="steal_node", description="偷节点来用")
    async def steal_node_tool(self, event: AstrMessageEvent) -> MessageEventResult:
        """
        偷节点来用
        当用户有描述需要节点或者偷群主节点时调用此函数，不需要参数
        """
        # 检查工具是否启用
        if not self.is_tool_enabled:
            logger.warning(f"LLM尝试调用已禁用的 steal_node 工具。调用者: {event.get_sender_name()}")
            return event.plain_result("抱歉，节点工具当前不可用。")
        
        try:
            # 获取一个随机可用节点
            node = await self.node_fetcher.get_random_node()
            
            if not node:
                return event.plain_result("❌ 无法获取可用节点，请稍后再试")
            
            # 格式化节点信息
            msg = self.node_fetcher.format_node_message(node)
            return event.plain_result(msg)
        except Exception as e:
            logger.error(f"获取节点时出错: {e}")
            return event.plain_result("⚠️ 脚本执行异常，已捕获")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("V2Ray节点工具插件已卸载。")