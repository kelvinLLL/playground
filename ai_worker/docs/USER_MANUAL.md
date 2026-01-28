# 🤖 AI Worker User Manual

Welcome to your AI Employee system! This bot is designed to be a versatile assistant that can handle research, stock analysis, game guides, and daily intelligence briefings.

## 🗣️ Natural Language Interaction (New!)
You don't need to memorize complex commands. Just talk naturally, and the **Smart Router** will assign the right agent to help you.

**Examples:**
- **Web Search:** "Search for the latest news on DeepSeek."
- **Game Guide:** "How do I beat the final boss in Black Myth: Wukong?"
- **Stock Analysis:** "Fetch market data for NVIDIA."
- **Backtest:** "Run a backtest for a mean reversion strategy on AAPL."
- **Research:** "Summarize this paper: https://arxiv.org/abs/2301.xxxxx"
- **Daily Brief:** "Generate today's intelligence brief."

---

## 📅 Daily Intelligence Brief
The bot can generate a comprehensive daily report covering AI News, GitHub Trending, ArXiv Papers, and Market Insights.

### Manual Generation
- **Command:** `!brief`
- **Result:** Generates the report immediately and sends it as a Markdown file attachment.

### Scheduled Delivery (Auto-Pilot)
You can set up the bot to send you a report every morning automatically.

**Setup Steps:**
1. **Set Channel:** Go to the channel where you want the report and type:
   `!setchannel`
2. **Set Time:** Set the delivery time (24h format, e.g., 8:30 AM):
   `!settime 8 30`
3. **Enable:** Turn on the scheduler:
   `!enablebrief`

**Other Commands:**
- `!disablebrief`: Stop scheduled reports.
- `!schedule`: View current schedule settings.

---

## 🧠 Memory System
The bot has both short-term (conversation) and long-term (fact) memory.

- **Remember:** `!remember my_name Kelvin`
- **Recall:** `!recall my_name`
- **Forget:** `!forget my_name`
- **Check Status:** `!memory` (See what the bot knows about you)
- **Clear History:** `!clearhistory` (Reset current conversation)

---

## 🛠️ Debug & Tools
For advanced users who want to test specific capabilities.

- `!tools`: List all available tools (Search, Browser, Filesystem, etc.).
- `!mcp_test <query>`: Force a test of the Model Context Protocol (MCP) integration.
- `!ping`: Check if the bot is alive.

---

## 🆘 Getting Help
At any time, type `!aihelp` in Discord to see a quick reference card.
