# DailyBrief 搜索策略优化

## TL;DR

> **Quick Summary**: 优化 DailyBriefWorker 的搜索策略，DDG 作为主力（无限免费），Tavily/Brave 作为高质量数据源专用。确保每天 5 次、每月 31 天的使用需求。
> 
> **Deliverables**:
> - 修改 `WebSearchTool` 优先级：DDG 优先，Tavily 备用
> - 创建 `BraveSearchTool` 封装 Brave MCP
> - 在 `curated_sources.py` 中标记高优先级源
> - 智能搜索路由：根据源重要性选择搜索引擎
> 
> **Estimated Effort**: Medium (2-4 小时)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 → Task 3 → Task 5

---

## Context

### Original Request
用户需要确保 DailyBriefWorker 支持每天 5 次、每月 31 天的使用（共 155 次/月），并优化搜索策略避免超出 API 配额。

### 当前问题分析

**发现的问题**:
1. **Tavily 被优先使用** - 因为配置了 API key，所有搜索消耗 Tavily 配额（1,000次/月）
2. **Brave MCP 未集成** - 虽然配置了，但 DailyBriefWorker 没有使用
3. **无智能路由** - 所有搜索用同一个引擎，没有区分重要性

**配额计算**:
- 每次 Brief: ~12 次搜索调用
- 每月需求: 155 × 12 = 1,860 次/月
- Tavily 免费: 1,000 次/月 ❌ 不够
- Brave 免费: 2,000 次/月 ✅ 勉强够
- DuckDuckGo: 无限制 ✅ 足够

### 用户决策
- **主力**: DuckDuckGo (承担 80% 搜索量)
- **高质量备用**: Tavily + Brave 用于:
  - OpenAI/Anthropic/DeepMind 博客
  - AI 新闻聚合
  - DDG 失败时的 fallback
  - GitHub/HuggingFace trending

---

## Work Objectives

### Core Objective
建立三层搜索策略：DDG 主力 + Brave 中层 + Tavily 高质量，确保配额可持续使用。

### Concrete Deliverables
1. `ai_worker/tools/web_search.py` - 修改优先级逻辑
2. `ai_worker/tools/brave_search.py` - 新建 Brave 封装
3. `ai_worker/config/curated_sources.py` - 添加 `search_tier` 字段
4. `ai_worker/workers/daily_brief_worker.py` - 智能搜索路由

### Definition of Done
- [ ] DDG 成为默认搜索引擎
- [ ] Brave MCP 可被调用
- [ ] 高优先级源使用 Tavily/Brave
- [ ] 普通源使用 DDG
- [ ] 每月配额可支撑 155 次 Daily Brief

### Must Have
- DDG 优先的搜索策略
- Brave MCP 集成
- 按源重要性路由搜索引擎
- 配额监控日志

### Must NOT Have (Guardrails)
- 不修改 MCP 服务器配置
- 不删除现有的 Tavily 支持
- 不引入新的 API 依赖
- 不修改 Real-time APIs (HN/Reddit/GitHub 已经免费)

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: Manual-only
- **Framework**: N/A

### Manual Verification
```bash
# 1. 验证 DDG 是默认搜索
python -c "
from ai_worker.tools.web_search import WebSearchTool
tool = WebSearchTool()  # 不传 tavily_api_key
print('DDG 模式:', tool.tavily_api_key is None)
"

# 2. 验证 Brave 工具可用
python -c "
from ai_worker.tools.brave_search import BraveSearchTool
import asyncio
tool = BraveSearchTool()
result = asyncio.run(tool.execute(query='AI news today', max_results=2))
print('Brave:', 'OK' if result.success else result.error)
"

# 3. 生成 Brief 并检查日志
python -c "
import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from ai_worker.workers.daily_brief_worker import DailyBriefWorker
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.config import get_settings

async def test():
    s = get_settings()
    w = DailyBriefWorker(OpenAIClient(s.openai))
    r = await w.generate_brief()
    print('Report:', r.extras.get('file_path'))

asyncio.run(test())
"
# 检查日志中搜索引擎使用情况
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: 修改 WebSearchTool 优先级 [no dependencies]
└── Task 2: 创建 BraveSearchTool [no dependencies]

Wave 2 (After Wave 1):
├── Task 3: 更新 curated_sources 添加 search_tier [depends: 1, 2]
└── Task 4: 修改 DailyBriefWorker 智能路由 [depends: 1, 2]

Wave 3 (After Wave 2):
└── Task 5: 端到端验证 [depends: 3, 4]

Critical Path: Task 1 → Task 3 → Task 5
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3, 4 | 2 |
| 2 | None | 3, 4 | 1 |
| 3 | 1, 2 | 5 | 4 |
| 4 | 1, 2 | 5 | 3 |
| 5 | 3, 4 | None | None |

---

## TODOs

- [ ] 1. 修改 WebSearchTool 优先级

  **What to do**:
  - 修改 `ai_worker/tools/web_search.py`
  - **反转优先级**: DDG 优先，Tavily 作为备用
  - 添加 `use_premium` 参数，显式请求 Tavily
  - 添加日志记录使用的搜索引擎

  **代码修改**:
  ```python
  async def execute(self, **kwargs: Any) -> ToolResult:
      query = kwargs.get("query")
      max_results = min(kwargs.get("max_results", 5), 10)
      timelimit = kwargs.get("timelimit")
      use_premium = kwargs.get("use_premium", False)  # 新增参数
      
      # 反转优先级：DDG 优先，Tavily 用于高质量需求
      if use_premium and self.tavily_api_key:
          logger.info(f"[Search] Using Tavily (premium) for: {query[:50]}")
          result = await self._search_tavily(query, max_results)
          if result.success:
              return result
          logger.warning(f"Tavily failed, falling back to DDG")
      
      logger.info(f"[Search] Using DuckDuckGo for: {query[:50]}")
      return await self._search_duckduckgo(query, max_results, timelimit)
  ```

  **Must NOT do**:
  - 不要删除 Tavily 支持
  - 不要修改参数格式

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None

  **References**:
  - `ai_worker/tools/web_search.py:64-87` - execute 方法 ✅ VERIFIED
  - `ai_worker/tools/web_search.py:77-83` - 当前优先级逻辑

  **Acceptance Criteria**:
  - [ ] 默认情况下使用 DDG
  - [ ] `use_premium=True` 时使用 Tavily
  - [ ] 日志显示使用的搜索引擎
  
  ```bash
  python -m py_compile ai_worker/tools/web_search.py
  grep -n "use_premium" ai_worker/tools/web_search.py
  ```

  **Commit**: YES
  - Message: `refactor(search): prioritize DDG, Tavily as premium option`
  - Files: `ai_worker/tools/web_search.py`

---

- [ ] 2. 创建 BraveSearchTool

  **What to do**:
  - 创建 `ai_worker/tools/brave_search.py`
  - 封装 Brave MCP (`brave_search__brave_web_search`)
  - 支持 `query`, `max_results` 参数
  - 添加到 ToolRegistry

  **实现模式**:
  ```python
  from ai_worker.tools.base import BaseTool, ToolResult
  from ai_worker.tools.registry import ToolRegistry
  import os
  import aiohttp
  
  @ToolRegistry.register("brave_search")
  class BraveSearchTool(BaseTool):
      """Brave Search API wrapper."""
      
      def __init__(self, api_key: str = None):
          super().__init__(
              name="brave_search",
              description="Search the web using Brave Search API",
          )
          self.api_key = api_key or os.getenv("BRAVE_API_KEY", "")
      
      async def execute(self, **kwargs) -> ToolResult:
          query = kwargs.get("query")
          max_results = min(kwargs.get("max_results", 5), 20)
          
          if not self.api_key:
              return ToolResult(success=False, error="BRAVE_API_KEY not set")
          
          # Brave Search API 调用
          url = "https://api.search.brave.com/res/v1/web/search"
          headers = {
              "Accept": "application/json",
              "X-Subscription-Token": self.api_key
          }
          params = {"q": query, "count": max_results}
          
          async with aiohttp.ClientSession() as session:
              async with session.get(url, headers=headers, params=params) as resp:
                  if resp.status != 200:
                      return ToolResult(success=False, error=f"Brave API error: {resp.status}")
                  data = await resp.json()
                  # 格式化结果...
  ```

  **Must NOT do**:
  - 不要直接调用 MCP (用 REST API 更可靠)
  - 不要硬编码 API key

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None

  **References**:
  - `ai_worker/tools/web_search.py` - 作为模板参考
  - `ai_worker/.env:22` - BRAVE_API_KEY 位置
  - Brave API 文档: https://api.search.brave.com/app/documentation/web-search/get-started

  **Acceptance Criteria**:
  - [ ] `ai_worker/tools/brave_search.py` 文件存在
  - [ ] 可以成功调用 Brave API
  - [ ] 结果格式与 WebSearchTool 一致
  
  ```bash
  python -m py_compile ai_worker/tools/brave_search.py
  python -c "from ai_worker.tools.brave_search import BraveSearchTool; print('OK')"
  ```

  **Commit**: YES
  - Message: `feat(search): add BraveSearchTool for premium searches`
  - Files: `ai_worker/tools/brave_search.py`

---

- [ ] 3. 更新 curated_sources 添加 search_tier

  **What to do**:
  - 修改 `ai_worker/config/curated_sources.py`
  - 在 `Source` dataclass 添加 `search_tier` 字段
  - 值: `"standard"` (DDG), `"tavily"` (Tavily), `"brave"` (Brave)
  - 标记策略:
    - AI Research 核心源 → tavily (高质量)
    - News/Community 源 → brave (广度)
    - 其他 → standard (DDG)

  ```python
  @dataclass
  class Source:
      # ... existing fields ...
      search_tier: str = "standard"  # "standard" | "tavily" | "brave"
  ```

  **Premium 源列表 (Tavily - AI Research, ~3/brief)**:
  - OpenAI Blog (priority=1, AI Research) → `search_tier="tavily"`
  - Anthropic (priority=1, AI Research) → `search_tier="tavily"`
  - DeepMind Blog (priority=1, AI Research) → `search_tier="tavily"`
  - HuggingFace Daily Papers (priority=1, Research) → `search_tier="tavily"`

  **Premium 源列表 (Brave - News/Community, ~3/brief)**:
  - Papers With Code (priority=1, Research) → `search_tier="brave"`
  - AIBase (priority=1, Chinese AI News) → `search_tier="brave"`
  - 机器之心 (priority=1, Chinese AI News) → `search_tier="brave"`
  - Product Hunt AI (priority=3, Products) → `search_tier="brave"`

  **Standard 源 (DDG - remaining)**:
  - 量子位, GitHub Trending (all 3), The Batch → `search_tier="standard"`

  **Must NOT do**:
  - 不要修改现有源的其他属性
  - 不要把太多源标记为 premium

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1, Task 2

  **References**:
  - `ai_worker/config/curated_sources.py:25-53` - Source dataclass
  - `ai_worker/config/curated_sources.py:60-109` - AI_NEWS_SOURCES

  **Acceptance Criteria**:
  - [ ] Source dataclass 包含 `search_tier` 字段
  - [ ] 默认值为 `"standard"`
  - [ ] ~4 个源标记为 `"tavily"` (AI Research)
  - [ ] ~4 个源标记为 `"brave"` (News/Community)
  
  ```bash
  python -m py_compile ai_worker/config/curated_sources.py
  grep -c "search_tier" ai_worker/config/curated_sources.py
  ```

  **Commit**: YES (groups with 4)
  - Message: `feat(sources): add search_tier for premium routing`
  - Files: `ai_worker/config/curated_sources.py`

---

- [ ] 4. 修改 DailyBriefWorker 智能路由

  **What to do**:
  - 修改 `_fetch_curated_sources` 方法
  - 根据 source.search_tier 选择搜索工具
  - Premium 源: 使用 `use_premium=True`
  - Standard 源: 使用默认 DDG
  - 添加配额使用日志

  **代码修改位置**:
  ```python
  # 在 _fetch_curated_sources 中
  for source in scrape_sources:
      # ...
      tier = getattr(source, 'search_tier', 'standard')
      
      if tier == "tavily":
          result = await search_tool.execute(
              query=query, max_results=source.max_items,
              timelimit="d", use_premium=True
          )
          logger.info(f"[Tavily] {source.name}")
      elif tier == "brave":
          result = await brave_tool.execute(
              query=query, max_results=source.max_items
          )
          logger.info(f"[Brave] {source.name}")
      else:
          result = await search_tool.execute(
              query=query, max_results=source.max_items, timelimit="d"
          )
          logger.info(f"[DDG] {source.name}")
  ```

  **Must NOT do**:
  - 不要修改 Real-time APIs 逻辑 (已经免费)
  - 不要删除 fallback 逻辑

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1, Task 2

  **References**:
  - `ai_worker/workers/daily_brief_worker.py:367-410` - _fetch_curated_sources 中的 scrape 逻辑
  - `ai_worker/workers/daily_brief_worker.py:412-444` - search 逻辑

  **Acceptance Criteria**:
  - [ ] Tavily 源使用 `use_premium=True`
  - [ ] Brave 源使用 BraveSearchTool
  - [ ] Standard 源使用 DDG
  - [ ] 日志显示 `[Tavily]` / `[Brave]` / `[DDG]`
  
  ```bash
  python -m py_compile ai_worker/workers/daily_brief_worker.py
  grep -n "use_premium" ai_worker/workers/daily_brief_worker.py
  ```

  **Commit**: YES (groups with 3)
  - Message: `feat(dailybrief): implement smart search routing by tier`
  - Files: `ai_worker/workers/daily_brief_worker.py`

---

- [ ] 5. 端到端验证

  **What to do**:
  - 测试 BraveSearchTool 单独可用
  - 测试 WebSearchTool 默认使用 DDG
  - 运行 DailyBrief 检查日志
  - 确认 premium 源使用正确的搜索引擎

  **验证命令**:
  ```bash
  # 1. Brave 单独测试
  python -c "
  import asyncio
  from ai_worker.tools.brave_search import BraveSearchTool
  tool = BraveSearchTool()
  r = asyncio.run(tool.execute(query='OpenAI latest news', max_results=2))
  print('Brave:', 'OK' if r.success else r.error)
  "

  # 2. DDG 默认测试  
  python -c "
  import asyncio
  from ai_worker.tools.web_search import WebSearchTool
  tool = WebSearchTool()  # 无 tavily_api_key
  r = asyncio.run(tool.execute(query='test query', max_results=2))
  print('DDG default:', 'OK' if r.success else r.error)
  "

  # 3. 完整 Brief 测试
  python -c "
  import asyncio
  import logging
  logging.basicConfig(level=logging.INFO)
  from ai_worker.workers.daily_brief_worker import DailyBriefWorker
  from ai_worker.llm.openai_client import OpenAIClient
  from ai_worker.config import get_settings
  
  async def test():
      s = get_settings()
      w = DailyBriefWorker(OpenAIClient(s.openai))
      r = await w.generate_brief()
      print('Report:', r.extras.get('file_path'))
  
  asyncio.run(test())
  " 2>&1 | grep -E "(Premium|DDG|Brave|Search)"
  ```

  **Must NOT do**:
  - 不要修改任何代码
  - 不要跳过验证步骤

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Parallel Group**: Wave 3 (final)
  - **Blocked By**: Task 3, Task 4

  **Acceptance Criteria**:
  - [ ] Brave 单独调用成功
  - [ ] WebSearchTool 默认使用 DDG
  - [ ] Brief 日志显示正确的搜索路由
  - [ ] Premium 源使用 Tavily/Brave

  **Commit**: NO (验证任务)

---

## 配额预算分析

### 优化后的配额分配 (Higher Premium Usage)

| 搜索引擎 | 月配额 | 每次 Brief 消耗 | 155 次 Brief 总消耗 | 状态 |
|---------|-------|----------------|-------------------|------|
| **DDG** | ∞ | ~6 次 | ~930 次 | ✅ 无限制 |
| **Tavily** | 1,000 | ~3 次 (AI Research) | ~465 次 | ✅ 余量 535 |
| **Brave** | 2,000 | ~3 次 (News/Community) | ~465 次 | ✅ 余量 1,535 |

### 每次 Brief 搜索分布

| 类型 | 调用数 | 使用引擎 |
|------|-------|---------| 
| Real-time APIs (HN/Reddit/GitHub) | 7 | 免费 API |
| AI Research (OpenAI/Anthropic/DeepMind/HF) | ~3 | Tavily |
| News/Community (PWC/AIBase/机器之心/PH) | ~3 | Brave |
| Standard (GitHub/量子位/TheBatch等) | ~6 | DDG |

---

## Commit Strategy

| After Task | Message | Files |
|------------|---------|-------|
| 1 | `refactor(search): prioritize DDG, Tavily as premium` | web_search.py |
| 2 | `feat(search): add BraveSearchTool` | brave_search.py |
| 3+4 | `feat(dailybrief): implement tiered search routing` | curated_sources.py, daily_brief_worker.py |

---

## Success Criteria

### Final Checklist
- [ ] DDG 是默认搜索引擎
- [ ] Brave API 集成可用
- [ ] Premium 源使用 Tavily
- [ ] Standard 源使用 DDG
- [ ] 日志显示搜索路由决策
- [ ] 155 次/月 Brief 配额可持续
