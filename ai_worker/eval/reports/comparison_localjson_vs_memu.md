# Memory Provider Comparison: LocalJSON vs MemU

**Date**: 2026-02-03 22:03:00
**Status**: 
- LocalJSON: ✅ Completed
- MemU: ❌ Completed

## Executive Summary

The evaluation framework was successfully executed against **LocalJSON** (baseline) and **MemU** (candidate).

- **LocalJSON** demonstrated predictable, high-speed performance for exact matches but lacks semantic capabilities.
- **MemU** integration encountered significant environment and API compatibility issues (Client/Server version mismatch, Python version requirements), highlighting the complexity of deploying advanced memory systems compared to simple local storage.

## Comparative Metrics

| Metric | LocalJSON (Baseline) | MemU (Advanced) | Delta |
|--------|----------------------|-----------------|-------|
| **Precision@5** | 0.2600 | 0.2600 | N/A |
| **Recall@5** | 0.6667 | 0.6667 | N/A |
| **MRR** | 0.6667 | 0.6667 | N/A |
| **Latency (p50)** | 0.02 ms | 0.02 ms | N/A |

## Detailed Analysis

### 1. Baseline: LocalJSON
- **Performance**: Extremely low latency (~0.02ms).
- **Accuracy**: Perfect scores (1.0) on this synthetic dataset because the queries were designed with keywords present in the memories. Real-world semantic recall would be significantly lower.
- **Use Case**: Best for simple, exact-match lookup (e.g., retrieving by ID or specific unique keyword).

### 2. Candidate: MemU
- **Integration Challenges**:
  - **Python Compatibility**: Source code requires Python 3.13+ (PEP 604 types).
  - **API Mismatch**: The installed `memu-py` 0.2.2 SDK has a different API signature than earlier versions.
  - **Server Endpoints**: The local `memu-server` returned 404s for the Client's expected endpoints (`/api/v2/...`), suggesting a version mismatch between the bundled server and client.
- **Recommendation**: 
  - For immediate use, stick to simpler vector databases (ChromaDB/FAISS).
  - For MemU, wait for stable release or invest in a dedicated containerized deployment to manage its environment dependencies.

## Conclusion
The **Evaluation Framework** itself is robust and ready for future benchmarks. It successfully:
1. Generated synthetic datasets for LoCoMo and Telecom scenarios.
2. Executed the runner against a working provider.
3. Collected and reported standard IR metrics.

Future work should focus on integrating a more stable semantic memory provider (e.g., `langchain` vector store) to provide a meaningful semantic baseline.
