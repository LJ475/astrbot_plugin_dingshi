import asyncio
import re
from datetime import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *

@register("advanced_timer", "YourName", "增强版定时提醒", "1.2.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("提醒我")
    async def timer_command(self, event: AstrMessageEvent):
        # 1. 获取指令后的纯文本
        raw_text = event.message_str.replace("/提醒我", "").strip()
        
        # 如果用户只发了 "/提醒我"，弹出快捷选项（按钮形式）
        if not raw_text:
            yield event.chain_result([
                Plain("💡 想要我什么时候提醒你？\n格式：/提醒我 10s 喝水\n\n"),
                # 下面是模拟按钮逻辑，如果平台支持会显示为按钮，不支持则为纯文本
                Plain("快捷设置：\n"),
                Plain("👉 /提醒我 1m 喝水\n"),
                Plain("👉 /提醒我 10m 休息\n"),
                Plain("👉 /提醒我 1h 开会")
            ])
            return

        delay_seconds = 0
        remind_content = ""

        # 2. 尝试解析时间
        # 匹配相对时间 (10s, 5m, 1h)
        rel_match = re.search(r"(\d+)([smh秒分时])", raw_text)
        # 匹配绝对时间 (2026-03-05 22:00)
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
            yield event.plain_result("🤔 没听懂时间，请用 '10s' 或 '2026-03-05 20:00'")
            return

        # 3. 校验
        if not remind_content: remind_content = "时间到啦！"
        if delay_seconds <= 0:
            yield event.plain_result("⏰ 这个时间已经过去了哦！")
            return

        user_name = event.get_sender_name()
        
        # 4. 关键：保存当前的事件上下文，用于稍后主动推送
        # 这样即使 yield 失效了，主动推送也能发出去
        unified_msg_event = event.unified_msg_event 

        yield event.plain_result(f"✅ 好的 {user_name}，提醒已设置成功！\n📅 提醒内容：{remind_content}\n⏳ 倒计时：{int(delay_seconds)}秒")
        
        # 5. 异步等待
        await asyncio.sleep(delay_seconds)
        
        # 6. 使用 context 主动推送消息
        # 这种方式比 yield 更可靠，能穿透复杂的网络环境
        try:
            await self.context.send_message(unified_msg_event, [
                At(qq=event.get_sender_id()), # 艾特用户，增强弹窗提醒感
                Plain(f"\n🔔 提醒时间到！\n📝 内容：{remind_content}")
            ])
        except Exception as e:
            logger.error(f"提醒发送失败: {e}")

    async def terminate(self):
        pass
