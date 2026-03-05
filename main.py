import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("simple_timer", "YourName", "全通用定时提醒", "1.4.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 使用普通的 command 装饰器。用户输入 /定时 也能看到帮助
    @filter.command("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        """发送 /定时 获取使用帮助"""
        user_name = event.get_sender_name()
        guide_text = (
            f"🔔 {user_name}，欢迎使用定时功能！\n"
            "--------------------------\n"
            "请按照以下格式输入指令：\n\n"
            "1️⃣ 快速提醒：\n"
            "   /提醒我 10s 喝水\n"
            "   /提醒我 5m 休息一下\n\n"
            "2️⃣ 精确时间：\n"
            "   /提醒我 2026-03-05 22:30 睡觉\n"
            "--------------------------\n"
            "💡 直接发送对应指令即可设置。"
        )
        yield event.plain_result(guide_text)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        # 提取指令后的内容
        raw_text = event.message_str.replace("/提醒我", "").strip()
        
        if not raw_text:
            yield event.plain_result("❌ 请输入内容！例如：/提醒我 10s 喝水")
            return

        delay_seconds = 0
        remind_content = ""

        # 正则解析逻辑
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        abs_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", raw_text)

        if rel_match:
            value = int(rel_match.group(1))
            unit = rel_match.group(2)
            unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
            delay_seconds = value * unit_map.get(unit, 1)
            remind_content = raw_text.replace(rel_match.group(0), "").strip()
        elif abs_match:
            time_str = abs_match.group(1)
            try:
                target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                delay_seconds = (target_time - datetime.now()).total_seconds()
                remind_content = raw_text.replace(time_str, "").strip()
            except ValueError:
                yield event.plain_result("❌ 日期格式不对，请按 YYYY-MM-DD HH:MM 输入")
                return
        else:
            yield event.plain_result("⚠️ 格式没认出来。发送 /定时 查看正确格式。")
            return

        if delay_seconds <= 0:
            yield event.plain_result("⏰ 这个时间已经过去啦！")
            return

        user_name = event.get_sender_name()
        yield event.plain_result(f"✅ 设置成功！将在 {int(delay_seconds)} 秒后提醒：{remind_content}")
        
        # 启动后台异步任务
        asyncio.create_task(self.execute_remind(event, delay_seconds, remind_content))

    async def execute_remind(self, event: AstrMessageEvent, delay: float, content: str):
        """倒计时结束后执行提醒"""
        await asyncio.sleep(delay)
        try:
            # 这里的 event.send 是最安全的推送方式
            chain = [
                At(qq=event.get_sender_id()), 
                Plain(f"\n🔔 时间到！提醒内容：\n{content}")
            ]
            await event.send(event.chain_result(chain))
        except Exception as e:
            logger.error(f"提醒推送失败: {e}")

    async def terminate(self):
        pass
