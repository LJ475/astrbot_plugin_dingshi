import asyncio # 引入异步 IO 库
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("timer_msg", "YourName", "10秒延迟回复插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        """发送：/提醒我 [内容]，机器人会在 10 秒后回复"""
        
        # 1. 获取用户想说的话（去掉指令部分）
        # message_str 通常包含 "/提醒我 xxx"，我们把指令前缀去掉
        content = event.message_str.replace("/提醒我", "").strip()
        if not content:
            content = "时间到啦！"
            
        user_name = event.get_sender_name()
        
        # 2. 先给用户一个即时反馈，告诉他任务已创建
        yield event.plain_result(f"好的 {user_name}，我已经记下了。10秒后我会提醒你：{content}")

        # 3. 异步等待 10 秒（不会卡住整个机器人）
        await asyncio.sleep(10)

        # 4. 时间到，发送第二条消息
        # 注意：这里继续使用 yield 发送结果
        yield event.plain_result(f"🔔 嘿 {user_name}，10秒到了！你之前让我提醒你：{content}")

    async def terminate(self):
        pass
