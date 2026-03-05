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
        # 1. 获取指令后的纯文本并去除首尾空格
        raw_text = event.message_str.replace("/提醒我", "").strip()
        
        if not raw_text:
            yield event.plain_result("💡 格式错误！试试：\n/提醒我 10s 喝水\n/提醒我 2026-03-05 22:00 睡觉")
            return

        delay_seconds = 0
        remind_content = ""

        # 2. 尝试解析【相对时间】：匹配 10s, 5m, 1h 等
        # \d+ 匹配数字，[smh秒分时] 匹配单位
        relative_pattern = r"(\d+)([smh秒分时])"
        rel_match = re.search(relative_pattern, raw_text)

        if rel_match:
            value = int(rel_match.group(1))
            unit = rel_match.group(2)
            unit_map = {'s': 1, '秒': 1, 'm': 60, '分': 60, 'h': 3600, '时': 3600}
            delay_seconds = value * unit_map.get(unit, 1)
            # 把时间部分删掉，剩下的就是提醒内容
            remind_content = raw_text.replace(rel_match.group(0), "").strip()
        
        # 3. 如果不是相对时间，尝试解析【年月日】
        else:
            # 匹配 2026-03-05 20:00 这种格式
            abs_pattern = r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})"
            abs_match = re.search(abs_pattern, raw_text)
            if abs_match:
                time_str = abs_match.group(1)
                try:
                    target_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
                    delay_seconds = (target_time - datetime.now()).total_seconds()
                    remind_content = raw_text.replace(time_str, "").strip()
                except ValueError:
                    yield event.plain_result("❌ 日期格式不对，请按 YYYY-MM-DD HH:MM 格式输入")
                    return
            else:
                yield event.plain_result("🤔 我没听懂时间，请用 '10s' 或 '2026-03-05 20:00' 这种格式")
                return

        # 4. 逻辑校验
        if not remind_content: remind_content = "时间到啦！"
        if delay_seconds <= 0:
            yield event.plain_result("⏰ 这个时间已经过去了哦！")
            return

        # 5. 执行提醒
        user_name = event.get_sender_name()
        yield event.plain_result(f"✅ 好的 {user_name}，已开启倒计时，提醒内容：{remind_content}")
        
        await asyncio.sleep(delay_seconds)
        yield event.plain_result(f"🔔 {user_name}，提醒时间到！\n内容：{remind_content}")
