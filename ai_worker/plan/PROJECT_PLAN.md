# AI Worker 项目开发计划

> 创建时间: 2026-01-25
> 最后更新: 2026-01-25

## 一、项目概览

**目标**：构建一个可扩展的多Agent AI员工系统，支持通过Discord和飞书对话框与专职AI员工交互。

**核心理念**：
- 每个AI员工专人专职（量化情报员、策略回测员等）
- 对话框 = 操作系统（LUI自然语言用户界面）
- Adapter Pattern 实现多平台支持

---

## 二、系统架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层 (User Layer)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Discord   │  │    飞书      │  │   未来平台   │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    适配器层 (Adapter Layer)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │DiscordAdapter│ │ FeishuAdapter│ │ 未来Adapter  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┴────────────────┴────────────────┴─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    消息网关 (Message Broker)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • 消息标准化 (StandardMessage)                              │ │
│  │  • 路由分发 (Router) - @员工名 -> 对应Worker                  │ │
│  │  • 权限鉴权 (Auth)                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI员工层 (Worker Layer)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐   │
│  │ 量化情报员  │  │ 策略回测员  │  │ 市场跟踪员  │  │ 通用助手  │   │
│  │ Agent A    │  │ Agent B    │  │ Agent C    │  │ Default  │   │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘   │
│          │              │              │              │          │
│          └──────────────┴──────────────┴──────────────┘          │
│                              │                                    │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  大脑 (LLM Core)                             │ │
│  │           OpenAI GPT-4o / Claude / 可配置                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     工具层 (Tools Layer)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Web搜索   │  │ 回测框架  │  │ 数据获取  │  │ 文件操作  │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构规划

```
ai_worker/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py           # 配置管理 (API Keys, 平台配置)
│
├── core/
│   ├── __init__.py
│   ├── message.py            # StandardMessage 消息标准化
│   ├── router.py             # 消息路由器
│   └── broker.py             # 消息网关核心
│
├── adapters/
│   ├── __init__.py
│   ├── base.py               # 适配器基类
│   ├── discord_adapter.py    # Discord 适配器
│   └── feishu_adapter.py     # 飞书适配器
│
├── workers/
│   ├── __init__.py
│   ├── base.py               # AI员工基类
│   ├── default.py            # 通用助手
│   └── quant/                # 量化专员 (后续扩展)
│       ├── __init__.py
│       ├── intel_worker.py   # 情报员
│       └── strategy_worker.py # 策略员
│
├── llm/
│   ├── __init__.py
│   ├── base.py               # LLM基类
│   └── openai_client.py      # OpenAI客户端
│
├── tools/
│   ├── __init__.py
│   └── base.py               # 工具基类
│
├── plan/                     # 项目计划文档
│   └── PROJECT_PLAN.md
│
└── main.py                   # 入口文件
```

---

## 四、分阶段开发计划

### Phase 1: Hello World (MVP) ✅ COMPLETED
**目标**：跑通最小可用版本

| 步骤 | 任务 | 状态 |
|------|------|------|
| 1.1 | 项目初始化 - 创建目录结构，配置管理 | [x] |
| 1.2 | Discord Bot 基础版 - 能接收消息并回复 "Hello World" | [x] |
| 1.3 | 消息标准化 - StandardMessage 数据结构 | [x] |
| 1.4 | Adapter 基类 - 抽象适配器接口 | [x] |
| 1.5 | Discord Adapter 重构 - 符合 Adapter Pattern | [x] |

**验收标准**：在Discord发送消息，Bot能正确回复

### Phase 2: 接入LLM ✅ COMPLETED
**目标**：AI员工能"思考"

| 步骤 | 任务 | 状态 |
|------|------|------|
| 2.1 | OpenAI Client - 封装 GPT-4o 调用 | [x] |
| 2.2 | LLM 基类 - 抽象 LLM 接口 | [x] |
| 2.3 | 默认员工 (DefaultWorker) - 接入LLM的通用助手 | [x] |
| 2.4 | 消息路由器 - 根据内容路由到对应Worker | [x] |

**验收标准**：发送问题，AI员工能智能回复

### Phase 3: 飞书适配器 (SKIPPED)
**目标**：支持飞书平台 (暂缓开发，优先增强能力)

### Phase 4: 专职员工 (量化场景) ✅ COMPLETED
**目标**：实现专人专职

| 步骤 | 任务 | 状态 |
|------|------|------|
| 4.1 | Worker 基类完善 - 角色/工具/权限隔离 | [x] |
| 4.2 | 情报员 (IntelWorker) - 专注信息收集 (MarketDataTool) | [x] |
| 4.3 | 策略员 (StrategyWorker) - 集成现有回测框架 (BacktestTool) | [x] |
| 4.4 | 路由逻辑 - 关键词/意图路由 | [x] |

**验收标准**：@策略员 跑回测 AAPL -> 返回回测结果

### Phase 5: 研究员 (Research Worker) ✅ COMPLETED
**目标**：深度阅读论文并生成报告

| 步骤 | 任务 | 状态 |
|------|------|------|
| 5.1 | PDF 解析工具 - 实现 PDFReaderTool (pypdf) | [x] |
| 5.2 | Discord 附件处理 - 支持下载用户上传的文件 | [x] |
| 5.3 | 研究员 (ResearchWorker) - 实现深度阅读 Prompt | [x] |
| 5.4 | 路由优化 - 支持文件类型的自动路由 | [x] |

**验收标准**：上传 PDF，Worker 返回详细阅读报告

### Phase 6: Web Search & Game Guide ✅ COMPLETED
**目标**：实时网络搜索与垂直领域攻略

| 步骤 | 任务 | 状态 |
|------|------|------|
| 6.1 | WebSearchTool - 支持 Tavily/DuckDuckGo | [x] |
| 6.2 | WebSearchWorker - 通用搜索情报员 | [x] |
| 6.3 | GameWorker - 游戏攻略专员 (Prompt Engineering) | [x] |
| 6.4 | 路由优化 - 区分 search(通用) 与 guide(游戏) | [x] |

**技术实现**：
- **WebSearchWorker**: 处理 "search", "news" 等通用查询。
- **GameWorker**: 复用搜索工具，但通过 Prompt 扮演 "Wiki 编辑"，强制输出结构化攻略 (Boss打法/配装推荐)。
- **路由逻辑**: 自动识别 "攻略", "build", "boss" 等游戏术语。

**验收标准**：
- 通用搜索: "search latest AI news" -> 返回新闻摘要
- 游戏攻略: "Elden Ring Malenia 攻略" -> 返回 Boss 技能解析与打法

### Phase 7: Memory System ✅ COMPLETED
**目标**：对话记忆与用户偏好持久化

| 步骤 | 任务 | 状态 |
|------|------|------|
| 7.1 | ConversationMemory - 短期对话上下文 (per-user, per-channel) | [x] |
| 7.2 | PersistentMemory - SQLite 长期存储 (偏好/事实) | [x] |
| 7.3 | 内存集成 - Workers 自动获取上下文 | [x] |
| 7.4 | Discord 命令 - !remember, !recall, !forget, !memory | [x] |

**验收标准**：Bot 能记住用户偏好，跨会话保持上下文

### Phase 8: 高级功能 (Future)
**目标**：生产级增强

| 步骤 | 任务 | 状态 |
|------|------|------|
| 8.1 | 员工间协作 - Agent间自动流转任务 | [ ] |
| 8.2 | 卡片交互 (飞书) - 按钮/表单交互 | [ ] |
| 8.3 | Slash Commands (Discord) - /backtest 命令 | [ ] |
| 8.4 | Code Execution Worker - 安全沙箱代码执行 | [ ] |
| 8.5 | News/Sentiment Worker - 市场情绪分析 | [ ] |

---

## 五、技术依赖

```txt
# ai_worker/requirements.txt
discord.py>=2.0
lark-oapi>=1.0
openai>=1.0
python-dotenv
aiohttp
```

---

## 六、环境配置要求

### Discord 配置
1. 前往 https://discord.com/developers/applications 创建应用
2. 在 Bot 页面创建 Bot，获取 Token
3. 启用 `MESSAGE CONTENT INTENT`
4. 生成邀请链接，邀请到你的服务器

### 飞书配置
1. 前往 https://open.feishu.cn 创建应用
2. 开启机器人能力
3. 获取 App ID 和 App Secret
4. 配置事件订阅 URL

### 环境变量
```bash
# .env
DISCORD_TOKEN=your_discord_bot_token
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
OPENAI_API_KEY=your_openai_api_key
```

---

## 七、快速开始指南

### 安装依赖
```bash
cd ai_worker
pip install -r requirements.txt
```

### 配置环境变量
```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，填入你的 Discord Token
# DISCORD_TOKEN=your_discord_bot_token
```

### 创建 Discord Bot
1. 前往 https://discord.com/developers/applications
2. 点击 "New Application"，输入名称
3. 进入 Bot 页面，点击 "Add Bot"
4. 复制 Token，填入 .env 文件
5. 在 Bot 页面启用 "MESSAGE CONTENT INTENT"
6. 进入 OAuth2 -> URL Generator
   - 选择 Scopes: `bot`
   - 选择 Bot Permissions: `Send Messages`, `Read Message History`
7. 复制生成的 URL，在浏览器打开，邀请 Bot 到你的服务器

### 运行
```bash
cd ai_worker
python main.py
```

### 测试
在 Discord 服务器中发送：
- 任意消息 -> Bot 会回复 "Hello World! You said: ..."
- `!hello` -> Bot 会问候你
- `!ping` -> Bot 会回复延迟信息

---

## 八、更新日志

| 日期 | 更新内容 |
|------|----------|
| 2026-01-25 | 初始计划创建 |
| 2026-01-25 | Phase 1 完成 - Discord Hello World Bot |
