import asyncio
import re
import uuid
from datetime import datetime, timedelta, timezone
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("advanced_multi_timer", "YourName", "多任务强化版定时器", "1.5.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 如果需要实现机器人重启后提醒不丢失，后续可在此处引入持久化数据库

    @filter.command("定时")
    async def timer_guide(self, event: AstrMessageEvent):
        """发送 /定时 查看帮助"""
        tz_bj = timezone(timedelta(hours=8))
        curr_time = datetime.now(timezone.utc).astimezone(tz_bj).strftime("%Y-%m-%d %H:%M:%S")
        
        guide_text = (
            f"🔔 多任务定时提醒系统\n"
            f"--------------------------\n"
            f"1️⃣ 相对时间：/提醒我 30s 拿外卖\n"
            f"2️⃣ 当天时间：/提醒我 14:00 开会\n"
            f"3️⃣ 具体日期：/提醒我 2026-03-06 08:00 起床\n"
            f"--------------------------\n"
            f"💡 支持同时布置多个任务，互不干扰。\n"
            f"🕒 当前北京时间：{curr_time}"
        )
        yield event.plain_result(guide_text)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        raw_text = event.message_str.replace("/提醒我", "").strip()
        if not raw_text:
            yield event.plain_result("❌ 格式错误。示例：/提醒我 10s 喝水")
            return

        # --- 核心：北京时区锁定 ---
        tz_bj = timezone(timedelta(hours=8))
        now_bj = datetime.now(timezone.utc).astimezone(tz_bj)
        
        delay_seconds = 0
        remind_content = ""

        # 正则匹配规则
        rel_pattern = r"(\d+)([smh秒分时])"
        abs_pattern = r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})"
        today_pattern = r"(\d{2}:\d{2})"

        try:
            # 1. 优先匹配具体日期
            abs_match = re.search(abs_pattern, raw_text)
            rel_match = re.search(rel_pattern, raw_text)
            today_match = re.search(today_pattern, raw_text)

            if abs_match:
                dt_naive = datetime.strptime(f"{abs_match.group(1)} {abs_match.group(2)}", "%Y-%m-%d %H:%M")
                target = dt_naive.replace(tzinfo=tz_bj)
                delay_seconds = (target - now_bj).total_seconds()
                remind_content = raw_text.replace(abs_match.group(0), "").strip()

            elif rel_match:
                value, unit = int(rel_match.group(1)), rel_match.group(2)
                unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
                delay_seconds = value * unit_map.get(unit, 1)
                remind_content = raw_text.replace(rel_match.group(0), "").strip()

            elif today_match:
                t_parts = today_match.group(1).split(":")
                target = now_bj.replace(hour=int(t_parts[0]), minute=int(t_parts[1]), second=0, microsecond=0)
                if target < now_bj:
                    target += timedelta(days=1)
                delay_seconds = (target - now_bj).total_seconds()
                remind_content = raw_text.replace(today_match.group(1), "").strip()

            else:
                yield event.plain_result("⚠️ 未能识别时间格式，请发送 [/定时] 查看帮助。")
                return

        except Exception as e:
            logger.error(f"时间解析异常: {e}")
            yield event.plain_result("❌ 时间解析出错。")
            return

        # 校验
        if delay_seconds <= 0:
            yield event.plain_result(f"⏰ 时间已过！当前北京时间: {now_bj.strftime('%H:%M:%S')}")
            return
        
        if delay_seconds > 2592000: # 30天
            yield event.plain_result("❌ 提醒跨度不能超过30天。")
            return

        # 任务处理
        task_id = str(uuid.uuid4())[:8] # 生成短ID
        remind_content = remind_content if remind_content else "时间到啦！"
        user_name = event.get_sender_name()

        yield event.plain_result(
            f"✅ 任务已创建 [ID:{task_id}]\n"
            f"👤 用户：{user_name}\n"
            f"📅 内容：{remind_content}\n"
            f"⏳ 倒计时：{int(delay_seconds)} 秒"
        )
        
        # 核心：将任务丢入后台异步执行，互不阻塞
        asyncio.create_task(self.do_remind_task(event, delay_seconds, remind_content, task_id))

    async def do_remind_task(self, event: AstrMessageEvent, delay: float, content: str, task_id: str):
        """独立的后台提醒任务"""
        logger.info(f"任务 {task_id} 开始倒计时: {delay}秒")
        
        await asyncio.sleep(delay)
        
        try:
            # 再次检查环境并发送
            chain = [
                At(qq=event.get_sender_id()), 
                Plain(f"\n🔔 提醒(ID:{task_id})：\n{content}")
            ]
            await event.send(event.chain_result(chain))
            logger.info(f"任务 {task_id} 提醒成功")
        except Exception as e:
            logger.error(f"任务 {task_id} 推送失败: {e}")

    async def terminate(self):
        # 插件卸载时的处理逻辑
        pass
