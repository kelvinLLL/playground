# PPTX 能力对比实验: Generalist vs Specialist

## TL;DR

> **Quick Summary**: 验证专用 OfficeWorker（麦肯锡顾问角色）vs 通用 DefaultWorker 生成 PPT 的质量差异。通过 Shell 调用集成 Node.js PPTX 工具链。
> 
> **Deliverables**:
> - PPTXSkill 类（封装 html2pptx.js 工具）
> - OfficeWorker 类（麦肯锡顾问 System Prompt）
> - 增强的 Logging 输出
> - 两组对比生成的技术方案汇报 PPT
> 
> **Estimated Effort**: Medium (4-6 小时)
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: Task 1 → Task 3 → Task 5 → Task 6

---

## Context

### Original Request
用户想测试 PPTX 能力，对比两种架构：
1. 直接用 DefaultWorker 基础能力进行 PPT 生成
2. 专门构建的 pptx worker/工作能力相关的 worker

### Interview Summary
**Key Discussions**:
- Node.js 集成: 通过 Shell subprocess 调用（符合 SKILL.md 设计）
- OfficeWorker 角色: 麦肯锡顾问（结构化思维、金字塔原理、MECE）
- 评估方式: 人工对比（结构、美观、内容质量）
- 测试主题: 技术方案汇报 PPT

**Research Findings**:
- PPTX Skill 已放置在 `ai_worker/skills/local/pptx/`
- 主要工具: html2pptx.js (Node.js), replace.py, thumbnail.py
- 现有 Worker 架构支持 Skills + Tools 组合
- notifier pattern 已存在，可用于进度通知

### Self Gap Analysis (Metis 不可用)
**Identified Gaps** (已解决):
1. Node.js 依赖安装验证 → 添加到 Task 1 验收标准
2. 输出目录管理 → 使用 `ai_worker/outputs/pptx/` 
3. 错误处理策略 → 工具失败时返回错误信息到 LLM

---

## Work Objectives

### Core Objective
验证专用 Worker 架构（OfficeWorker）是否比通用 Worker（DefaultWorker + Skill）产生更高质量的 PPT 输出。

### Concrete Deliverables
1. `ai_worker/skills/pptx.py` - PPTXSkill 类
2. `ai_worker/workers/office_worker.py` - OfficeWorker 类
3. `ai_worker/outputs/pptx/` - 测试输出目录
4. 两份对比 PPT: `default_worker_output.pptx`, `office_worker_output.pptx`

### Definition of Done
- [ ] DefaultWorker 能调用 PPTX Skill 生成 PPT
- [ ] OfficeWorker 能生成结构化的 PPT
- [ ] 两个 Worker 都有清晰的进度日志
- [ ] 生成的 PPT 可以正常打开

### Must Have
- Shell 调用 Node.js 脚本
- 麦肯锡顾问风格的 System Prompt
- 进度日志通知 (notifier pattern)
- 错误处理和用户友好提示

### Must NOT Have (Guardrails)
- 不要实现 Word/Excel 支持（未来扩展）
- 不要创建自动评分系统
- 不要修改现有 Worker 的行为
- 不要引入新的 LLM 依赖

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (现有 worker 测试模式)
- **User wants tests**: Manual-only (人工对比评估)
- **Framework**: N/A

### Manual Verification Procedures

**For PPTX Generation** (using Bash):
```bash
# 验证 PPT 文件存在且非空
ls -la ai_worker/outputs/pptx/*.pptx
# 验证文件可解压（PPTX 是 ZIP 格式）
unzip -t ai_worker/outputs/pptx/default_worker_output.pptx
```

**For Logging** (观察 console output):
```
# 期望看到类似日志:
📝 Starting presentation creation...
🎨 Designing slide 1: Title slide
📊 Creating slide 2: Problem Statement
✅ Presentation saved: output.pptx
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: PPTXSkill 基础实现 [no dependencies]
└── Task 2: 输出目录和依赖验证 [no dependencies]

Wave 2 (After Wave 1):
├── Task 3: OfficeWorker 实现 [depends: 1]
└── Task 4: DefaultWorker 集成 PPTXSkill [depends: 1]

Wave 3 (After Wave 2):
└── Task 5: Logging 增强 [depends: 3, 4]

Wave 4 (After Wave 3):
└── Task 6: 对比测试 [depends: 5]

Critical Path: Task 1 → Task 3 → Task 5 → Task 6
Parallel Speedup: ~35% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3, 4 | 2 |
| 2 | None | 6 | 1 |
| 3 | 1 | 5 | 4 |
| 4 | 1 | 5 | 3 |
| 5 | 3, 4 | 6 | None |
| 6 | 5 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | category="quick" or "unspecified-low" |
| 2 | 3, 4 | category="unspecified-low" |
| 3 | 5 | category="quick" |
| 4 | 6 | category="unspecified-low" |

---

## TODOs

- [ ] 1. 创建 PPTXSkill 类

  **What to do**:
  - 创建 `ai_worker/skills/pptx.py`
  - 实现 `PPTXSkill(BaseSkill)` 类
  - 创建 Tools 封装以下功能:
    - `create_presentation_from_html`: 调用 html2pptx.js 生成 PPT
    - `generate_thumbnail`: 调用 thumbnail.py 生成预览图
  - 每个 Tool 通过 `subprocess.run()` 调用脚本
  - 实现 `get_instructions()` 返回 SKILL.md 的关键指导

  **Must NOT do**:
  - 不要封装所有脚本（只封装创作相关的）
  - 不要修改原始 SKILL.md 或脚本

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 标准 Python 类实现，无复杂逻辑
  - **Skills**: [`git-master`]
    - `git-master`: 需要创建新文件并可能提交

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: None (can start immediately)

  **References**:
  
  **Pattern References** (existing code to follow):
  - `ai_worker/skills/base.py:37-106` - BaseSkill 基类，需要继承 metadata, get_tools(), get_instructions()
  - `ai_worker/skills/browser.py` - 类似的 Skill 实现模式
  - `ai_worker/skills/search.py` - Tool 注册和组织模式

  **API/Type References**:
  - `ai_worker/tools/base.py:BaseTool` - Tool 基类
  - `ai_worker/skills/base.py:SkillMetadata` - 元数据定义

  **Documentation References**:
  - `ai_worker/skills/local/pptx/SKILL.md:1-60` - PPTX Skill 概述和功能说明
  - `ai_worker/skills/local/pptx/SKILL.md:47-170` - html2pptx workflow 详细说明
  - `ai_worker/skills/local/pptx/html2pptx.md` - html2pptx.js 使用指南

  **Script References** (需要封装的脚本):
  - `ai_worker/skills/local/pptx/scripts/html2pptx.js` - 主要的 HTML 转 PPT 脚本
  - `ai_worker/skills/local/pptx/scripts/thumbnail.py` - 缩略图生成

  **WHY Each Reference Matters**:
  - `base.py` 定义了 Skill 必须实现的接口
  - `browser.py` 展示了如何组织多个 Tools
  - `SKILL.md` 包含了用户使用这些工具的完整工作流程

  **Acceptance Criteria**:
  - [ ] `ai_worker/skills/pptx.py` 文件存在
  - [ ] 类继承 `BaseSkill` 并实现所有抽象方法
  - [ ] `get_tools()` 返回至少 2 个工具
  - [ ] `get_instructions()` 返回非空字符串
  
  ```bash
  # 验证文件语法正确
  python -m py_compile ai_worker/skills/pptx.py
  # 验证可以导入
  python -c "from ai_worker.skills.pptx import PPTXSkill; s = PPTXSkill(); print(s.metadata.name)"
  # 期望输出: PPTX
  ```

  **Commit**: YES
  - Message: `feat(skills): add PPTXSkill for presentation generation`
  - Files: `ai_worker/skills/pptx.py`
  - Pre-commit: `python -m py_compile ai_worker/skills/pptx.py`

---

- [ ] 2. 设置输出目录和验证依赖

  **What to do**:
  - 创建 `ai_worker/outputs/pptx/` 目录
  - 创建 `ai_worker/outputs/pptx/.gitkeep`
  - 验证 Node.js 依赖已安装 (pptxgenjs, playwright, sharp)
  - 验证 Python 依赖已安装 (python-pptx, markitdown)
  - 如有缺失，添加到 requirements.txt 并安装

  **Must NOT do**:
  - 不要安装非必要的依赖
  - 不要修改全局 Node.js 配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的目录创建和依赖检查
  - **Skills**: []
    - 无需特殊技能

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 6
  - **Blocked By**: None

  **References**:
  
  **Documentation References**:
  - `ai_worker/skills/local/pptx/SKILL.md:472-484` - 依赖列表

  **Acceptance Criteria**:
  ```bash
  # 验证目录存在
  ls -la ai_worker/outputs/pptx/
  # 验证 Node.js 依赖
  npm list -g pptxgenjs
  npm list -g playwright
  npm list -g sharp
  # 验证 Python 依赖
  pip show python-pptx markitdown
  ```
  - [ ] 目录 `ai_worker/outputs/pptx/` 存在
  - [ ] Node.js 依赖已安装
  - [ ] Python 依赖已安装

  **Commit**: YES (groups with 1)
  - Message: `chore: add pptx output directory and verify dependencies`
  - Files: `ai_worker/outputs/pptx/.gitkeep`
  - Pre-commit: N/A

---

- [ ] 3. 创建 OfficeWorker

  **What to do**:
  - 创建 `ai_worker/workers/office_worker.py`
  - 实现 `OfficeWorker(BaseWorker)` 类
  - 设计麦肯锡顾问风格的 System Prompt:
    - 强调金字塔原理（结论先行）
    - MECE 框架（相互独立、完全穷尽）
    - 每页一个核心信息
    - 先规划大纲再创作
  - 加载 PPTXSkill
  - 使用 LLM function calling 执行工具

  **Must NOT do**:
  - 不要实现 Word/Excel 功能
  - 不要修改 GameWorker 或其他现有 Worker

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Worker 实现，需要理解现有模式
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **References**:
  
  **Pattern References** (existing code to follow):
  - `ai_worker/workers/base.py:27-147` - BaseWorker 基类定义
  - `ai_worker/workers/game_worker.py:22-114` - 专用 Worker 实现示例（简洁版）
  - `ai_worker/workers/default.py:62-160` - 带 function calling 的 Worker（复杂版）

  **API/Type References**:
  - `ai_worker/workers/base.py:WorkerConfig` - Worker 配置
  - `ai_worker/llm/base.py:BaseLLM, Message, ToolDefinition, ToolCall` - LLM 类型

  **Documentation References**:
  - `ai_worker/skills/local/pptx/SKILL.md:47-100` - 设计原则（颜色、布局、排版）

  **WHY Each Reference Matters**:
  - `game_worker.py` 展示了一个简洁的专用 Worker 模式
  - `default.py` 展示了如何使用 function calling
  - `SKILL.md` 中的设计原则应该融入 System Prompt

  **Acceptance Criteria**:
  - [ ] `ai_worker/workers/office_worker.py` 文件存在
  - [ ] 类继承 `BaseWorker`
  - [ ] System Prompt 包含金字塔原理、MECE 关键词
  - [ ] 实现 `process()` 方法
  
  ```bash
  # 验证语法
  python -m py_compile ai_worker/workers/office_worker.py
  # 验证导入
  python -c "from ai_worker.workers.office_worker import OfficeWorker; print('OK')"
  ```

  **Commit**: YES
  - Message: `feat(workers): add OfficeWorker for presentation creation`
  - Files: `ai_worker/workers/office_worker.py`
  - Pre-commit: `python -m py_compile ai_worker/workers/office_worker.py`

---

- [ ] 4. 集成 PPTXSkill 到 DefaultWorker

  **What to do**:
  - 修改 `ai_worker/workers/default.py`
  - 在 `__init__` 的 skills 列表中添加 `PPTXSkill()`
  - 导入 `from ai_worker.skills.pptx import PPTXSkill`

  **Must NOT do**:
  - 不要修改其他 Skills 的加载逻辑
  - 不要修改 Router 逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 只是添加一行导入和一行初始化
  - **Skills**: [`git-master`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 3)
  - **Blocks**: Task 5
  - **Blocked By**: Task 1

  **References**:
  
  **Pattern References** (exact location to modify):
  - `ai_worker/workers/default.py:27-31` - 现有 Skill 导入区域
  - `ai_worker/workers/default.py:88-94` - skills 列表初始化

  **Acceptance Criteria**:
  - [ ] `PPTXSkill` 已添加到导入
  - [ ] `PPTXSkill()` 已添加到 self.skills 列表
  
  ```bash
  # 验证导入不报错
  python -c "from ai_worker.workers.default import DefaultWorker; print('OK')"
  # 验证 PPTXSkill 已添加到导入列表 (静态检查)
  grep -n "PPTXSkill" ai_worker/workers/default.py
  # 期望看到: 导入行和 self.skills 列表中都有 PPTXSkill
  ```

  **Commit**: YES (groups with 3)
  - Message: `feat(workers): integrate PPTXSkill into DefaultWorker`
  - Files: `ai_worker/workers/default.py`
  - Pre-commit: `python -m py_compile ai_worker/workers/default.py`

---

- [ ] 5. 增强 Logging 输出

  **What to do**:
  - 在 PPTXSkill 的工具执行中添加详细日志
  - 使用 notifier pattern 发送进度更新
  - 日志格式示例:
    ```
    📝 开始创建演示文稿...
    🎨 设计第 1 页: 标题页
    📊 创建第 2 页: 问题陈述
    ✅ 演示文稿已保存: output.pptx
    ```
  - 在 OfficeWorker 中添加类似的进度日志
  - 确保错误信息用户友好

  **Must NOT do**:
  - 不要删除现有的 logging 调用
  - 不要使用 print() 替代 logging

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 添加日志语句
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Task 6
  - **Blocked By**: Task 3, Task 4

  **References**:
  
  **Pattern References**:
  - `ai_worker/workers/default.py:349-350` - notifier 使用模式
  - `ai_worker/workers/game_worker.py:73-82` - 进度通知示例
  - `ai_worker/main.py:195-213` - progress_notifier 实现

  **Acceptance Criteria**:
  - [ ] PPTXSkill 工具执行时发送进度通知
  - [ ] OfficeWorker 在关键步骤发送通知
  - [ ] 日志包含 emoji 前缀提高可读性
  - [ ] 错误信息清晰说明问题

  **Commit**: YES
  - Message: `feat(logging): enhance PPTX generation progress notifications`
  - Files: `ai_worker/skills/pptx.py`, `ai_worker/workers/office_worker.py`
  - Pre-commit: `flake8 ai_worker/skills/pptx.py ai_worker/workers/office_worker.py`

---

- [ ] 6. 对比测试

  **What to do**:
  - 创建测试脚本 `test_pptx_comparison.py`
  - 测试 Prompt: "创建一个技术方案汇报 PPT，主题是 'AI 驱动的智能客服系统架构设计'，包含：问题背景、技术方案、系统架构、实施计划、预期效果"
  - **⚠️ 只生成 2 个 PPT (节省 token)**: 
    - `default_worker_output.pptx` (DefaultWorker 生成)
    - `office_worker_output.pptx` (OfficeWorker 生成)
  - 输出保存到 `ai_worker/outputs/pptx/`
  - 生成缩略图便于快速对比

  **Must NOT do**:
  - 不要实现自动评分
  - 不要修改核心代码
  - **不要生成超过 2 个 PPT** (避免消耗过多 token)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 需要理解 Worker 使用方式，编写测试脚本
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (final)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 5

  **References**:
  
  **Pattern References**:
  - `ai_worker/main.py:162-176` - 如何构造 StandardMessage 并调用 Worker
  - `ai_worker/workers/game_worker.py:62-113` - Worker.process() 调用模式

  **Test References**:
  - `ai_worker/test_workers.py` - 现有测试模式（如果存在）

  **Acceptance Criteria**:
  - [ ] `test_pptx_comparison.py` 脚本存在
  - [ ] 运行后生成两个 PPT 文件
  - [ ] 两个 PPT 文件都能正常打开
  
  ```bash
  # 运行测试
  python test_pptx_comparison.py
  # 验证输出
  ls -la ai_worker/outputs/pptx/*.pptx
  # 验证文件完整性
  unzip -t ai_worker/outputs/pptx/default_worker_output.pptx
  unzip -t ai_worker/outputs/pptx/office_worker_output.pptx
  ```

  **Evidence to Capture**:
  - [ ] Console 日志截图（展示 Logging 效果）
  - [ ] 两个 PPT 文件
  - [ ] 缩略图对比（如果生成）

  **Commit**: YES
  - Message: `test: add PPTX comparison test script`
  - Files: `test_pptx_comparison.py`
  - Pre-commit: N/A

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1+2 | `feat(skills): add PPTXSkill and output directory` | pptx.py, .gitkeep | py_compile |
| 3+4 | `feat(workers): add OfficeWorker and integrate PPTXSkill` | office_worker.py, default.py | py_compile |
| 5 | `feat(logging): enhance PPTX generation progress notifications` | pptx.py, office_worker.py | flake8 |
| 6 | `test: add PPTX comparison test script` | test_pptx_comparison.py | run test |

---

## Success Criteria

### Verification Commands
```bash
# 验证所有新文件语法正确
python -m py_compile ai_worker/skills/pptx.py
python -m py_compile ai_worker/workers/office_worker.py
python -m py_compile ai_worker/workers/default.py

# 运行对比测试
python test_pptx_comparison.py

# 验证输出存在
ls -la ai_worker/outputs/pptx/*.pptx

# 验证 PPT 完整性
unzip -t ai_worker/outputs/pptx/default_worker_output.pptx
unzip -t ai_worker/outputs/pptx/office_worker_output.pptx
```

### Final Checklist
- [ ] PPTXSkill 能被 DefaultWorker 加载和使用
- [ ] OfficeWorker 能独立生成 PPT
- [ ] 两个 Worker 都有清晰的进度日志
- [ ] 生成的 PPT 可以正常打开
- [ ] 无 Word/Excel 相关代码（Guardrail）
- [ ] 无自动评分系统（Guardrail）
