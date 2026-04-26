import os
import json
import time
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Reply, BaseMessageComponent,Image

class ShitTaxPlugin(Star):
    """
    屎税管理插件
    命令：
    - /屎（引用消息）：记录被引用消息为“屎”，并增加发送该消息的群友欠税次数。
    - /税（引用图片或消息含图）：交税，抵扣一次欠税，并保存税图。
    """
    def __init__(self, context: Context):
        super().__init__(context)
        # 1. 数据文件存储在插件的 data 目录下
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.shit_file = os.path.join(self.data_dir, "shit_tax.json")
        self.data = self.load_data()

    def load_data(self):
        # ... (数据加载逻辑保持不变)
        pass

    def save_data(self):
        # ... (数据保存逻辑保持不变)
        pass

    def get_reply_message_obj(self, event: AstrMessageEvent):
        msg_obj = event.message_obj
        if not msg_obj:
            return None
        for comp in msg_obj.message:
            # 根据调试输出，确认类名。暂时保留 Reply
            if isinstance(comp, Reply):
                # 尝试多种已知属性名
                return (getattr(comp, 'message', None) or
                        getattr(comp, 'reply', None) or
                        getattr(comp, 'reply_message', None))
        return None

    def extract_image(self, message_chain):
        """从消息链中提取第一张图片的路径或URL"""
        for comp in message_chain:
            if isinstance(comp, Image):
                return comp.data.get("url") or comp.data.get("file")
        return None

    @filter.command("屎")
    async def record_shit(self, event: AstrMessageEvent):
        """记录搬屎"""
        # 1. 获取被引用的消息
        reply_message = self.get_reply_message_obj(event)
        if not reply_message:
            yield event.plain_result("请引用一条你认为的“屎”消息再使用此命令。")
            return

        # 2. 获取被引用消息的发送者
        target_sender = reply_message.sender  # sender 是 MessageMember 对象
        target_id = target_sender.user_id if target_sender else None
        if not target_id:
            yield event.plain_result("无法获取被引用消息的发送者，记录失败。")
            return

        # 3. 获取屎的内容
        shit_content = reply_message.message_str  # 纯文本内容
        shit_image = self.extract_image(reply_message.message)  # 第一张图片

        if not shit_content and not shit_image:
            yield event.plain_result("被引用的消息中没有文本或图片，无法记录。")
            return

        # 4. 记录
        group_id = event.message_obj.group_id
        new_tax = self.add_tax(group_id, target_id)

        record = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "group_id": group_id,
            "shitter_id": target_id,
            "reporter_id": event.get_sender_id(),
            "content": shit_content,
            "image": shit_image
        }
        self.data["shit_records"].append(record)
        self.save_data()

        target_name = target_sender.nickname if target_sender and target_sender.nickname else f"用户{target_id}"
        yield event.plain_result(f"记录成功！{target_name} 的“屎”已被存档，当前欠税 {new_tax} 次。")

    @filter.command("税")
    async def pay_tax(self, event: AstrMessageEvent):
        """交税"""
        # 1. 获取图片：优先从引用消息中获取，否则从当前消息获取
        tax_image = None
        reply_message = self.get_reply_message_obj(event)
        if reply_message:
            tax_image = self.extract_image(reply_message.message)
        if not tax_image:
            tax_image = self.extract_image(event.message_obj.message)

        if not tax_image:
            yield event.plain_result("请引用含税图片的消息，或在本消息中附带图片。")
            return

        # 2-5. 与之前类似的处理逻辑
        # ...
        pass