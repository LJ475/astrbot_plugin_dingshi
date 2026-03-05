import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("advanced_timer", "YourName", "自定义时间提醒插件", "1.1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        """
        格式1: /提醒我 10s 喝水 (支持 s, m, h)
        格式2: /提醒我 2026-05-20 13:14 告白
        """
        msg = event.message_str.replace("/提醒我", "").strip()
        if not msg:
            yield event.plain_result("请输入内容！格式：/提醒我 [时间] [内容]\n示例：/提醒我 10s 泡面")
            return

        # 1. 尝试解析 相对时间 (例如 10s, 5m)
        relative_match = re.match(r"^(\d+)([smh秒分时])\s+(.*)$", msg)
        # 2. 尝试解析 具体日期 (例如 2026-05-20 13:14)
        absolute_match = re.match(r"^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})\s+(.*)$", msg)

        delay_seconds = 0
        remind_content = ""

        if relative_match:
            value, unit, remind_content = relative_match.groups()
            unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
            delay_seconds = int(value) * unit_map.get(unit, 1)
        
        elif absolute_match:
            time_str, remind_content = absolute_match.groups()
            try:
                target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                delay_seconds = (target_time - datetime.now()).total_seconds()
            except ValueError:
                yield event.plain_result("日期格式错啦！请使用: YYYY-MM-DD HH:MM")
                return
        else:
            yield event.plain_result("格式没对上，试试：\n/提醒我 10s 喝水\n/提醒我 2026-01-01 12:00 元旦快乐")
            return

        if delay_seconds < 0:
            yield event.plain_result("这个时间已经过去啦！")
            return

        user_name = event.get_sender_name()
        yield event.plain_result(f"✅ 没问题 {user_name}，已开启倒计时（约 {int(delay_seconds)} 秒后提醒）。")

        # 异步等待
        await asyncio.sleep(delay_seconds)

        # 提醒
        yield event.plain_result(f"🔔 时间到！{user_name}\n内容：{remind_content}")
