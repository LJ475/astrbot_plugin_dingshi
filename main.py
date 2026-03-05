import asyncio
import re
from datetime import datetime, timedelta, timezone
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("simple_timer", "YourName", "时区修复版定时", "1.4.3")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        guide_text = (
            "🔔 定时提醒使用说明 (已自动校准北京时间)\n"
            "--------------------------\n"
            "1️⃣ 相对时间：/提醒我 10s 喝水\n"
            "2️⃣ 当天时间：/提醒我 22:30 睡觉\n"
            "3️⃣ 具体日期：/提醒我 2026-03-05 23:00 刷牙\n"
            "--------------------------\n"
            "💡 发送后请检查机器人回复的倒计时秒数。"
        )
        yield event.plain_result(guide_text)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        raw_text = event.message_str.replace("/提醒我", "").strip()
        if not raw_text:
            yield event.plain_result("❌ 格式：/提醒我 10s 内容")
            return

        # --- 核心：强制使用北京时间 (UTC+8) 计算 ---
        tz_beijing = timezone(timedelta(hours=8))
        now_beijing = datetime.now(timezone.utc).astimezone(tz_beijing)
        
        delay_seconds = 0
        remind_content = ""

        # 1. 解析相对时间
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        # 2. 解析年月日 (2026-03-05 22:30)
        abs_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", raw_text)
        # 3. 解析纯时间 (22:30)
        today_match = re.search(r"(\d{2}:\d{2})", raw_text)

        if rel_match:
            value, unit = int(rel_match.group(1)), rel_match.group(2)
            unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
            delay_seconds = value * unit_map.get(unit, 1)
            remind_content = raw_text.replace(rel_match.group(0), "").strip()
            
        elif abs_match:
            try:
                target = datetime.strptime(abs_match.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=tz_beijing)
                delay_seconds = (target - now_beijing).total_seconds()
                remind_content = raw_text.replace(abs_match.group(1), "").strip()
            except: pass
            
        elif today_match:
            try:
                time_str = today_match.group(1)
                target = datetime.strptime(f"{now_beijing.strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=tz_beijing)
                if target < now_beijing: target += timedelta(days=1) # 如果时间过了就定明天
                delay_seconds = (target - now_beijing).total_seconds()
                remind_content = raw_text.replace(time_str, "").strip()
            except: pass

        if delay_seconds <= 0:
            yield event.plain_result(f"⚠️ 解析失败。当前北京时间: {now_beijing.strftime('%H:%M')}")
            return

        yield event.plain_result(f"✅ 设置成功！\n⏳ 将在 {int(delay_seconds)} 秒后提醒。")
        asyncio.create_task(self.do_remind(event, delay_seconds, remind_content))

    async def do_remind(self, event, delay, content):
        await asyncio.sleep(delay)
        try:
            await event.send(event.chain_result([At(qq=event.get_sender_id()), Plain(f"\n🔔 提醒：{content or '时间到！'}")]))
        except Exception as e:
            logger.error(f"发送失败: {e}")
