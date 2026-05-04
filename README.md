<div align="center">

# 🎖️ TaxOfficer · 群税官

**AI 驱动的群聊屎税管理系统 —— 让 LLM 替你收税！**

[![AstrBot](https://img.shields.io/badge/AstrBot-v4.24%2B-blue)](https://github.com/Soulter/AstrBot)
[![AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v2.0-brightgreen)](https://github.com/C1F5D2DD/TaxOfficer-astrbot)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)

**一个基于 [AstrBot](https://github.com/Soulter/AstrBot) 的趣味群管理插件，让 LLM 来理解群友们在说什么屎话！**

</div>

---

## 📖 简介

TaxOfficer（群税官）v2.0 完全重构，不再使用固定命令。**通过大模型（LLM）理解群友的自然语言**，自动识别"举报屎"和"交税"意图，记录群友的屎和税，实现群内自我监督！

> 💡 **核心思路**：群友引用一条消息说"这也太逆天了" → LLM 判断为举报 → 记录欠税。群友说"交税了"并附上图片 → LLM 判断为交税 → 消除欠税记录。

---

## ✨ 功能特性

- 🤖 **LLM 驱动** — 不再需要固定命令，群友用自然语言就能触发
- 🚨 **举报屎** — 引用消息 + 自然语言表达"这是屎" → 被举报人欠税 +1
- 💰 **交税** — 引用消息 + 表达"交税"并附图片/文字 → 清除欠税记录
- 📊 **欠税追踪** — 自动统计每个人的欠税条数，先还最早欠的税
- 🖼️ **图文取证** — 屎和税都支持图片 + 文本记录
- 🗄️ **持久化存储** — 数据保存在 `tax_data.json`，重启不丢失

---

## 🎯 工作流程

```
群友 A：发了某条不合适/精神污染的消息

┌─────────────────────────────────────────────────────┐
│  举报流程                                            │
│                                                     │
│  群友 B（引用群友 A 的消息）："这也能发出来？"        │
│                                                      │
│  → LLM 判断为 "report_shit"                          │
│  → 群税官回复：🚨 举报已立案！                        │
│    📌 嫌疑人：群友 A                                  │
│    💩 罪证：群友 A 的消息内容                          │
│    🚔 举报人：群友 B                                  │
│    💰 当前欠税：1 条                                   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  交税流程                                            │
│                                                     │
│  群友 A（引用任意消息）："交税了" [+ 图片作为税]      │
│                                                      │
│  → LLM 判断为 "pay_tax"                              │
│  → 群税官回复：💰 收税成功！                          │
│    🙋 纳税人：群友 A                                  │
│    📝 抵税条目：之前的屎内容                           │
│    🖼️ 税图已入库                                      │
│    📊 剩余欠税：0 条                                   │
└─────────────────────────────────────────────────────┘
```

---

## 📋 触发方式

不再需要固定命令！只要**引用一条消息**并说出相关自然语言即可：

### 举报屎
引用消息 + 任何表达"这是屎"含义的话：
- "这也太逆天了"
- "绷不住了"
- "这什么玩意儿"
- "举报了"
- "这也能发？"
- 等等……

### 交税
引用消息 + 表达交税含义的话（通常附上图片作为税）：
- "交税了"
- "纳税"
- "上税"
- "交罚款"
- "补税"
- 等等……

> ⚠️ **注意**：所有操作都必须**引用（回复）一条消息**，否则不会被处理。

---

## 🔧 安装方法

### 方法一：通过 AstrBot 插件市场
1. 打开 AstrBot 控制面板
2. 进入 **插件管理** 页面
3. 搜索 `TaxOfficer`
4. 点击 **安装**

### 方法二：手动安装
```bash
cd AstrBot/plugins/
git clone https://github.com/C1F5D2DD/TaxOfficer-astrbot.git
# 重启 AstrBot
```

### 方法三：从 GitHub 安装
在 AstrBot WebUI 插件管理页面，选择「从 GitHub 安装」，输入：
```
https://github.com/C1F5D2DD/TaxOfficer-astrbot.git
```

---

## ⚙️ 配置说明

本插件**无需额外配置**。会调用 AstrBot 当前使用的 LLM 提供商（如 DeepSeek、OpenAI 等）进行意图分类。

> 💡 **建议**：使用 DeepSeek 等性价比高的模型进行分类，每次分类消耗极少量 token。

---

## 📦 依赖要求

- **Python** >= 3.9
- **AstrBot** >= v4.24（需要 `context.llm_generate` API）
- 无需其他第三方依赖

---

## 🗺️ 未来计划

- [ ] 📊 `/税单` 命令 — 查看群友的纳税统计排名
- [ ] 🗑️ 管理员赦免命令
- [ ] ⚙️ 可配置的 LLM 分类模型
- [ ] 🔔 欠税过多时自动提醒

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

## 📄 开源许可

本项目基于 **GNU Affero General Public License v3.0** 开源协议发布。

---

<div align="center">

**⭐ 如果觉得这个插件有趣，欢迎给个 Star！** ⭐

[![Star](https://img.shields.io/github/stars/C1F5D2DD/TaxOfficer-astrbot?style=social)](https://github.com/C1F5D2DD/TaxOfficer-astrbot)

*让 LLM 替你收税，从今天开始！* 🎖️

</div>
