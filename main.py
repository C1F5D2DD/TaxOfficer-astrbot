from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.message_components import *
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

import traceback
from data_process import *








@register("TaxOfficer", "c1f5d2dd", "记录群友搬的屎和交的税 - LLM驱动版", "2.0")
class TaxOfficer(Star):
    """
    群税官插件主类。

    核心功能：
    1. 监听群聊中所有带引用回复的消息，用 LLM 判断意图
       - 举报屎（report_shit）→ 被举报人欠税 +1
       - 交税（pay_tax）→ 清除一笔欠税
    2. LLM 同时验证被引用内容是否真的是屎
       - 是 → 被举报人欠税
       - 否（恶意举报）→ 举报人自己欠税
    3. 欠税 >2 条的人不能举报别人
    4. 纯图片消息直接走交税快捷路径，跳过 LLM
    5. 查询命令：/我、/查税 name
    """
    # ──────────────────────────────
    # 我的欠税
    # ──────────────────────────────

    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        self.plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        self.data=TaxDataManager(str(self.plugin_data_path))
        self.config=config
        self.resent_reports=[]

    @filter.command("我")
    async def my_debt(self, event: AstrMessageEvent,config: AstrBotConfig):
        uid = event.get_sender_id()
        name = event.get_sender_name()

        unpaid = self.data.get_unpaid_debts(uid)
        if len(unpaid)==0:
            yield event.plain_result(f"✅ {name}，你现在清清白白，没有欠税～")
        yield event.plain_result(f"📊 {name}，你还有 {len(unpaid)} 条欠税未还：")

    # ──────────────────────────────
    # 查别人欠税
    # ──────────────────────────────

    @filter.command("查税")
    async def check_debt(self, event: AstrMessageEvent, name: str):
        """查询指定群友的欠税情况。

        Args:
            name(string): 群友昵称或名字
        """
        unpaid = self.data.find_debts_by_name(name)
        if len(unpaid) == 0:
            yield event.plain_result(f"✅ {name}现在清清白白，没有欠税～")
        yield event.plain_result(f"📊 {name}还有 {len(unpaid)} 条欠税未还：")

    # ──────────────────────────────
    # 监听所有消息，用 LLM 判断意图
    # ──────────────────────────────

    async def llm_judge_IS_Shit(self, provider_id: str, text) :
        prompt = f"""你是一个群聊消息分类器。请判断以下消息是不是恶心，反动，令人不适的内容

        {text}

        如果是,输出yes。
        如果不是，输出no。
        不要输出任何其它内容。
        """
        try:
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
            )
            return llm_resp.completion_text.strip().lower()== "yes"
        except Exception as e:
            logger.error(f"TaxOfficer LLM 出错: {e}")
            logger.error(traceback.format_exc())
        return None

    async def llm_judge_IS_Rreport(self, provider_id: str, text) :
        prompt = f"""你是一个群聊消息分类器。请判断以下消息的意图。
        只返回一个词，不要其他内容。

        用户消息（引用了一条消息）：{text}

        回答（三选一）：
          report — 用户在举报屎（令人不适的内容）
          pay  — 用户在交税
          other — 用户在干其他的
        """
        try:
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
            )
            return llm_resp.completion_text.strip().lower()
        except Exception as e:
            logger.error(f"TaxOfficer LLM 出错: {e}")
            logger.error(traceback.format_exc())
        return None

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        msg = event.get_messages()
        reply_comp = next((c for c in msg if isinstance(c, Reply)), None)
        if not reply_comp:
            return

        # 去重
        dedup_key = f"{event.get_message_str()}|{event.get_sender_id()}|{event.get_group_id()}"
        if dedup_key not in self.resent_reports:
            self.resent_reports.append(dedup_key)
            self.resent_reports.pop(0)
        else:
            return

        # 提取信息
        reporter_id = event.get_sender_id()
        reporter_name = event.get_sender_name() or f"用户{reporter_id}"
        bot_id = event.get_self_id()
        quoted_id = str(reply_comp.sender_id)
        quoted_name = reply_comp.sender_nickname or f"用户{quoted_id}"
        user_text = event.get_message_str()
        quoted_text = reply_comp.message_str or ""

        # 不能举报机器人
        if bot_id and quoted_id == str(bot_id):
            return

        # 引用的消息中的图片
        quoted_images = []
        if reply_comp.chain:
            for item in reply_comp.chain:
                if isinstance(item, Image):
                    url = item.url or item.file or ""
                    if url:
                        quoted_images.append(url)

        # 当前消息中的图片
        current_images = []
        for c in msg:
            if isinstance(c, Image):
                url = c.url or c.file or ""
                if url:
                    current_images.append(url)

        provider_id = await self.context.get_current_chat_provider_id(
            umo=event.unified_msg_origin
        )

        has_images = bool(current_images)
        plain_text = "".join(c.text for c in msg if isinstance(c, Plain))
        has_text = bool(plain_text.strip())

        # ── LLM 分类 ──


        result = await self.llm_judge_IS_Rreport(provider_id,user_text)
        if result=="other":
            return

        if result=="pay":

            self.data.pay_debt(quoted_id,quoted_name,quoted_text,quoted_images)
            debt_num = len(self.data.get_unpaid_debts(quoted_id))
            yield event.plain_result(
                f"🚨 交税成功！\n"
                f"📌 缴纳人：{quoted_name}\n"
                f"💩 内容：{quoted_text or '(无文本)'}\n"
                f"{'🖼️ 含罪证图片\n' if quoted_images else ''}"
                f"💰 {quoted_name} 当前欠税：{debt_num} 条"
            )

            # 欠税 >2 不能举报
        if len(self.data.get_unpaid_debts(reporter_id))>self.config.max_reporter_debts:
            yield event.plain_result(f"🚫 {reporter_name}，你欠税超过 {self.config.max_reporter_debts} 条，先交税再来举报！")

        is_shit =await self.llm_judge_IS_Shit(provider_id,quoted_text)
        if (not has_images and has_text and is_shit) or has_images:
            debt_num=len(self.data.get_unpaid_debts(quoted_id))
            if len<self.config.max_debts:
                self.data.add_debt(quoted_id,quoted_name,quoted_text,current_images,reporter_id, reporter_name)
                yield event.plain_result(
                    f"🚨 举报已立案！\n"
                    f"📌 嫌疑人：{quoted_name}\n"
                    f"💩 罪证：{quoted_text or '(无文本)'}\n"
                    f"{'🖼️ 含罪证图片\n' if quoted_images else ''}"
                    f"🚔 举报人：{reporter_name}\n"
                    f"💰 {quoted_name} 当前欠税：{debt_num+1} 条"
                )
            else:
                yield event.plain_result(f"{quoted_name}已经欠税{debt_num}条了，可怜可怜他")




