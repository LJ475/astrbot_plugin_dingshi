import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("simple_timer", "YourName", "全通用定时提醒", "1.4.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 当用户输入“定时”时，触发“模拟弹窗”引导
    @filter.on_keyword("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        user_name = event.get_sender_name()
        guide_text = (
            f"🔔 {user_name}，欢迎使用定时功能！\n"
            "--------------------------\n"
            "请复制下方指令并修改内容：\n\n"
            "1️⃣ 快速提醒：\n"
            "   /提醒我 10s 喝水\n"
            "   /提醒我 5m 休息一下\n\n"
            "2️⃣ 精确时间（年月日）：\n"
            "   /提醒我 2026-03-05 22:30 睡觉\n"
            "--------------------------\n"
            "💡 直接发送指令即可设置。"
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

        # 正则解析：相对时间 (数字 + s/m/h/秒/分/时)
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        # 正则解析：绝对时间 (YYYY-MM-DD HH:MM)
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
            yield event.plain_result("⚠️ 格式没认出来，请参考‘定时’说明。")
            return

        if delay_seconds <= 0:
            yield event.plain_result("⏰ 这个时间已经过去啦！")
            return

        user_name = event.get_sender_name()
        yield event.plain_result(f"✅ 设置成功！将在 {int(delay_seconds)} 秒后提醒：{remind_content}")
        
        # 核心：启动后台异步倒计时
        asyncio.create_task(self.execute_remind(event, delay_seconds, remind_content))

    async def execute_remind(self, event: AstrMessageEvent, delay: float, content: str):
        """倒计时结束后执行提醒"""
        await asyncio.sleep(delay)
        try:
            # 构造包含 @用户 的消息链
            chain = [
                At(qq=event.get_sender_id()), 
                Plain(f"\n🔔 时间到！提醒内容：\n{content}")
            ]
            # 使用 event.send 确保消息发送成功
            await event.send(event.chain_result(chain))
        except Exception as e:
            logger.error(f"提醒推送失败: {e}")

    async def terminate(self):
        pass
