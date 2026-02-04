# MemU Evaluation Analysis: Why Precision/Recall is Zero?

## Executive Summary

Despite successfully configuring and running the MemU benchmark (HTTP 200 OK responses), the evaluation metrics (`Precision@5`, `Recall@5`) reported **0.00**.

This is **not a failure of MemU's retrieval capability**, but a **mismatch between the evaluation methodology and MemU's architecture**. The benchmark assumes a "Store & Retrieve" model (Key-Value), whereas MemU implements a "Digest & Generate" model (Semantic/Agentic).

---

## 1. The Core Conflict: Identity Preservation vs. Data Digestion

### LocalJSON (The Baseline)
*   **Model**: Key-Value Store / Simple Cache.
*   **Behavior**: You store an object with ID `m1`. When you search, it returns the *exact same object* with ID `m1`.
*   **Evaluation**: The runner compares `retrieved_id` (`m1`) with `ground_truth` (`m1`).
*   **Result**: Match! (Score: 1.0)

### MemU (The Agentic System)
*   **Model**: Cognitive Architecture.
*   **Behavior**: You submit a *Resource* (e.g., a text file) with ID `m1`. MemU does NOT just store it. It:
    1.  **Reads** the resource.
    2.  **Extracts** atomic facts (Items) using an LLM.
    3.  **Generates** new Memory Items with **new, internal UUIDs** (e.g., `550e8400...`).
    4.  **Indexes** these new items.
*   **Retrieval**: When you query, MemU returns these *newly generated* Memory Items (`550e...`).
*   **Evaluation**: The runner compares `retrieved_id` (`550e...`) with `ground_truth` (`m1`).
*   **Result**: Mismatch. (Score: 0.0)

---

## 2. Technical Breakdown of the Disconnect

### Step 1: Ingestion (`add`)
*   **Benchmark Input**: `{"id": "m1", "content": "Sky is blue"}`
*   **MemU Action**: 
    *   Creates `Resource(id="m1_file", content="Sky is blue")`.
    *   LLM Process: "Extract facts from this resource."
    *   Creates `Item(id="uuid_A", summary="The sky is blue", resource_id="m1_file")`.

### Step 2: Retrieval (`search`)
*   **Query**: "What color is the sky?"
*   **MemU Action**: 
    *   Vector Search finds `Item("uuid_A")`.
    *   Returns `Item("uuid_A")` to the runner.

### Step 3: Scoring (`metrics`)
*   **Runner Logic**: `if retrieved_id in relevant_ids:`
*   **Check**: `if "uuid_A" in ["m1"]:`
*   **Outcome**: `False`.

---

## 3. Why This Matters

This phenomenon highlights a fundamental difference in evaluating **Retrieval-Augmented Generation (RAG)** vs. **Agentic Memory**:

| Feature | Standard Database / RAG | Agentic Memory (MemU) |
| :--- | :--- | :--- |
| **Unit of Storage** | Chunk / Document | Fact / Entity / Concept |
| **ID Persistence** | Preserved (User ID) | Generated (System UUID) |
| **Content Fidelity** | Exact Copy | Synthesized / Summarized |
| **Retrieval Goal** | Find the *Source* | Find the *Answer/Knowledge* |

MemU is designed to answer questions using knowledge derived from sources, not just to return the sources themselves.

---

## 4. Solutions for Fair Evaluation

To correctly evaluate MemU, we must adapt the benchmark strategy:

### Solution A: Traceability (Parent ID Matching)
Instead of matching the Item ID, we should check the **Lineage**.
1.  MemU Items contain a `resource_id` field pointing back to the source.
2.  **Fix**: Update `MemUProvider` to return `item.resource_id` instead of `item.id`.
3.  **Result**: `retrieved_id` becomes `m1_file`, which matches (or can be mapped to) `m1`.

### Solution B: Semantic/Fuzzy Matching (Recommended)
Stop checking IDs entirely. Check the **Content**.
1.  **Logic**: Does the retrieved text contain the answer?
2.  **Metric**: `BERTScore`, `Rouge-L`, or `LLM-as-a-Judge` ("Does this retrieved fact answer the query?").
3.  **Result**: "The sky is blue" semantically matches "Sky is blue". Score: High.

### Solution C: RAG Mode Optimization (Implemented)
We configured MemU to run in `rag` mode with `sufficiency_check=False`.
*   This makes it behave more like a standard vector store.
*   However, even in RAG mode, if MemU indexes *chunks* with new IDs rather than preserving the document ID as the primary key for the chunk, the ID mismatch persist unless we explicitly map the returned chunk metadata back to the document ID.

## 5. Implementation: LLM-as-a-Judge (The "Professional" Solution)

We have implemented a rigorous **LLM-as-a-Judge** evaluation pipeline to solve the semantic mismatch.

### Methodology
Instead of checking IDs, we use a separate LLM (the Judge) to evaluate the **Information Recall**.

**Prompt Logic:**
```
Query: {query}
Ground Truth: {ground_truth_text}
Retrieved Context: {retrieved_text_blob}

Task: Does the Retrieved Context contain the core facts present in the Ground Truth necessary to answer the Query?
Score: 0.0 (No), 0.5 (Partial), 1.0 (Yes)
```

### Advantages
1.  **Semantic Fairness**: Correctly scores MemU even if it rephrases "The sky is blue" to "Sky color: Blue".
2.  **ID Agnostic**: Doesn't care about UUIDs, only content.
3.  **Industry Standard**: Aligns with RAGAS/TruLens methodologies.

### How to Run
Use the `--metric-type llm_judge` flag with the runner:

```bash
python -m ai_worker.eval.runner --provider memu --metric-type llm_judge ...
```

This provides a true measure of MemU's "Cognitive Recall" performance.
