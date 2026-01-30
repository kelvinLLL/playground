# MemU Implementation Deep Dive

This document contains a detailed code walkthrough of the MemU project, focusing on its architecture, implementation details, and key components.

## 1. Architecture Overview

MemU is designed as a modular, proactive memory system for AI agents. Its architecture separates concerns into distinct layers:

1.  **Service Layer (`src/memu/app/service.py`)**: The main entry point (`MemoryService`). It orchestrates operations but delegates specific logic to Mixins and Workflows.
2.  **Workflow Engine (`src/memu/workflow/`)**: A flexible pipeline system that executes tasks as a sequence of steps. This allows for dynamic reconfiguration and extension of memory processes.
3.  **Business Logic (`src/memu/app/`)**: Implemented as Mixins (`MemorizeMixin`, `RetrieveMixin`) that define the specific workflows (e.g., "memorize", "retrieve_rag").
4.  **Database Layer (`src/memu/database/`)**: A repository-based abstraction for storage. It supports pluggable backends (SQLite, Postgres) and handles vector search.
5.  **LLM Layer (`src/memu/llm/`)**: A unified interface for LLM interactions, featuring a robust interceptor system for observability and control.

---

## 2. Core Components

### 2.1. MemoryService
Located in `src/memu/app/service.py`, `MemoryService` is the central class.
- **Inheritance**: It inherits from `MemorizeMixin`, `RetrieveMixin`, and `CRUDMixin`, effectively combining all capabilities.
- **Initialization**:
    - Configures LLM profiles and database connections.
    - Initializes the `PipelineManager`.
    - Registers default pipelines (e.g., "memorize", "retrieve_rag").
- **Lazy Loading**: LLM clients are initialized lazily (`_get_llm_client`) to avoid overhead at startup.

### 2.2. The Workflow Engine
The workflow engine (`src/memu/workflow/`) is a standout feature, enabling a "Pipeline-as-Code" approach.

- **`WorkflowStep`**: Represents a single unit of work.
    - `handler`: The function to execute.
    - `requires`: Input keys expected in the state.
    - `produces`: Output keys added to the state.
    - This explicit dependency declaration allows for validation and easier debugging.
- **`PipelineManager`**: Manages pipeline definitions and revisions.
    - Supports runtime modification: `insert_after`, `replace_step`, `remove_step`.
    - This is crucial for customizing behavior without changing the core library code.
- **`WorkflowRunner`**: Executes the steps. The default `LocalWorkflowRunner` executes steps sequentially in the current process.

---

## 3. The Memorization Pipeline

The `memorize` workflow (defined in `MemorizeMixin._build_memorize_workflow`) transforms raw data into structured memory.

### Step-by-Step Flow:
1.  **`ingest_resource`**:
    - **Input**: `resource_url`, `modality`.
    - **Action**: Uses `LocalFS` to fetch the file content.
    - **Output**: `local_path`, `raw_text`.
2.  **`preprocess_multimodal`**:
    - **Action**: Handles specific modalities (Audio -> Transcribe, Video -> Frame Extraction + Vision API).
    - **Detail**: Uses `_preprocess_resource_url` to dispatch to specific handlers like `_preprocess_video` or `_preprocess_audio`.
3.  **`extract_items`**:
    - **Action**: The core intelligence step. Uses LLM to extract structured facts (Profile, Events, etc.).
    - **Prompting**: Uses modular prompts (`src/memu/prompts/memory_type/`) and expects XML output for robust parsing.
    - **Output**: `resource_plans` containing structured entries.
4.  **`categorize_items`**:
    - **Action**: Generates embeddings for items and links them to categories.
    - **Detail**: Calls `_persist_memory_items` which creates `MemoryItem` records and `CategoryItem` relationships.
5.  **`persist_index`**:
    - **Action**: Updates category summaries based on new items using an LLM summarization step.
6.  **`build_response`**:
    - **Action**: Formats the final output dictionary.

---

## 4. The Retrieval Pipeline

The retrieval logic is encapsulated in `RetrieveMixin` (located in `src/memu/app/retrieve.py`). This pipeline is unique because it's **recursive and decision-based**, rather than a simple linear search.

### 4.1. Pipeline Structure
The `retrieve` method initializes the workflow, choosing between `retrieve_rag` (vector-based) or `retrieve_llm` (LLM-ranking-based).

The `retrieve_rag` pipeline is defined in `_build_rag_retrieve_workflow` (lines 106-211) and consists of these steps:

1.  **`route_intention`** (Handler: `_rag_route_intention`)
    -   **Goal**: Determine if memory retrieval is even necessary.
    -   **Logic**: Uses `_decide_if_retrieval_needed` to ask the LLM: "Given the user's query and conversation history, do I need to look up external information?"
    -   **Output**: `needs_retrieval` (bool) and `rewritten_query` (optimized for search).

2.  **`route_category`** (Handler: `_rag_route_category`)
    -   **Goal**: Find high-level topics (Categories) relevant to the query.
    -   **Logic**:
        -   Embeds the `active_query`.
        -   Searches against `MemoryCategory` embeddings (`store.memory_category_repo.list_categories`).
        -   Calls `_rank_categories_by_summary` to get the top-k categories.
    -   **Why**: Narrowing down the search space early prevents retrieving irrelevant details.

3.  **`sufficiency_after_category`** (Handler: `_rag_category_sufficiency`)
    -   **Goal**: **Early Exit Strategy**. Checks if the *Category Summaries* alone answer the user's question.
    -   **Logic**:
        -   Feeds the retrieved category summaries to the LLM.
        -   Asks: "Is this information sufficient?"
        -   If **Yes**, it sets `proceed_to_items = False`. The pipeline effectively stops deeper search here.
        -   If **No**, it sets `proceed_to_items = True` and potentially rewrites the query for the next step.

4.  **`recall_items`** (Handler: `_rag_recall_items`)
    -   **Goal**: Find specific facts (Memory Items) if categories weren't enough.
    -   **Logic**:
        -   Only runs if `proceed_to_items` is True.
        -   Performs vector search (`vector_search_items`) against `MemoryItem`s.
        -   **Crucial Optimization**: It implicitly filters/prioritizes based on the categories found in the previous step (though in the RAG version, it's often a global search weighted by the query).

5.  **`sufficiency_after_items`** (Handler: `_rag_item_sufficiency`)
    -   **Goal**: Second Early Exit Check.
    -   **Logic**: Similar to the previous check. If the specific facts found are enough, `proceed_to_resources = False`. Otherwise, dig deeper.

6.  **`recall_resources`** (Handler: `_rag_recall_resources`)
    -   **Goal**: Retrieve the raw source material (e.g., original document text).
    -   **Logic**: Vector search against `Resource` captions/embeddings. This is the "deepest" level of memory.

7.  **`build_context`** (Handler: `_rag_build_context`)
    -   **Goal**: Assemble the final response.
    -   **Logic**: Aggregates all found categories, items, and resources into a structured dictionary.

### 4.2. Key Logic: The "Sufficiency Loop"
The helper method `_decide_if_retrieval_needed` (lines 706-745) drives the intelligence of this pipeline.
- It prompts the LLM with:
    1.  User Query
    2.  Conversation History
    3.  **Content Retrieved So Far** (e.g., just category summaries)
- The LLM outputs a decision: `RETRIEVE` (need more) or `NO_RETRIEVE` (have enough).
- This mimics a human looking at a table of contents, then a chapter summary, then the text itself, stopping as soon as they know the answer.

---

## 5. Database Layer Details

MemU's database layer (`src/memu/database/`) is designed for flexibility, supporting different backends through a unified `Database` protocol (`src/memu/database/interfaces.py`).

### 5.1. Repositories
The system uses the Repository pattern to abstract data access. The `Database` interface requires four repositories:
1.  **`ResourceRepo`**: Manages original data sources (URLs, file paths).
2.  **`MemoryCategoryRepo`**: Manages high-level topics/categories.
3.  **`MemoryItemRepo`**: Manages the actual extracted facts.
4.  **`CategoryItemRepo`**: Manages the many-to-many relationship between items and categories.

### 5.2. SQLite Implementation (`src/memu/database/sqlite/`)
The SQLite implementation serves as a self-contained, lightweight backend.
- **ORM**: It uses `SQLModel` (a wrapper around SQLAlchemy and Pydantic) for defining schemas and interacting with the database.
- **Vector Search**: Since SQLite lacks native vector support, MemU implements **in-memory brute-force vector search**.
    - **Loading**: `load_existing()` reads all items into memory (`self.items` dict).
    - **Searching**: `vector_search_items` computes Cosine Similarity between the query vector and *all* cached item vectors using NumPy (`src/memu/database/inmemory/vector.py`).
    - **Pros/Cons**: This is extremely fast for small-to-medium datasets (thousands of items) but will not scale to millions of items without a specialized vector database (like pgvector, which MemU also supports but we focused on SQLite here).

### 5.3. Scoped Models
A clever design pattern in `src/memu/database/models.py` is "Scoped Models".
- Functions `merge_scope_model` and `build_scoped_models` allow the application to dynamically inject user-specific fields (e.g., `user_id`, `agent_id`) into the base data models.
- This ensures that a single codebase can support multi-tenancy or multi-agent setups without hardcoding specific scope fields in the core logic.

---

## 6. LLM Integration Layer

The LLM layer (`src/memu/llm/`) is not just a wrapper around API calls; it's a managed runtime for AI operations.

### 6.1. LLMClientWrapper
The `LLMClientWrapper` (`src/memu/llm/wrapper.py`) wraps every LLM client instance. It provides:
- **Unified Interface**: Methods like `summarize`, `embed`, `vision` abstract away provider differences.
- **Metadata Tracking**: Automatically attaches `step_id`, `workflow_name`, and `trace_id` to every call (`LLMCallMetadata`).

### 6.2. Interceptor System
This is a powerful feature for observability and control. The `LLMInterceptorRegistry` allows registering hooks:
- **`before`**: Modify the prompt, block requests, or log intent.
- **`after`**: Log success, record metrics, or post-process responses.
- **`on_error`**: Handle failures, retry logic, or fallback strategies.

This system is used internally for logging (`LLMUsage`) and can be extended by users to add custom monitoring or guardrails.

---

## 7. Prompt Engineering Strategy

MemU uses a structured, modular approach to prompting (`src/memu/prompts/`).

- **Modular Blocks**: Prompts are constructed from reusable blocks (e.g., `PROMPT_BLOCK_OBJECTIVE`, `PROMPT_BLOCK_RULES`, `PROMPT_BLOCK_OUTPUT`). This makes them easier to maintain and test.
- **XML Output Enforcement**: The system heavily relies on XML-tagged output (e.g., `<item><memory>...</memory></item>`).
    - **Why?** XML tags are robust to parsing errors compared to pure JSON, especially when the model outputs mixed text and data.
    - **Parsing**: `MemorizeMixin._parse_memory_type_response_xml` uses Python's `xml.etree.ElementTree` to reliably extract structured data from the model's response.
- **Few-Shot Examples**: Prompts often include concrete examples (`PROMPT_BLOCK_EXAMPLES`) to guide the model's behavior, ensuring consistent style and granularity for memory items.

---

## 8. Summary & Key Takeaways

MemU distinguishes itself through **Proactiveness** and **Architecture**.

1.  **Workflow-First Design**: By defining logic as pipelines (`src/memu/workflow`), it gains flexibility. You can inject a "Approval" step or a "Sanitization" step into the `memorize` pipeline without rewriting the core service.
2.  **Hierarchical Memory**: The Resource -> Item -> Category structure allows it to handle information at different levels of abstraction.
3.  **Proactive Retrieval**: The "Sufficiency Check" loop in retrieval is a key agentic pattern. It doesn't just search once; it thinks, "Do I have enough info?" and keeps searching if needed.
4.  **Hybrid Database Approach**: Using SQLite + In-Memory Vector Search provides a zero-dependency "getting started" experience while the architecture allows swapping in Postgres/pgvector for production.

This walkthrough covers the primary mechanisms that make MemU work. For a developer looking to extend it, the **Workflow Interceptors** and **Custom Pipeline Steps** are the most important extension points.
