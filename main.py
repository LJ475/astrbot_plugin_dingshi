import asyncio
import re
from datetime import datetime, timedelta
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("simple_timer", "YourName", "全通用定时提醒", "1.4.2")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        """发送 /定时 获取使用帮助"""
        guide_text = (
            "🔔 欢迎使用定时功能！\n"
            "--------------------------\n"
            "1️⃣ 快速提醒：/提醒我 10s 喝水\n"
            "2️⃣ 精确时间：/提醒我 21:45 睡觉\n"
            "3️⃣ 完整日期：/提醒我 2026-03-05 22:30 睡觉\n"
            "--------------------------\n"
            "💡 直接发送对应指令即可设置。"
        )
        yield event.plain_result(guide_text)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        raw_text = event.message_str.replace("/提醒我", "").strip()
        if not raw_text:
            yield event.plain_result("❌ 请输入内容！例如：/提醒我 10s 喝水")
            return

        delay_seconds = 0
        remind_content = ""
        now = datetime.now() # 获取系统当前时间

        # 1. 解析相对时间 (10s, 5m 等)
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        
        # 2. 解析完整日期 (2026-03-05 22:30)
        abs_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", raw_text)
        
        # 3. 解析仅当天时间 (22:30)
        today_time_match = re.search(r"(\d{2}:\d{2})", raw_text)

        if rel_match:
            value = int(rel_match.group(1))
            unit = rel_match.group(2)
            unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
            delay_seconds = value * unit_map.get(unit, 1)
            remind_content = raw_text.replace(rel_match.group(0), "").strip()
        elif abs_match:
            try:
                target_time = datetime.strptime(abs_match.group(1), "%Y-%m-%d %H:%M")
                delay_seconds = (target_time - now).total_seconds()
                remind_content = raw_text.replace(abs_match.group(1), "").strip()
            except: pass
        elif today_time_match and not abs_match:
            try:
                time_str = today_time_match.group(1)
                target_time = datetime.strptime(f"{now.strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %H:%M")
                # 如果设定的时间已经过了，默认指明天
                if target_time < now:
                    target_time += timedelta(days=1)
                delay_seconds = (target_time - now).total_seconds()
                remind_content = raw_text.replace(time_str, "").strip()
            except: pass

        if delay_seconds <= 0:
            yield event.plain_result(f"⏰ 时间解析失败或已过期 (当前系统时间: {now.strftime('%H:%M:%S')})")
            return

        user_name = event.get_sender_name()
        yield event.plain_result(f"✅ 设置成功！\n⏳ 将在 {int(delay_seconds)} 秒后提醒：{remind_content}")
        
        asyncio.create_task(self.execute_remind(event, delay_seconds, remind_content))

    async def execute_remind(self, event: AstrMessageEvent, delay: float, content: str):
        await asyncio.sleep(delay)
        try:
            chain = [At(qq=event.get_sender_id()), Plain(f"\n🔔 时间到！内容：{content}")]
            await event.send(event.chain_result(chain))
        except Exception as e:
            logger.error(f"提醒失败: {e}")
