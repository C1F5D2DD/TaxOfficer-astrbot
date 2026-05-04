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
# ── 去重缓存 ──
# 存储最近处理过的消息特征键值，防止同一条消息因多次 @bot 等原因被重复处理。
# _PROCESSED_IDS 是列表实现的 FIFO 队列，_MAX_CACHE 控制最大缓存数量。
_PROCESSED_IDS = []
_MAX_CACHE = 50

# ── 数据文件路径 ──
# JSON 文件存放在插件目录下，与 main.py 同级。
# 数据结构：
#   debts[]    — 欠税记录列表，每条记录包含 shitter(欠税人)、reporter(举报人)、shit 内容等
#   payments[] — 交税记录列表，每条记录包含 payer(交税人)、对应的 debt_id、税的内容等
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tax_data.json")


def load_data():
    """
    从 JSON 文件加载持久化数据。
    如果文件不存在（首次运行），返回空的数据结构。
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"debts": [], "payments": []}


def save_data(data):
    """
    将当前数据持久化保存到 JSON 文件。
    ensure_ascii=False 确保中文正常显示，indent=2 格式化便于阅读。
    每次增删改后都调用此函数，保证数据不丢失。
    """
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@register("TaxOfficer", "c1f5d2dd", "记录群友搬的屎和交的税 - LLM驱动版", "2.0")
class TaxOfficer(Star):
    """
    群税官插件主类。

    核心功能：
    1. 监听群聊中所有带引用回复的消息，用 LLM 判断是否在
    """
    # ──────────────────────────────
    # 我的欠税
    # ──────────────────────────────

    @filter.command("我")
    async def my_debt(self, event: AstrMessageEvent):
        uid = event.get_sender_id()
        name = event.get_sender_name()

        unpaid = [d for d in self.data["debts"] if d["shitter_id"] == uid and not d["paid"]]
        total = len([d for d in self.data["debts"] if d["shitter_id"] == uid])

        if not unpaid:
            yield event.plain_result(f"✅ {name}，你现在清清白白，没有欠税～（历史共 {total} 条）")
            return

        lines = [f"📊 {name}，你还有 {len(unpaid)} 条欠税未还："]
        for i, d in enumerate(unpaid, 1):
            text = d["shit_text"] or "(无文本)"
            lines.append(f"  {i}. {text[:30]}{'...' if len(text) > 30 else ''}")
        lines.append(f"📌 共 {total} 条记录")
        yield event.plain_result("\n".join(lines))

    # ──────────────────────────────
    # 查别人欠税
    # ──────────────────────────────

    @filter.command("查税")
    async def check_debt(self, event: AstrMessageEvent, name: str):
        """查询指定群友的欠税情况。

        Args:
            name(string): 群友昵称或名字
        """
        debts = [d for d in self.data["debts"] if d["shitter_name"] == name or name in d["shitter_name"]]

        if not debts:
            yield event.plain_result(f"🔍 没找到 {name} 的欠税记录～")
            return

        unpaid = [d for d in debts if not d["paid"]]
        paid = [d for d in debts if d["paid"]]

        lines = [f"🔍 {name} 的税务记录："]
        if unpaid:
            lines.append(f"\n❌ 未还欠税（{len(unpaid)} 条）：")
            for i, d in enumerate(unpaid, 1):
                text = d["shit_text"] or "(无文本)"
                lines.append(f"  {i}. {text[:30]}{'...' if len(text) > 30 else ''}")
        else:
            lines.append("\n✅ 暂无未还欠税")

        if paid:
            lines.append(f"\n✅ 已交税（{len(paid)} 条）")

        lines.append(f"\n📊 总计：{len(debts)} 条 | 未还：{len(unpaid)} 条 | 已还：{len(paid)} 条")
        yield event.plain_result("\n".join(lines))

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

    def _unpaid_count(self, uid: str) -> int:
        return sum(1 for d in self.data["debts"] if d["shitter_id"] == uid and not d["paid"])

    def _record_debt(self, shitter_id: str, shitter_name: str, shit_text: str,
                     shit_images: list, reporter_id: str, reporter_name: str) -> dict:
        debt = {
            "id": str(uuid.uuid4()),
            "shitter_id": shitter_id,
            "shitter_name": shitter_name,
            "shit_text": shit_text,
            "shit_images": shit_images,
            "reporter_id": reporter_id,
            "reporter_name": reporter_name,
            "timestamp": time.time(),
            "paid": False,
        }
        self.data["debts"].append(debt)
        save_data(self.data)
        return debt

    def _count_remaining(self, uid: str) -> int:
        return sum(1 for d in self.data["debts"] if d["shitter_id"] == uid and not d["paid"])

    async def _call_llm_json(self, provider_id: str, prompt: str) -> dict | None:
        try:
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=prompt,
            )
            text = llm_resp.completion_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"TaxOfficer LLM 返回非 JSON: {text[:200]}")
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
        if self._is_duplicate(dedup_key):
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

        # ── 图片交税快捷路径 ──
        if has_images and not has_text:
            resp = await self._handle_payment(event, reply_comp, user_text, current_images)
            if resp:
                yield event.plain_result(resp)
            return

        # ── LLM 分类 ──
        prompt = f"""你是一个群聊消息分类器。

用户消息（引用了一条消息）：{user_text}
被引用消息内容：{quoted_text}
{'用户还附带了图片' if has_images else ''}

请分析用户意图，只返回 JSON：

1. "report_shit" — 用户举报"屎"，表达这是屎、举报等含义。
   如果是举报屎，请同时判断：被引用的内容真的是屎（不合适/精神污染）吗？
2. "pay_tax" — 用户"交税"，表达交税、纳税、上税、交罚款等含义。
3. "none" — 都不是。

返回格式：
- 举报屎且内容确实是屎：{{"intent": "report_shit", "is_valid": true, "reason": "理由"}}
- 举报屎但内容不是屎（恶意举报）：{{"intent": "report_shit", "is_valid": false, "reason": "理由"}}
- 交税：{{"intent": "pay_tax", "is_valid": true, "reason": "理由"}}
- 都不是：{{"intent": "none", "is_valid": true, "reason": ""}}"""

        result = await self._call_llm_json(provider_id, prompt)
        if not result:
            return

        intent = result.get("intent", "none")
        is_valid = result.get("is_valid", True)

        if intent == "report_shit":
            # 欠税 >2 不能举报
            if self._unpaid_count(reporter_id) > 2:
                yield event.plain_result(f"🚫 {reporter_name}，你欠税超过 2 条，先交税再来举报！")
                return

            if is_valid:
                # 确实在举报屎 → 被举报人欠税
                debt = self._record_debt(
                    quoted_id, quoted_name, quoted_text, quoted_images,
                    reporter_id, reporter_name
                )
                remaining = self._count_remaining(quoted_id)
                yield event.plain_result(
                    f"🚨 举报已立案！\n"
                    f"📌 嫌疑人：{quoted_name}\n"
                    f"💩 罪证：{quoted_text or '(无文本)'}\n"
                    f"{'🖼️ 含罪证图片\n' if quoted_images else ''}"
                    f"🚔 举报人：{reporter_name}\n"
                    f"💰 {quoted_name} 当前欠税：{remaining} 条"
                )
            else:
                # 恶意举报 → 举报人自己交税
                debt = self._record_debt(
                    reporter_id, reporter_name,
                    f"[恶意举报] 举报了 {quoted_name} 的消息：{quoted_text or '(无文本)'}",
                    [], reporter_id, reporter_name
                )
                remaining = self._count_remaining(reporter_id)
                yield event.plain_result(
                    f"⚠️ 经鉴定，{quoted_name} 的内容不是屎，属于恶意举报！\n"
                    f"📌 {reporter_name}，你被罚款了！\n"
                    f"💰 你当前欠税：{remaining} 条"
                )

        elif intent == "pay_tax":
            resp = await self._handle_payment(event, reply_comp, user_text, current_images)
            if resp:
                yield event.plain_result(resp)

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


