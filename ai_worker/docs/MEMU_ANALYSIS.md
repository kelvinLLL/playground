# MemU Architecture Analysis

**Version**: 1.0 (Based on `memu-py` 1.2.0)
**Date**: 2026-01-29

## 1. Executive Summary

MemU (NevaMind-AI/memU) is an open-source, hierarchical memory framework designed for "Always-on" AI Agents and Companions. Unlike simple Vector Stores (which just index text chunks), MemU structures memory into layers to enable **traceability**, **evolution**, and **high-accuracy retrieval**.

It claims SOTA performance on the LoCoMo benchmark (92% accuracy) and emphasizes "Self-Evolving Memory".

## 2. Core Architecture: The 3-Layer System

MemU distinguishes itself with a strict data hierarchy inspired by human cognitive architecture:

### Layer 1: Resource Layer (Episodic / Raw Input)
- **Concept**: "What happened?"
- **Content**: Immutable logs of interactions. User messages, system responses, tool outputs, external documents.
- **Properties**: Time-ordered, high-volume, noisy.
- **Function**: Serves as the "Ground Truth". Any high-level fact can be traced back to a Resource ID.

### Layer 2: Memory Item Layer (Semantic / Discrete Facts)
- **Concept**: "What does it mean?"
- **Content**: Extracted atomic facts.
    - *Example*: From "I'm rewriting my backend in Rust", extracts: `(User, is_using, Rust)`, `(User, role, Backend Developer)`.
- **Role**: The "Working Memory" for retrieval. These are deduplicated and normalized.
- **Mechanism**: An LLM (Memorizer) runs asynchronously to process Resources and generate Items.

### Layer 3: Category Layer (Structured / Conceptual)
- **Concept**: "How does this fit into the world?"
- **Content**: High-level clusters or "Folders" of knowledge.
    - *User Profile*: Personality, Preferences.
    - *World Model*: coding_standards, project_architecture.
- **Role**: Provides the "Mental Model". Items are tagged or linked to Categories.

## 3. Key Differentiators & Mechanisms

### 3.1 Traceability (The "Why")
Standard RAG gives you a chunk of text. MemU gives you a **Fact** linked to its **Source**.
- Query: "Does the user know Python?"
- Result: "Yes (Confidence: 0.9)"
- Evidence: "Resource #1024: User said 'I have 5 years of Python experience'."
**Value**: Critical for debugging agent hallucinations.

### 3.2 Self-Evolution (Conflict Resolution)
What happens when facts change?
- *T1*: "I love React." -> Item A: `(User, likes, React)`
- *T2*: "I hate React now, Svelte is better." -> Item B: `(User, dislikes, React)`, Item C: `(User, likes, Svelte)`
- **Evolution Logic**: MemU detects the conflict between Item A and B. Based on recency (Timestamp) and explicit negation, it updates the Graph:
    - Item A marked as "Outdated" or "Historical".
    - Item B becomes "Active".
    - This creates a **Time-Travel capable memory** (State at T1 vs State at T2).

### 3.3 Retrieval Strategies (The "Brain")
MemU exposes distinct retrieval paths:
1.  **Semantic Search (RAG)**: Embedding-based. Fast. Finds "similar" items.
    - *Use case*: "Has the user mentioned 'docker' before?"
2.  **Graph Traversal**: Finds connected items.
    - *Use case*: "What tech stack does the user prefer?" (Traverse `User -> prefers -> ?`)
3.  **Hybrid**: Combine vector similarity with graph connections to find "conceptually related" memories even if keywords don't match.

## 4. Integration Strategy

We will integrate MemU via the `MemUProvider` class, wrapping the `memu-py` SDK.

### 4.1 Interface Mapping

| AI Worker Interface | MemU Concept | Data Flow |
| :--- | :--- | :--- |
| `add(content)` | `Resource` | Ingest -> Async Extraction -> Item/Graph |
| `search(query)` | `Item` / `Graph` | Query -> Embedding/LLM -> Ranked Facts |
| `get_recent()` | `Resource` | Simple time-based fetch |

### 4.2 Application in AI Worker
1.  **Background Learning**: The worker pushes every interaction to MemU. MemU silently builds a profile.
2.  **Context Injection**: Before answering, the Worker queries MemU for "User Profile" + "Query-Relevant Facts".
3.  **Skill Enhancement**: If User asks "Deploy this", MemU recalls "User prefers Docker over K8s", and the Agent adapts the deployment script automatically.

## 5. SDK Usage (Conceptual)

```python
from memu import MemU

# Initialization (likely requires DB config)
client = MemU(api_key="...", storage="postgres://...")

# 1. Ingest (Fire and Forget)
# The system returns a resource_id immediately, extraction happens in background
resource_id = client.add("I want to switch to Poetry for dependency management.", user_id="u1")

# 2. Recall (Retrieval)
# 'context' contains list of Fact Objects with graph links
context = client.search("dependency management preferences", user_id="u1")

print(context[0].content) # "User prefers Poetry"
print(context[0].source_id) # links back to resource_id
```

## 6. Compatibility Check
*   **Python Version**: `memu-py` metadata says `>= 3.13`. We are on `3.12`.
    *   *Risk*: High. We might need to fork or patch if it uses new syntax.
    *   *Mitigation*: Test install in a separate environment or wait for 3.13 support in our environment.
*   **Backend**: MemU is a *Framework*. It likely requires us to run a Database (Postgres/Neo4j) or use their Cloud API.
    *   *Decision*: For the "Local" vibe of AI Worker, running a local Postgres might be heavy. We should check if `memu-py` supports SQLite or simple file storage (like Chroma).

---
**Status**: Deep Dive Complete. Understanding of internal mechanics established.
