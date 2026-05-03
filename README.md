<div align="center">

# 🎖️ TaxOfficer · 群税官

**记录群友搬的屎，征收精神污染税！**

[![AstrBot](https://img.shields.io/badge/AstrBot-v4.5%2B-blue)](https://github.com/Soulter/AstrBot)
[![AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v1.0-brightgreen)](https://github.com/C1F5D2DD/TaxOfficer-astrbot)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)

**一个基于 [AstrBot](https://github.com/Soulter/AstrBot) 的趣味群管理插件，让群友们为自己的"精神污染"行为负责！**

</div>

---

## 📖 简介

TaxOfficer（群税官）是一个轻松有趣的群聊管理插件，旨在**记录群友在群里发布的"屎"（不合适的消息/精神污染内容）**。当群友发布了不合适的内容时，其他群友可以使用命令对该消息进行"举报"，插件会记录下这条消息的内容、发送者以及举报人信息，实现群内自我监督。

> 💡 **插件名称由来**：Tax 取自 Tax（税）的英文，"群税官"即负责征收"精神污染税"的群聊管理员。

---

## ✨ 功能特性

- ✅ **消息举报** — 引用一条消息并输入命令，即可举报该消息
- ✅ **图文记录** — 支持记录被举报消息的**文本内容**和**图片**
- ✅ **信息溯源** — 完整记录消息发送者、举报人信息，方便追溯
- ✅ **即时反馈** — 举报成功后立即返回详细记录报告
- ✅ **轻量高效** — 基于 AstrBot 框架，安装即用，无需额外配置

---

## 📋 命令列表

| 命令 | 说明 | 示例 |
|:---:|:---:|:---:|
| `/屎` | 举报并记录被引用的消息 | `引用一条消息 + /屎` |

### 使用示例

```
用户A：发了某条不合适/精神污染的消息
用户B（引用该消息）：/屎

💩 群税官回复：
📌 被引用消息发送者：用户A (123456789)
💩 屎内容：不合适的内容...
🖼️ 屎图：https://example.com/image.jpg
🚨 举报人：用户B (987654321)
```

---

## 🔧 安装方法

### 方法一：通过 AstrBot 插件市场（推荐）

1. 打开 AstrBot 控制面板
2. 进入 **插件管理** 页面
3. 搜索 `TaxOfficer`
4. 点击 **安装**

### 方法二：手动安装

```bash
# 进入 AstrBot 插件目录
cd AstrBot/plugins/

# 克隆仓库
git clone https://github.com/C1F5D2DD/TaxOfficer-astrbot.git

# 重启 AstrBot 即可加载插件
```

### 方法三：直接下载

1. 下载本仓库的 [最新源码](https://github.com/C1F5D2DD/TaxOfficer-astrbot/archive/refs/heads/main.zip)
2. 解压到 AstrBot 的 `plugins/` 目录下
3. 重启 AstrBot

---

## ⚙️ 配置说明

本插件**无需额外配置**，安装后即可使用。所有功能通过命令触发，零配置开箱即用。

---

## 📦 依赖要求

- **Python** >= 3.9
- **AstrBot** >= v4.5（支持插件 display_name 特性）
- 无需其他第三方依赖

---

## 🗺️ 未来计划

- [ ] 🗑️ `/赦免` 命令 — 赦免被举报的消息
- [ ] 📊 `/税单` 命令 — 查看群友的"纳税"统计排名
- [ ] ⚙️ 可配置的举报关键词自动触发
- [ ] 🔔 举报达到阈值时自动通知管理员

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进 TaxOfficer！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

---

## 📄 开源许可

本项目基于 **GNU Affero General Public License v3.0** 开源协议发布。详见 [LICENSE](LICENSE) 文件。

```
Copyright (C) 2022-2099 AstrBot Plugin Authors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
```

---

<div align="center">

**⭐ 如果觉得这个插件有趣，欢迎给个 Star！** ⭐

[![Star](https://img.shields.io/github/stars/C1F5D2DD/TaxOfficer-astrbot?style=social)](https://github.com/C1F5D2DD/TaxOfficer-astrbot)

*让群聊环境更美好，从征收精神污染税开始！* 🎖️

</div>
