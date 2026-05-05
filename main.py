from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.event.filter import EventMessageType
from astrbot.api.message_components import *
from astrbot.api import logger
from astrbot.api import AstrBotConfig
from pathlib import Path
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

import traceback









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
    5. 查询命令：/我、/查税 uid、/所有欠税
    """
    # ──────────────────────────────
    # 我的欠税
    # ──────────────────────────────

    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        if config.data_dir == "":
            self.plugin_data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
        else:
            self.plugin_data_path=config.data_dir
        self.data=TaxDataManager(str(self.plugin_data_path))
        self.config=config
        self.resent_reports=[]
        logger.info("INIT")

    @filter.command("我")
    async def my_debt(self, event: AstrMessageEvent):

        uid = event.get_sender_id()
        name = event.get_sender_name()
        logger.info(f"查税{uid}:{name}")
        unpaid = self.data.get_unpaid_debts(uid)
        if len(unpaid)==0:
            yield event.plain_result(f"✅ {name}，你现在清清白白，没有欠税～")
        yield event.plain_result(f"📊 {name}，你还有 {len(unpaid)} 条欠税未还：")

    # ──────────────────────────────
    # 查别人欠税
    # ──────────────────────────────

    @filter.command("查税")
    async def check_debt(self, event: AstrMessageEvent, uid: str):
        """查询指定群友的欠税情况。

        Args:
            uid(string): 群友的 UID
        """
        logger.info(f"查税 uid={uid}")
        unpaid = self.data.get_unpaid_debts(uid)
        if len(unpaid) == 0:
            yield event.plain_result(f"✅ 用户({uid})现在清清白白，没有欠税～")
            return
        name = unpaid[0].get("shitter_name", f"用户{uid}")
        yield event.plain_result(f"📊 {name}({uid})还有 {len(unpaid)} 条欠税未还：")

    # ──────────────────────────────
    # 全群欠税
    # ──────────────────────────────

    @filter.command("所有欠税")
    async def all_debts(self, event: AstrMessageEvent):
        """列出当前群聊所有人的欠税情况。"""
        logger.info(f"所有欠税")
        all_unpaid = self.data.list_all_unpaid_debts()
        if not all_unpaid:
            yield event.plain_result("✅ 所有人现在都清清白白，没有欠税～")
            return

        lines = ["📊 全群欠税清单：\n"]
        for uid, info in all_unpaid.items():
            lines.append(f"💰 {info['name']}({uid})：{info['count']} 条")
        lines.append(f"\n🔢 共 {len(all_unpaid)} 人欠税")

        yield event.plain_result("\n".join(lines))

    # ──────────────────────────────
    # 监听所有消息，用 LLM 判断意图
    # ──────────────────────────────

    async def llm_judge_IS_Shit(self, provider_id: str, text) :
        logger.info(f"llm_judge_IS_Shit:{text}")
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
            logger.info(f"llm_judge_IS_shit result:{llm_resp.completion_text.strip().lower()}")
            return llm_resp.completion_text.strip().lower()== "yes"
        except Exception as e:
            logger.error(f"TaxOfficer LLM 出错: {e}")
            logger.error(traceback.format_exc())
        return None

    async def llm_judge_IS_Rreport(self, provider_id: str, text) :
        logger.info(f"llm_judge_IS_report:{text}")
        if text=="交税":
            return "pay"
        if text=="屎":
            return "report"
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
            logger.info(f"llm_judge_IS_report result:{llm_resp.completion_text.strip().lower()}")
            return llm_resp.completion_text.strip().lower()
        except Exception as e:
            logger.error(f"TaxOfficer LLM 出错: {e}")
            logger.error(traceback.format_exc())
        return None

    @filter.event_message_type(EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        logger.info(f"on_message")
        msg = event.get_messages()

        reply_comp = next((c for c in msg if isinstance(c, Reply)), None)
        if not reply_comp:
            logger.info("不是税务相关")
            return
        logger.info(f"reply_comp:{reply_comp}")


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
            yield event.plain_result("不准举报bot酱！")
            return


        logger.info("# 引用的消息中的图片/聊天记录")
        quoted_other = []
        if reply_comp.chain:
            for item in reply_comp.chain:
                if isinstance(item, Image) or isinstance(item, Forward):
                    url = item.url or item.file or ""
                    if url:
                        quoted_other.append(url)
        logger.info(quoted_other)
        logger.info("# 当前的消息中的图片")
        current_images = []
        for c in msg:
            if isinstance(c, Image):
                url = c.url or c.file or ""
                if url:
                    current_images.append(url)
        logger.info(current_images)
        provider_id = await self.context.get_current_chat_provider_id(
            umo=event.unified_msg_origin
        )

        has_images = len(quoted_other) > 0
        plain_text = "".join(c.text for c in msg if isinstance(c, Plain))
        has_text = bool(plain_text.strip())

        logger.info("# ── LLM 分类 ──")


        result = await self.llm_judge_IS_Rreport(provider_id,user_text)
        if result=="other":
            return

        if result=="pay":

            self.data.pay_debt(quoted_id, quoted_name, quoted_text, quoted_other)
            debt_num = len(self.data.get_unpaid_debts(quoted_id))
            yield event.plain_result(
                f"🚨 交税成功！\n"
                f"📌 缴纳人：{quoted_name}\n"
                f"💩 内容：{quoted_text or '(无文本)'}\n"
                f"{'🖼️ 含罪证图片\n' if quoted_other else ''}"
                f"💰 {quoted_name} 当前欠税：{debt_num} 条"
            )
            return
        logger.info("准备交税")
        # 去重
        dedup_key = f"{event.get_message_str()}|{event.get_sender_id()}|{event.get_group_id()}"
        if dedup_key not in self.resent_reports:
            self.resent_reports.append(dedup_key)
            if len(self.resent_reports) >= 50:
                self.resent_reports.pop(0)
        else:
            yield event.plain_result("已经举报过了")
            return
            # 欠税 >2 不能举报
        if len(self.data.get_unpaid_debts(reporter_id))>self.config.max_reporter_debts:
            yield event.plain_result(f"🚫 {reporter_name}，你欠税超过 {self.config.max_reporter_debts} 条，先交税再来举报！")
            return
        if not has_images and has_text:
            is_shit =await self.llm_judge_IS_Shit(provider_id,quoted_text)
            if is_shit :
                debt_num=len(self.data.get_unpaid_debts(quoted_id))
                if debt_num<self.config.max_debts:
                    self.data.add_debt(quoted_id, quoted_name, quoted_text, quoted_other, reporter_id, reporter_name)
                    yield event.plain_result(
                        f"🚨 举报已立案！\n"
                        f"📌 嫌疑人：{quoted_name}\n"
                        f"💩 罪证：{quoted_text or '(无文本)'}\n"
                        f"{'🖼️ 含罪证图片\n' if quoted_other else ''}"
                        f"🚔 举报人：{reporter_name}\n"
                        f"💰 {quoted_name} 当前欠税：{debt_num+1} 条"
                    )
                    return
                else:
                    yield event.plain_result(f"{quoted_name}已经欠税{debt_num}条了，可怜可怜他")
                    return
            else:
                debt_num = len(self.data.get_unpaid_debts(quoted_id))
                self.data.add_debt(reporter_id, reporter_name, quoted_text, quoted_other, reporter_id, reporter_name)
                yield event.plain_result(
                    f"🚨 诬告！\n"
                    f"📌 嫌疑人：{reporter_name}\n"
                    f"💩 罪证：{ quoted_text or '(无文本)'}\n"
                    f"{'🖼️ 含罪证图片\n' if quoted_other else ''}"
                    f"💰 {reporter_name} 当前欠税：{debt_num + 1} 条"
                )
                return

        if has_images:
            debt_num = len(self.data.get_unpaid_debts(quoted_id))
            if debt_num < self.config.max_debts:
                self.data.add_debt(quoted_id, quoted_name, quoted_text, quoted_other, reporter_id, reporter_name)
                yield event.plain_result(
                    f"🚨 举报已立案！\n"
                    f"📌 嫌疑人：{quoted_name}\n"
                    f"💩 罪证：{quoted_text or '(无文本)'}\n"
                    f"{'🖼️ 含罪证图片\n' if quoted_other else ''}"
                    f"🚔 举报人：{reporter_name}\n"
                    f"💰 {quoted_name} 当前欠税：{debt_num + 1} 条"
                )
                return
            else:
                yield event.plain_result(f"{quoted_name}已经欠税{debt_num}条了，可怜可怜他")
                return








"""
TaxOfficer 数据持久化模块。

目录结构：
  {base_path}/
    {user_id}/                    # 以用户 ID 命名的文件夹
      report_record.json          # 这个人作为"举报人"的所有举报记录
      debt_record.json            # 这个人作为"欠税人"的所有欠税/交税记录

report_record.json 结构（列表）：
  [
    {
      "id": "uuid",               # 举报记录唯一 ID
      "reporter_id": "123",       # 举报人 ID
      "reporter_name": "张三",    # 举报人昵称（举报时的）
      "shitter_id": "456",        # 被举报人 ID
      "shitter_name": "李四",     # 被举报人昵称
      "shit_text": "消息内容",    # 屎的文本
      "shit_images": ["url"],     # 屎的图片
      "is_valid": true,           # 举报是否有效（false=恶意举报）
      "timestamp": 1234567890     # 举报时间
    }
  ]

debt_record.json 结构（列表）：
  [
    {
      "id": "uuid",               # 欠税记录唯一 ID
      "shitter_id": "456",        # 欠税人 ID
      "shitter_name": "李四",     # 欠税人昵称
      "shit_text": "消息内容",    # 屎的文本
      "shit_images": ["url"],     # 屎的图片
      "reporter_id": "123",       # 举报人 ID
      "reporter_name": "张三",    # 举报人昵称
      "timestamp": 1234567890,    # 立案时间
      "paid": false,              # 是否已还
      "payment": null              # 如果已还，记录交税信息
                                   # {
                                   #   "payment_id": "uuid",
                                   #   "payer_name": "李四",
                                   #   "tax_text": "...",
                                   #   "tax_images": ["url"],
                                   #   "timestamp": 1234567891
                                   # }
    }
  ]
"""

import json
import os
import time
import uuid


class TaxDataManager:
    """
    按用户 ID 分文件夹存储数据的管理器。
    每个用户的举报记录和欠税记录分别存在各自的 JSON 文件里。
    """

    def __init__(self, base_path: str):
        """
        初始化数据管理器。

        Args:
            base_path: 数据根目录（如 data/plugin_data/TaxOfficer/）
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    # ── 内部工具方法 ──

    def _user_dir(self, user_id: str) -> str:
        """获取（并创建）指定用户的文件夹"""
        d = os.path.join(self.base_path, str(user_id))
        os.makedirs(d, exist_ok=True)
        return d

    def _report_path(self, user_id: str) -> str:
        """举报记录文件路径"""
        return os.path.join(self._user_dir(user_id), "report_record.json")

    def _debt_path(self, user_id: str) -> str:
        """欠税记录文件路径"""
        return os.path.join(self._user_dir(user_id), "debt_record.json")

    def _load_json(self, path: str) -> list:
        """从 JSON 文件加载列表，文件不存在则返回空列表"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_json(self, path: str, data: list):
        """保存列表到 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════════
    #  举报记录 — 这个人举报了谁
    # ═══════════════════════════════════════════════

    def load_reports(self, reporter_id: str) -> list:
        """加载某个用户的全部举报记录"""
        return self._load_json(self._report_path(reporter_id))

    def add_report(self, reporter_id: str, reporter_name: str,
                   shitter_id: str, shitter_name: str,
                   shit_text: str, shit_images: list,
                   is_valid: bool) -> dict:
        """
        添加一条举报记录，保存到举报人的 report_record.json。

        Args:
            reporter_id: 举报人 ID
            reporter_name: 举报人昵称
            shitter_id: 被举报人 ID
            shitter_name: 被举报人昵称
            shit_text: 屎的文本
            shit_images: 屎的图片 URL 列表
            is_valid: 举报是否有效（True=有效, False=恶意举报被反杀）

        Returns:
            新创建的举报记录 dict
        """
        record = {
            "id": str(uuid.uuid4()),
            "reporter_id": reporter_id,
            "reporter_name": reporter_name,
            "shitter_id": shitter_id,
            "shitter_name": shitter_name,
            "shit_text": shit_text,
            "shit_images": shit_images,
            "is_valid": is_valid,
            "timestamp": time.time(),
        }
        reports = self.load_reports(reporter_id)
        reports.append(record)
        self._save_json(self._report_path(reporter_id), reports)
        return record

    # ═══════════════════════════════════════════════
    #  欠税记录 — 这个人欠了多少税
    # ═══════════════════════════════════════════════

    def load_debts(self, user_id: str) -> list:
        """加载某个用户的全部欠税记录"""
        return self._load_json(self._debt_path(user_id))

    def add_debt(self, shitter_id: str, shitter_name: str,
                 shit_text: str, shit_images: list,
                 reporter_id: str, reporter_name: str) -> dict:
        """
        添加一条欠税记录，保存到欠税人的 debt_record.json。

        Args:
            shitter_id: 欠税人 ID
            shitter_name: 欠税人昵称
            shit_text: 屎的文本
            shit_images: 屎的图片 URL 列表
            reporter_id: 举报人 ID
            reporter_name: 举报人昵称

        Returns:
            新创建的欠税记录 dict
        """
        debts = self.load_debts(shitter_id)
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
            "payment": None,
        }
        debts.append(debt)
        self._save_json(self._debt_path(shitter_id), debts)
        return debt

    def get_unpaid_debts(self, user_id: str) -> list:
        """获取某个用户所有未还的欠税（按时间排序，最早的在前）"""
        return [d for d in self.load_debts(user_id) if not d["paid"]]

    def unpaid_count(self, user_id: str) -> int:
        """获取某个用户未还欠税数量"""
        return len(self.get_unpaid_debts(user_id))

    def pay_debt(self, payer_id: str, payer_name: str,
                 tax_text: str, tax_images: list) -> dict | None:
        """
        交税：偿还最早一笔未还欠税。

        Args:
            payer_id: 交税人 ID
            payer_name: 交税人昵称
            tax_text: 交税时的文本
            tax_images: 交税时的图片（税图）

        Returns:
            被偿还的欠税记录 dict（已标记为 paid），
            如果没有未还欠税则返回 None。
        """
        debts = self.load_debts(payer_id)
        for debt in debts:
            if not debt["paid"]:
                # 标记为已还
                debt["paid"] = True
                debt["payment"] = {
                    "payment_id": str(uuid.uuid4()),
                    "payer_name": payer_name,
                    "tax_text": tax_text,
                    "tax_images": tax_images,
                    "timestamp": time.time(),
                }
                self._save_json(self._debt_path(payer_id), debts)
                return debt
        return None

    # ═══════════════════════════════════════════════
    #  跨用户查询
    # ═══════════════════════════════════════════════

    def list_all_unpaid_debts(self) -> dict:
        """
        遍历所有用户目录，收集所有有未还欠税的用户信息。
        用于 /所有欠税 命令。

        Returns:
            dict: {user_id: {"name": str, "count": int, "debts": list}}
                  按欠税条数从多到少排序
        """
        result = {}
        if not os.path.exists(self.base_path):
            return result
        for uid in os.listdir(self.base_path):
            debt_path = os.path.join(self.base_path, uid, "debt_record.json")
            if not os.path.exists(debt_path):
                continue
            with open(debt_path, "r", encoding="utf-8") as f:
                try:
                    debts = json.load(f)
                except json.JSONDecodeError:
                    continue
            unpaid = [d for d in debts if not d["paid"]]
            if unpaid:
                result[uid] = {
                    "name": unpaid[0].get("shitter_name", f"用户{uid}"),
                    "count": len(unpaid),
                    "debts": unpaid,
                }
        # 按欠税条数从高到低排序
        sorted_result = dict(sorted(result.items(), key=lambda x: x[1]["count"], reverse=True))
        return sorted_result

