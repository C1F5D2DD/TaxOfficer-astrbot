from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.message_components import Reply

@register("TexOfficer", "c1f5d2dd", "记录群友搬的屎和交的税", "1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("屎")
    async def record_shit(self, event: AstrMessageEvent):
        msg = event.message_obj.message
        print(msg)
        # 1. 查找 Reply 组件
        reply_comp = None
        for comp in msg:
            if isinstance(comp, Reply):
                reply_comp = comp
                break

        if not reply_comp:
            yield event.plain_result("请引用一条消息再使用 /屎 命令。")
            return

        # 2. 提取被引用消息的文本
        shit_text = reply_comp.message_str or ""

        # 3. 提取被引用消息中的第一张图片
        img_url = None
        if reply_comp.chain:
            for item in reply_comp.chain:
                if isinstance(item, Image):
                    # Image 的 data 字段通常包含 url 或 file
                    img_url = item.data.get("url") or item.data.get("file")
                    if img_url:
                        break

        # 4. 构造回复
        target_id = reply_comp.sender_id
        target_name = reply_comp.sender_nickname or f"用户{target_id}"
        reporter_id = event.get_sender_id()
        reporter_name = event.get_sender_name()

        response = f"📌 被引用消息发送者：{target_name} ({target_id})\n"
        response += f"💩 屎内容：{shit_text or '(无文本)'}\n"
        if img_url:
            response += f"🖼️ 屎图：{img_url}\n"
        response += f"🚨 举报人：{reporter_name} ({reporter_id})"

        yield event.plain_result(response)


