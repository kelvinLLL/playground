# DailyBriefWorker 全面优化

## TL;DR

> **Quick Summary**: 优化 DailyBriefWorker 的内容新鲜度、数据源覆盖和报告格式。新增 Reddit 数据源，重构报告为 "简报 + 附录 + Sources" 三段式结构。
> 
> **Deliverables**:
> - 更新的 System Prompt 和 Editorial Prompt（强化 24h 新鲜度）
> - 新增 3 个 Reddit 数据源（algotrading, ChatGPT, startups）
> - 重构的报告格式（Brief + Appendix + Sources）
> - 优化的 token 消耗控制
> 
> **Estimated Effort**: Medium (3-5 小时)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 → Task 3 → Task 5 → Task 6

---

## Context

### Original Request
用户希望全面优化 DailyBriefWorker，解决以下问题：
1. 内容过时 - 报告中出现旧新闻
2. 缺少重要新闻 - 覆盖不全面
3. 报告质量不高 - LLM 综合效果需改进
4. 数据源不够 - 需要更多来源
5. 格式可美化 - Markdown 结构需改进

### Interview Summary
**Key Discussions**:
- X/Twitter: 跳过，不在本次范围内
- Reddit 扩展: 新增 r/algotrading, r/ChatGPT, r/startups
- Token 预算: 平衡模式（80-120K tokens）
- 报告格式: 简报 + 附录（保留原始信息）

**Research Findings**:
- `curated_sources.py` 已有完整的数据源配置系统（501行）
- `realtime_sources.py` 的 HN/Reddit/GitHub 工具已有服务端时间过滤
- 当前报告格式是单一 Markdown，没有附录部分

### Self Gap Analysis (Metis 不可用)
**Identified Gaps** (已解决):
1. max_items 控制 → 在 curated_sources.py 中调整
2. 附录格式规范 → 定义清晰的 Markdown 结构
3. Sources 提取逻辑 → 复用现有 `_extract_links_from_report`

---

## Work Objectives

### Core Objective
优化 DailyBriefWorker 的信息质量和报告格式，确保内容新鲜、覆盖全面、格式美观。

### Concrete Deliverables
1. 更新的 `daily_brief_worker.py` - System Prompt 和 Editorial Prompt
2. 更新的 `curated_sources.py` - 新增 Reddit 数据源
3. 更新的 `realtime_sources.py` - 新增 subreddit 支持
4. 重构的报告生成逻辑 - Brief + Appendix + Sources 格式

### Definition of Done
- [x] 报告严格过滤 24 小时以外的内容
- [x] 新增的 3 个 Reddit 社区数据正常获取
- [x] 报告包含 Brief、Appendix、Sources 三部分
- [x] 原始采集数据完整保留在附录中
- [x] Token 消耗在合理范围内

### Must Have
- 24h 新鲜度强制过滤
- 新 Reddit 数据源接入
- 三段式报告格式
- 原始数据保留

### Must NOT Have (Guardrails)
- 不接入 X/Twitter
- 不添加配置化 UI
- 不修改 RealtimeIntelSkill 的核心逻辑
- 不引入新的依赖库
- 不生成 PDF/HTML 等其他格式

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (无自动化测试)
- **User wants tests**: Manual-only
- **Framework**: N/A

### Manual Verification Procedures

**For Report Generation** (using Bash):
```bash
# 运行 Daily Brief 生成
python -c "
import asyncio
from ai_worker.workers.daily_brief_worker import DailyBriefWorker
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.config import get_settings

async def test():
    settings = get_settings()
    llm = OpenAIClient(settings.openai)
    worker = DailyBriefWorker(llm)
    result = await worker.generate_brief()
    print(f'Report generated: {result.extras.get(\"file_path\")}')

asyncio.run(test())
"

# 验证报告结构包含三部分
grep -E "^## (🔥|📋|📚)" ai_worker/reports/daily_brief_*.md | head -10
```

**For New Reddit Sources** (验证数据获取):
```bash
python -c "
import asyncio
from ai_worker.tools.realtime_sources import RedditDailyTool

async def test():
    tool = RedditDailyTool()
    for sub in ['algotrading', 'ChatGPT', 'startups']:
        result = await tool.execute(subreddit=sub, max_results=3)
        print(f'{sub}: {\"OK\" if result.success else result.error}')

asyncio.run(test())
"
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: 更新 System Prompt 和 Editorial Prompt [no dependencies]
└── Task 2: 新增 Reddit 数据源配置 [no dependencies]

Wave 2 (After Wave 1):
├── Task 3: 重构报告格式 (_phase_editorial) [depends: 1]
└── Task 4: 更新 _fetch_realtime_sources 调用新 subreddits [depends: 2]

Wave 3 (After Wave 2):
└── Task 5: 优化 token 控制和 max_items [depends: 3, 4]

Wave 4 (After Wave 3):
└── Task 6: 端到端验证 [depends: 5]

Critical Path: Task 1 → Task 3 → Task 5 → Task 6
Parallel Speedup: ~30% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3 | 2 |
| 2 | None | 4 | 1 |
| 3 | 1 | 5 | 4 |
| 4 | 2 | 5 | 3 |
| 5 | 3, 4 | 6 | None |
| 6 | 5 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | category="quick" |
| 2 | 3, 4 | category="unspecified-low" |
| 3 | 5 | category="quick" |
| 4 | 6 | category="quick" |

---

## TODOs

- [x] 1. 更新 System Prompt 和 Editorial Prompt
- [x] 2. 新增 Reddit 数据源配置
- [x] 3. 重构报告格式 (Brief + Appendix + Sources)
- [x] 4. 更新 _fetch_realtime_sources 调用新 subreddits
- [x] 5. 优化 token 控制
- [x] 6. 端到端验证

  **What to do**:
  - 运行完整的 Daily Brief 生成流程
  - 验证报告包含所有预期部分
  - 检查新 Reddit 数据是否正常获取
  - 确认报告格式正确

  **验证步骤**:
  ```bash
  # 1. 测试新 Reddit 源
  python -c "
  import asyncio
  from ai_worker.tools.realtime_sources import RedditDailyTool

  async def test():
      tool = RedditDailyTool()
      for sub in ['algotrading', 'ChatGPT', 'startups']:
          result = await tool.execute(subreddit=sub, max_results=3)
          print(f'{sub}: {\"✓\" if result.success else \"✗ \" + str(result.error)}')

  asyncio.run(test())
  "

  # 2. 生成完整报告
  python -c "
  import asyncio
  from ai_worker.workers.daily_brief_worker import DailyBriefWorker
  from ai_worker.llm.openai_client import OpenAIClient
  from ai_worker.config import get_settings

  async def test():
      settings = get_settings()
      llm = OpenAIClient(settings.openai)
      worker = DailyBriefWorker(llm)
      result = await worker.generate_brief()
      print(f'Report: {result.extras.get(\"file_path\")}')

  asyncio.run(test())
  "

  # 3. 验证报告结构
  ls -la ai_worker/reports/daily_brief_*.md | tail -1
  # 检查最新报告是否包含 Appendix 和 Sources
  grep -c "Appendix\|Sources\|附录\|信息来源" ai_worker/reports/daily_brief_*.md | tail -1
  ```

  **Must NOT do**:
  - 不要修改任何代码
  - 不要跳过任何验证步骤

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 只是运行验证命令
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 5

  **References**:
  
  **Pattern References**:
  - `ai_worker/reports/` - 报告输出目录

  **Acceptance Criteria**:
  - [ ] 3 个新 Reddit 源测试通过
  - [ ] 完整报告生成成功
  - [ ] 报告包含 Appendix 部分
  - [ ] 报告包含 Sources 部分
  - [ ] 无 Python 错误

  **Evidence to Capture**:
  - [ ] 验证命令的输出日志
  - [ ] 生成的报告文件

  **Commit**: NO (验证任务)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1+2 | `feat(dailybrief): improve freshness and add new sources` | daily_brief_worker.py, curated_sources.py | py_compile |
| 3+4 | `feat(dailybrief): restructure report format with appendix` | daily_brief_worker.py | py_compile |
| 5 | `perf(dailybrief): optimize token usage` | daily_brief_worker.py | py_compile |

---

## Success Criteria

### Verification Commands
```bash
# 验证所有修改文件语法正确
python -m py_compile ai_worker/workers/daily_brief_worker.py
python -m py_compile ai_worker/config/curated_sources.py

# 测试新 Reddit 源
python -c "
import asyncio
from ai_worker.tools.realtime_sources import RedditDailyTool
async def test():
    tool = RedditDailyTool()
    for sub in ['algotrading', 'ChatGPT', 'startups']:
        r = await tool.execute(subreddit=sub, max_results=2)
        print(f'{sub}: OK' if r.success else f'{sub}: FAIL')
asyncio.run(test())
"

# 生成测试报告
python -c "
import asyncio
from ai_worker.workers.daily_brief_worker import DailyBriefWorker
from ai_worker.llm.openai_client import OpenAIClient
from ai_worker.config import get_settings

async def main():
    s = get_settings()
    w = DailyBriefWorker(OpenAIClient(s.openai))
    r = await w.generate_brief()
    print(r.extras.get('file_path'))

asyncio.run(main())
"
```

### Final Checklist
- [x] 报告只包含 24 小时内的新闻
- [x] 新增 3 个 Reddit 社区数据正常获取
- [x] 报告包含 Brief + Appendix + Sources 三部分
- [x] 原始采集数据在附录中保留
- [x] Token 消耗在平衡范围内
- [x] 无 X/Twitter 相关代码（Guardrail）
- [x] 无配置化 UI 代码（Guardrail）
