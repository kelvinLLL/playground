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

## Phase 3: Memory System (Completed)

- [x] ConversationMemory - Short-term per-user/channel (auto-expires 1hr)
- [x] PersistentMemory - Long-term SQLite storage
- [x] Worker internal memory

**Discord Commands:**
- `!remember <key> <value>` - Store a fact
- `!recall <key>` - Retrieve a fact
- `!forget <key>` - Delete a fact
- `!memory` - Show all memories
- `!clearhistory` - Clear channel conversation
- `!clearall` - **NEW** Clear ALL memory (conversation + persistent + worker)

## Phase 4: MCP Integration (Completed - 2026-01-27)

### MCP-First Architecture

Workers automatically use MCP tools when available, falling back to local implementations.

**Key Components:**
- `ToolRegistry.prefer_mcp = True` - Auto-discovers MCP versions
- `MCPProxyTool` - Wraps remote MCP tools for local use
- `${VAR}` expansion in mcp_servers.json

### Connected MCP Servers (5 total, 48 tools)

| Server | Package | Tools |
|--------|---------|-------|
| self_hosted | Local Python MCP | 4 (web_search, read_pdf, fetch_market_data, run_backtest) |
| filesystem | @modelcontextprotocol/server-filesystem | 14 (read/write/edit files) |
| playwright | @playwright/mcp@latest | 22 (browser automation) |
| duckduckgo | duckduckgo-mcp-server (uvx) | 2 (search, fetch_content) |
| brave_search | @brave/brave-search-mcp-server | 6 (web/news/image/video search) |

### Configuration Files

**mcp_servers.json:**
```json
{
  "mcpServers": {
    "self_hosted": { "command": "python", "args": ["-m", "ai_worker.mcp_server"] },
    "filesystem": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "..."] },
    "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp@latest", "--headless"] },
    "duckduckgo": { "command": "uvx", "args": ["duckduckgo-mcp-server"] },
    "brave_search": { "command": "npx", "args": ["...", "${BRAVE_API_KEY}"] }
  }
}
```

**.env:**
```
DISCORD_TOKEN=...
OPENAI_API_KEY=sk-antigravity
OPENAI_BASE_URL=http://127.0.0.1:8045/v1
OPENAI_MODEL=gemini-3-flash
TAVILY_API_KEY=...
BRAVE_API_KEY=...
```

---

## Current Architecture

```
ai_worker/
├── config/settings.py          # Settings with dotenv
├── core/message.py             # StandardMessage abstraction
├── adapters/discord_adapter.py # Discord bot
├── workers/
│   ├── base.py                 # BaseWorker with register_tool(as_name=)
│   ├── default.py              # General chat
│   ├── research_worker.py      # PDF analysis
│   ├── web_search_worker.py    # Web search
│   ├── game_worker.py          # Game guides
│   └── quant/
│       ├── intel_worker.py     # Market data
│       └── strategy_worker.py  # Backtesting
├── tools/
│   ├── base.py                 # BaseTool, ToolResult
│   ├── registry.py             # MCP-First ToolRegistry
│   └── *.py                    # Local tool implementations
├── memory/
│   ├── conversation.py         # Short-term memory
│   └── persistent.py           # SQLite long-term memory
├── mcp_server.py               # FastMCP server (4 tools)
├── mcp_client.py               # MCPClientManager
├── mcp_servers.json            # MCP server configs
├── reports/                    # Filesystem MCP sandbox
└── main.py                     # Entry point
```

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

## Known Issues

1. **SSL Certificate:** Need `NODE_TLS_REJECT_UNAUTHORIZED=0` for npm packages
2. **Pyright LSP:** Shows import errors (config issue, doesn't affect runtime)
3. **Model Limits:** gemini-3-pro-low has account limits, using gemini-3-flash

---

## Next Phase: Planned Features

### Option A: Daily Briefing Worker
Scheduled worker that:
1. Searches trending papers/GitHub repos
2. Gathers daily news and investment insights
3. Uses tiered search: DuckDuckGo → Brave → Tavily
4. Scrapes with Playwright for deep content
5. Writes markdown reports to `reports/`

### Option B: Function Calling Integration
Upgrade LLM client to support proper OpenAI function calling:
- Workers can dynamically decide which tools to use
- More natural multi-tool workflows

### Option C: Multi-Platform Support
Add adapters for:
- Feishu (飞书)
- Slack
- Telegram

### Option D: Agent Orchestration
Create a Manager/Dispatcher that:
- Routes complex tasks to multiple workers
- Coordinates multi-step workflows
- Implements ReAct-style reasoning

---

*Last Updated: 2026-01-27 21:45*
