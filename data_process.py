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

    def find_debts_by_name(self, name: str) -> list:
        """
        遍历所有用户目录，模糊匹配欠税人名字。
        用于 /查税 name 命令。
        """
        results = []
        if not os.path.exists(self.base_path):
            return results
        for uid in os.listdir(self.base_path):
            debt_path = os.path.join(self.base_path, uid, "debt_record.json")
            if os.path.exists(debt_path):
                with open(debt_path, "r", encoding="utf-8") as f:
                    try:
                        debts = json.load(f)
                    except json.JSONDecodeError:
                        continue
                for d in debts:
                    if d.get("shitter_name") == name or name in d.get("shitter_name", ""):
                        results.append(d)
        return results
