# AI Worker Project Progress

## Project Overview

**Location:** `/Users/haojunliu/Easy/Projects/playground/ai_worker/`  
**Purpose:** Multi-Agent AI Employee System with Discord integration and MCP tool ecosystem

---

## Phase 1: Core Architecture (Completed)

- [x] StandardMessage/StandardResponse abstraction
- [x] BaseWorker with tool registration
- [x] ToolRegistry with decorator-based registration
- [x] OpenAI-compatible LLM client
- [x] Discord adapter with typing indicators and reactions

## Phase 2: Workers (Completed)

| Worker | Purpose | Tools |
|--------|---------|-------|
| DefaultWorker | General chat | None |
| WebSearchWorker | Real-time web search | web_search |
| GameWorker | Game guides & walkthroughs | web_search |
| ResearchWorker | PDF/paper analysis | read_pdf |
| IntelWorker | Market data fetching | fetch_market_data |
| StrategyWorker | Backtesting | run_backtest |
| **DailyBriefWorker** | **Daily intelligence reports** | **search, playwright, filesystem** |

## Phase 3: Memory System (Completed)

- [x] ConversationMemory - Short-term per-user/channel (auto-expires 1hr)
- [x] PersistentMemory - Long-term SQLite storage
- [x] Worker internal memory

## Phase 4: MCP Integration (Completed)

### Connected MCP Servers (5 total, 48 tools)

| Server | Package | Tools |
|--------|---------|-------|
| self_hosted | Local Python MCP | 4 (web_search, read_pdf, fetch_market_data, run_backtest) |
| filesystem | @modelcontextprotocol/server-filesystem | 14 (read/write/edit files) |
| playwright | @playwright/mcp@latest | 22 (browser automation) |
| duckduckgo | duckduckgo-mcp-server (uvx) | 2 (search, fetch_content) |
| brave_search | @brave/brave-search-mcp-server | 6 (web/news/image/video search) |

## Phase 5: Daily Briefing System (Completed - 2026-01-27)

### Features

- **4-Phase Pipeline:** Scouting → Deep Dive → Editorial → Delivery
- **Configurable Schedule:** Via `.env` or Discord commands
- **Opt-in Activation:** Disabled by default, requires `!enablebrief`
- **Persistent Settings:** All settings survive restarts

### Configuration (.env)

```env
DAILY_BRIEF_HOUR=8
DAILY_BRIEF_MINUTE=0
NOTIFICATION_CHANNEL_ID=
DAILY_BRIEF_ENABLED=false
```

---

## Phase 6: Smart Routing & Experience Upgrade (Completed - 2026-01-28)

### Major Improvements
- **Smart Routing:** Replaced hardcoded keyword matching with LLM-based routing (`DefaultWorker` as Router)
- **Function Calling:** Added `chat_with_tools` support to OpenAIClient
- **File Delivery:** Daily briefs now return the full markdown file as an attachment in Discord
- **Model Upgrade:** Switched to `gemini-3-pro-high` for better reasoning

### Routing Logic
User Message → DefaultWorker (Smart Router)
                    ↓
              LLM decides (function calling)
                    ↓
        ┌──────────┼──────────┐
        ↓          ↓          ↓
  call_worker  call_mcp_tool  respond_directly
        ↓          ↓          ↓
   Specialized   MCP Tools   Direct LLM
    Workers                   Response

## Discord Commands Reference

### 基础命令
| Command | Description |
|---------|-------------|
| `!ping` | 检查响应延迟 |
| `!hello` | 打招呼 |
| `!aihelp` | 显示完整帮助 |

### 记忆系统
| Command | Description |
|---------|-------------|
| `!remember <key> <value>` | 记住事实 |
| `!recall <key>` | 回忆事实 |
| `!forget <key>` | 忘记事实 |
| `!memory` | 显示所有记忆 |
| `!clearhistory` | 清除频道对话 |
| `!clearall` | 清除所有记忆 |

### 每日简报
| Command | Description |
|---------|-------------|
| `!brief` | 手动生成简报 |
| `!enablebrief` | 启用定时简报 |
| `!disablebrief` | 禁用定时简报 |
| `!setchannel` | 设置通知频道 |
| `!settime <h> <m>` | 设置时间 |
| `!schedule` | 查看定时任务 |

### 工具调试
| Command | Description |
|---------|-------------|
| `!tools` | 列出所有工具 |
| `!mcp_test <query>` | 测试 MCP 调用 |

### 自然语言交互 (Smart Routing)
No more hardcoded "search xxx" commands! Just talk naturally:
- "Help me find the latest AI news" → Routes to Web Search
- "How do I beat the final boss in Elden Ring?" → Routes to Game Worker
- "Summarize this paper: [PDF Link]" → Routes to Research Worker
- "Analyze TSLA stock" → Routes to Intel Worker
- "Run a backtest for AAPL" → Routes to Strategy Worker
- "Generate today's brief" → Routes to Daily Brief Worker

---

## Running the Bot

```bash
cd /Users/haojunliu/Easy/Projects/playground/ai_worker
NODE_TLS_REJECT_UNAUTHORIZED=0 PYTHONPATH=/Users/haojunliu/Easy/Projects/playground uv run python -m ai_worker.main
```

**Stopping:**
```bash
pkill -f "ai_worker.main"
```

---

## Architecture

```
ai_worker/
├── config/settings.py          # Settings with SchedulerConfig
├── core/message.py             # StandardMessage abstraction
├── adapters/discord_adapter.py # Discord bot
├── workers/
│   ├── base.py                 # BaseWorker
│   ├── default.py              # General chat
│   ├── daily_brief_worker.py   # Daily intelligence reports
│   ├── research_worker.py      # PDF analysis
│   ├── web_search_worker.py    # Web search
│   ├── game_worker.py          # Game guides
│   └── quant/
│       ├── intel_worker.py     # Market data
│       └── strategy_worker.py  # Backtesting
├── tools/
│   ├── registry.py             # MCP-First ToolRegistry
│   └── *.py                    # Local tool implementations
├── memory/
│   ├── conversation.py         # Short-term memory
│   └── persistent.py           # SQLite long-term memory
├── mcp_server.py               # FastMCP server (4 tools)
├── mcp_client.py               # MCPClientManager
├── mcp_servers.json            # MCP server configs
├── reports/                    # Daily brief output directory
└── main.py                     # Entry point with APScheduler
```

---

## Known Issues

1. **SSL Certificate:** Need `NODE_TLS_REJECT_UNAUTHORIZED=0` for npm packages
2. **Pyright LSP:** Shows import errors (config issue, doesn't affect runtime)
3. **Model Limits:** gemini-3-pro-low has account limits, using gemini-3-flash

---

## Next Phase: Planned Features

### Option A: Function Calling Integration
- LLM dynamically decides which tools to use
- More natural multi-tool workflows

### Option B: Multi-Platform Support
- Feishu (飞书)
- Slack / Telegram

### Option C: Enhanced Daily Brief
- Playwright scraping for full articles
- Tiered search: DuckDuckGo → Brave → Tavily
- Configurable topics via Discord

---

*Last Updated: 2026-01-27 22:45*
