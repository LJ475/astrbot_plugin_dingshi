import asyncio
import re
from datetime import datetime, timedelta, timezone
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("simple_timer", "YourName", "时区最终修复版", "1.4.5")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        """发送 /定时 查看帮助"""
        yield event.plain_result(
            "🔔 定时提醒 (时区最终修复版)\n"
            "--------------------------\n"
            "1️⃣ 相对时间：/提醒我 10s 喝水\n"
            "2️⃣ 准确时间：/提醒我 22:30 睡觉\n"
            "3️⃣ 具体日期：/提醒我 2026-03-05 23:00 刷牙\n"
            "--------------------------\n"
            "💡 当前北京时间参考：\n" + 
            datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
        )

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        raw_text = event.message_str.replace("/提醒我", "").strip()
        if not raw_text:
            yield event.plain_result("❌ 请输入内容，例如：/提醒我 10s 喝水")
            return

        # --- 核心：彻底锁定北京时间 ---
        tz_bj = timezone(timedelta(hours=8))
        # 获取当前最准确的 UTC 时间，并转化为北京时间
        now_bj = datetime.now(timezone.utc).astimezone(tz_bj)
        
        delay_seconds = 0
        remind_content = ""

        # 正则解析
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        abs_match = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})", raw_text) # 优化了空格匹配
        today_match = re.search(r"(\d{2}:\d{2})", raw_text)

        try:
            if rel_match:
                # 1. 相对时间解析
                value = int(rel_match.group(1))
                unit = rel_match.group(2)
                unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
                delay_seconds = value * unit_map.get(unit, 1)
                remind_content = raw_text.replace(rel_match.group(0), "").strip()
                
            elif abs_match:
                # 2. 具体日期时间解析 (2026-03-05 22:30)
                date_part = abs_match.group(1)
                time_part = abs_match.group(2)
                # 先解析为无时区对象
                dt_naive = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M")
                # 重新构造并强制注入北京时区 (避免 replace 的某些兼容性问题)
                target = datetime(dt_naive.year, dt_naive.month, dt_naive.day, 
                                 dt_naive.hour, dt_naive.minute, tzinfo=tz_bj)
                delay_seconds = (target - now_bj).total_seconds()
                remind_content = raw_text.replace(abs_match.group(0), "").strip()
                
            elif today_match:
                # 3. 仅时间解析 (22:30)
                time_str = today_match.group(1)
                t_parts = time_str.split(":")
                # 构造今日的目标北京时间
                target = datetime(now_bj.year, now_bj.month, now_bj.day, 
                                 int(t_parts[0]), int(t_parts[1]), tzinfo=tz_bj)
                
                # 如果时间已经过了，则设定为明天
                if target < now_bj:
                    target += timedelta(days=1)
                
                delay_seconds = (target - now_bj).total_seconds()
                remind_content = raw_text.replace(time_str, "").strip()

        except Exception as e:
            logger.error(f"解析时间出错: {e}")
            yield event.plain_result("❌ 时间格式解析出错，请检查输入。")
            return

        # 4. 最终校验
        if delay_seconds <= 0:
            yield event.plain_result(f"⚠️ 解析的时间已过。当前北京时间: {now_bj.strftime('%H:%M:%S')}")
            return

        # 限制最大延时 30 天
        if delay_seconds > 2592000:
            yield event.plain_result("❌ 提醒时间太长啦，请设置在 30 天以内。")
            return

        yield event.plain_result(f"✅ 设置成功！\n📅 提醒内容：{remind_content or '无'}\n⏳ 倒计时：{int(delay_seconds)} 秒")
        
        # 启动后台异步任务
        asyncio.create_task(self.do_remind(event, delay_seconds, remind_content))

    async def do_remind(self, event, delay, content):
        """执行具体的提醒逻辑"""
        await asyncio.sleep(delay)
        try:
            chain = [
                At(qq=event.get_sender_id()), 
                Plain(f"\n🔔 时间到！提醒内容：\n{content or '时间到啦！'}")
            ]
            await event.send(event.chain_result(chain))
        except Exception as e:
            logger.error(f"提醒推送失败: {e}")

    async def terminate(self):
        pass
