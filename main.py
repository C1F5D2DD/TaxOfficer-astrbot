from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.message_components import *
from astrbot.api import logger
import json
import os
import uuid
import time
import traceback
# 去重缓存：记录最近处理过的消息ID列表
_PROCESSED_IDS = []
_MAX_CACHE = 50

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tax_data.json")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"debts": [], "payments": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@register("TaxOfficer", "c1f5d2dd", "记录群友搬的屎和交的税 - LLM驱动版", "2.0")
class TaxOfficer(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data = load_data()

    async def initialize(self):
        logger.info(f"TaxOfficer 已加载，当前欠税记录：{len(self.data['debts'])} 条")

    async def terminate(self):
        save_data(self.data)

    # ──────────────────────────────
    # 监听所有消息，用 LLM 判断意图
    # ──────────────────────────────

    # ── 去重 ──
    def _is_duplicate(self, msg_id: str) -> bool:
        global _PROCESSED_IDS
        if msg_id in _PROCESSED_IDS:
            return True
        _PROCESSED_IDS.append(msg_id)
        if len(_PROCESSED_IDS) > _MAX_CACHE:
            _PROCESSED_IDS = _PROCESSED_IDS[-_MAX_CACHE:]
        return False

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        # 只处理包含引用回复的消息
        msg = event.get_messages()
        reply_comp = None
        for comp in msg:
            if isinstance(comp, Reply):
                reply_comp = comp
                break
        if not reply_comp:
            return

        # 去重：防止 @bot 多次导致重复处理
        dedup_key = f"{event.get_message_str()}|{event.get_sender_id()}|{event.get_group_id()}"
        if self._is_duplicate(dedup_key):
            return

        # 不能举报机器人自己
        bot_id = event.get_self_id()
        if bot_id and str(reply_comp.sender_id) == str(bot_id):
            return

        # 提取消息文本和图片
        user_text = event.get_message_str()
        quoted_text = reply_comp.message_str or ""

        current_images = []
        for comp in msg:
            if isinstance(comp, Image):
                url = comp.url or comp.file or ""
                if url:
                    current_images.append(url)

        # 获取当前 LLM 提供商 ID
        provider_id = await self.context.get_current_chat_provider_id(
            umo=event.unified_msg_origin
        )

        # ── 图片交税快捷路径 ──
        # 如果用户发了图片但没写什么文字（或只有@），直接判定为交税
        has_images = bool(current_images)
        # 只检查 Plain 组件中的文字（排除 @ 等自动生成的文本）
        plain_text = "".join(c.text for c in msg if isinstance(c, Plain))
        has_text = bool(plain_text.strip())
        if has_images and not has_text:
            response = await self._handle_payment(
                event, reply_comp, user_text, current_images
            )
            if response:
                yield event.plain_result(response)
            return

        # ── 调用 LLM 判断意图 ──
        prompt = f"""你是一个群聊消息分类器，只负责判断以下用户消息的意图。

用户发送的消息（引用了一条之前的消息）：{user_text}
{'用户还附带了图片' if has_images else ''}

请判断这条消息是否属于以下两类之一，只返回 JSON：

1. "report_shit" — 用户在举报"屎"。用户引用了一条消息，并用自然语言表达"这是屎"、"举报"、"这太离谱了"、"绷不住了"等含义，指责被引用消息内容不当。
2. "pay_tax" — 用户在"交税"。用户引用了一条消息，并用自然语言表达"交税"、"纳税"、"上税"、"交罚款"等含义，通常还会附带图片作为"税"的内容。

返回格式（只返回 JSON，不要其他内容）：
- 举报屎：{{"intent": "report_shit", "reason": "简要判断理由"}}
- 交税：{{"intent": "pay_tax", "reason": "简要判断理由"}}
- 都不是：{{"intent": "none", "reason": ""}}"""

        try:
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
            )
            result_text = llm_resp.completion_text.strip()

            # 尝试从 LLM 回复中提取 JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            result = json.loads(result_text)
            intent = result.get("intent", "none")

            if intent == "report_shit":
                response = await self._handle_report(event, reply_comp, quoted_text)
                yield event.plain_result(response)
            elif intent == "pay_tax":
                response = await self._handle_payment(
                    event, reply_comp, user_text, current_images
                )
                yield event.plain_result(response)

        except json.JSONDecodeError:
            logger.warning(
                f"TaxOfficer LLM 返回非 JSON: {llm_resp.completion_text[:200]}"
            )
        except Exception as e:
            logger.error(f"TaxOfficer LLM 分类出错: {e}")
            logger.error(traceback.format_exc())

    # ──────────────────────────────
    # 处理举报屎
    # ──────────────────────────────

    async def _handle_report(self, event, reply_comp, quoted_text):
        shitter_id = str(reply_comp.sender_id)
        shitter_name = reply_comp.sender_nickname or f"用户{shitter_id}"
        reporter_id = event.get_sender_id()
        reporter_name = event.get_sender_name() or f"用户{reporter_id}"

        # 收集引用消息中的图片
        shit_images = []
        if reply_comp.chain:
            for item in reply_comp.chain:
                if isinstance(item, Image):
                    url = item.url or item.file or ""
                    if url:
                        shit_images.append(url)

        # 创建欠税记录
        debt = {
            "id": str(uuid.uuid4()),
            "shitter_id": shitter_id,
            "shitter_name": shitter_name,
            "shit_text": quoted_text,
            "shit_images": shit_images,
            "reporter_id": reporter_id,
            "reporter_name": reporter_name,
            "timestamp": time.time(),
            "paid": False,
        }
        self.data["debts"].append(debt)
        save_data(self.data)

        # 统计该用户未还欠税
        unpaid = sum(
            1
            for d in self.data["debts"]
            if d["shitter_id"] == shitter_id and not d["paid"]
        )

        response = (
            f"🚨 举报已立案！\n"
            f"📌 嫌疑人：{shitter_name}\n"
            f"💩 罪证：{quoted_text or '(无文本)'}\n"
            f"{'🖼️ 含罪证图片\n' if shit_images else ''}"
            f"🚔 举报人：{reporter_name}\n"
            f"💰 当前欠税：{unpaid} 条"
        )
        return response

    # ──────────────────────────────
    # 处理交税
    # ──────────────────────────────

    async def _handle_payment(self, event, reply_comp, user_text, current_images):
        payer_id = event.get_sender_id()
        payer_name = event.get_sender_name() or f"用户{payer_id}"

        # 查找该用户未还的欠税（先还最早的）
        unpaid_debts = [
            d
            for d in self.data["debts"]
            if d["shitter_id"] == payer_id and not d["paid"]
        ]

        if not unpaid_debts:
            return f"✅ {payer_name}，你现在一身清白，没有欠税～"

        # 还最早的债
        debt_paid = unpaid_debts[0]
        debt_paid["paid"] = True

        payment = {
            "id": str(uuid.uuid4()),
            "debt_id": debt_paid["id"],
            "payer_id": payer_id,
            "payer_name": payer_name,
            "tax_text": user_text,
            "tax_images": current_images,
            "timestamp": time.time(),
        }
        self.data["payments"].append(payment)
        save_data(self.data)

        remaining = sum(
            1
            for d in self.data["debts"]
            if d["shitter_id"] == payer_id and not d["paid"]
        )

        response = (
            f"💰 收税成功！\n"
            f"🙋 纳税人：{payer_name}\n"
            f"📝 抵税条目：{debt_paid['shit_text'] or '(无文本)'}\n"
            f"{'🖼️ 税图已入库\n' if current_images else ''}"
            f"📊 剩余欠税：{remaining} 条"
        )
        return response


