# MemU Workflow Design & Management

This document explains the "Workflow Engine" within MemU, detailing how pipelines (Memorize, Retrieve RAG, Retrieve LLM) are constructed, managed, and executed.

## 1. Core Concepts

MemU treats every major operation as a **Workflow**. A workflow is a sequence of **Steps** that transform a shared **State**.

### 1.1. The Building Blocks

*   **`WorkflowState` (`dict[str, Any]`)**: A shared dictionary that holds all data (e.g., `original_query`, `found_items`, `database_connection`). Every step reads from and writes to this state.
*   **`WorkflowStep`**: A single unit of logic (e.g., "Summarize Text", "Vector Search").
    *   **`handler`**: The async function to execute.
    *   **`requires`**: Keys that *must* exist in `state` before running.
    *   **`produces`**: Keys that this step *will add* to `state`.
*   **`PipelineManager`**: The registry that stores workflow definitions (lists of steps).
*   **`WorkflowRunner`**: The engine that executes the steps.

---

## 2. Workflow Management (`PipelineManager`)

The `PipelineManager` (`src/memu/workflow/pipeline.py`) is the central authority.

### 2.1. Registration
Workflows are registered at startup in `MemoryService.__init__`.

```python
# src/memu/app/service.py

self.pipeline_manager.register(
    "memorize",
    self._build_memorize_workflow(),
    initial_state_keys=self._list_memorize_initial_keys(),
)

self.pipeline_manager.register(
    "retrieve_rag",
    self._build_rag_retrieve_workflow(),
    initial_state_keys=self._list_retrieve_initial_keys(),
)
# ... same for "retrieve_llm"
```

### 2.2. Dynamic Modification (The "Magic")
The `PipelineManager` allows **runtime modification** of workflows. This is powerful for users who want to inject custom logic without forking the library.

*   `insert_after(name, target_step_id, new_step)`
*   `insert_before(...)`
*   `replace_step(...)`
*   `remove_step(...)`
*   `config_step(...)`: Modify a step's configuration (e.g., change the LLM model for the "Summarize" step).

**Example Scenario**:
> "I want to add a 'Sensitive Data Filter' step right after text extraction in the `memorize` workflow."
>
> You can do this by calling `service.pipeline_manager.insert_after("memorize", "extract_text", my_filter_step)`.

---

## 3. Workflow Execution (`WorkflowRunner`)

MemU uses a `WorkflowRunner` to execute pipelines. The default is `LocalWorkflowRunner` (`src/memu/workflow/runner.py`), which runs steps **sequentially** and **asynchronously** (using `await`).

### 3.1. Execution Flow

When you call `memory.memorize(...)` or `memory.retrieve(...)`:

1.  **Prepare Initial State**: The service method creates the initial `WorkflowState` dictionary (e.g., putting `resource_url` into it).
2.  **Resolve Runner**: It gets the `LocalWorkflowRunner`.
3.  **Run Steps Loop**:
    *   The runner iterates through the list of `WorkflowStep`s.
    *   **Validation**: Checks if `requires` keys exist in `state`. If not, raises `KeyError`.
    *   **Interceptors (Hooks)**:
        *   `run_before_interceptors`: Pre-step hooks (logging, blocking).
        *   `step.run(state)`: **The actual logic execution.**
        *   `run_after_interceptors`: Post-step hooks (metrics, tracing).
        *   `run_on_error_interceptors`: Error handling.
    *   **State Update**: The return value of `step.run` (a dict) is **merged** into the global `state`.

### 3.2. Sync vs Async

*   **Concurrency**: The steps within a *single* workflow run **sequentially** (Step 1 -> Step 2 -> Step 3).
    *   *Why?* Because Step 2 usually depends on data produced by Step 1.
*   **Parallelism**: Since `run_steps` is an `async` function, **multiple workflows can run in parallel** if the user calls them concurrently (e.g., processing 5 documents at once).
*   **IO Bound**: Most steps are IO-bound (LLM API calls, DB queries), so Python's `asyncio` handles concurrency efficiently.

---

## 4. The Three Main Workflows

### 4.1. `memorize` Workflow
*   **Goal**: Ingest data -> Create structured memory.
*   **Structure**: Linear pipeline.
*   **Steps**:
    1.  `ingest_resource`: Download/Read file.
    2.  `preprocess_multimodal`: Transcribe audio / Extract video frames.
    3.  `extract_items`: **LLM** extracts facts (Profile, Events).
    4.  `categorize_items`: **Vector** embedding + Clustering.
    5.  `persist_index`: Update category summaries (LLM).
    6.  `build_response`: Format output.

### 4.2. `retrieve_rag` Workflow
*   **Goal**: Fast, cost-effective retrieval using Vector Search.
*   **Structure**: Recursive / Conditional pipeline (using `sufficiency_check`).
*   **Steps**:
    1.  `route_intention`: **LLM** decides "Do we need to search?".
    2.  `route_category`: **Vector** search for categories.
    3.  `sufficiency_check`: **LLM** checks "Is category info enough?". **(Early Exit)**
    4.  `recall_items`: **Vector** search for specific items.
    5.  `sufficiency_check`: **LLM** checks again. **(Early Exit)**
    6.  `recall_resources`: **Vector** search for raw docs.
    7.  `build_context`: Aggregate results.

### 4.3. `retrieve_llm` Workflow
*   **Goal**: High-precision, reasoning-heavy retrieval using LLM Ranking.
*   **Structure**: Same steps as RAG, but different handlers.
*   **Steps**:
    1.  `route_intention`: Same.
    2.  `route_category`: **LLM** ranks categories (Listwise Ranking).
    3.  `sufficiency_check`: Same.
    4.  `recall_items`: **LLM** ranks items (Listwise Ranking).
    5.  `sufficiency_check`: Same.
    6.  `recall_resources`: **LLM** ranks resources.
    7.  `build_context`: Same.

---

## 5. Key Design Patterns

1.  **Explicit Data Flow**:
    *   Every step declares what it needs (`requires`) and what it gives (`produces`). This makes the data flow transparent and self-documenting.

2.  **State Accumulation**:
    *   The `state` dict grows as the workflow progresses.
    *   Step 1 adds `text`, Step 2 adds `summary`, Step 3 adds `embedding`.
    *   Final step just picks what it needs from the accumulated state to build the response.

3.  **Interceptor System (Observability)**:
    *   `src/memu/workflow/interceptor.py`
    *   Allows "Sidecar" logic: Logging token usage, tracing execution time, or even modifying state *between* steps without touching the step logic itself.

4.  **Configuration Injection**:
    *   Each step has a `config` dict.
    *   The `PipelineManager.config_step` method allows you to change these configs at runtime (e.g., swapping the LLM model for a specific step).
