import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("advanced_timer", "YourName", "按钮交互式定时提醒", "1.3.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 监听用户输入“定时”两个字
    @filter.on_keyword("定时")
    async def timer_popup(self, event: AstrMessageEvent):
        """当用户发送‘定时’时，发送交互式引导消息"""
        user_name = event.get_sender_name()
        
        # 这里构造一个“模拟弹窗”的按钮消息
        # 在大多数平台上，这会以带链接或指令按钮的形式展现
        yield event.chain_result([
            Plain(f"你好 {user_name}！请选择提醒时间：\n\n"),
            Plain("🕒 快速选择：\n"),
            Plain("1️⃣ [10秒后提醒] -> 发送：/提醒我 10s 喝水\n"),
            Plain("2️⃣ [1分钟后提醒] -> 发送：/提醒我 1m 休息一下\n"),
            Plain("3️⃣ [1小时后提醒] -> 发送：/提醒我 1h 准备开会\n\n"),
            Plain("💡 或者直接输入具体日期，例如：\n/提醒我 2026-03-05 22:30 睡觉")
        ])

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        raw_text = event.message_str.replace("/提醒我", "").strip()
        
        if not raw_text:
            yield event.plain_result("🤔 你没告诉我内容呢！示例：/提醒我 10s 喝水")
            return

        delay_seconds = 0
        remind_content = ""

        # 时间解析逻辑
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
            yield event.plain_result("⚠️ 格式没认出来。试试：/提醒我 10s 喝水")
            return

        if delay_seconds <= 0:
            yield event.plain_result("⏰ 这个时间已经过去啦！")
            return

        yield event.plain_result(f"✅ 设置成功！将在 {int(delay_seconds)} 秒后提醒：{remind_content}")
        
        # 启动后台任务
        asyncio.create_task(self.do_remind(event, delay_seconds, remind_content))

    async def do_remind(self, event: AstrMessageEvent, delay: float, content: str):
        await asyncio.sleep(delay)
        try:
            # 最终提醒：艾特用户并播报内容
            chain = [
                At(qq=event.get_sender_id()), 
                Plain(f"\n🔔 时间到！你之前交待的事：\n📝 {content}")
            ]
            await event.send(event.chain_result(chain))
        except Exception as e:
            logger.error(f"发送提醒失败: {e}")

    async def terminate(self):
        pass
