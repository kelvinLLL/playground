# Memory Evaluation Datasets

This directory contains datasets for benchmarking memory providers.

## Structure

### LoCoMo (General Agentic Memory)
- `locomo/retrieval.jsonl`: Basic fact retrieval scenarios
- `locomo/temporal.jsonl`: Temporal reasoning and conflict resolution scenarios

### Telecom (Domain Specific)
- `telecom/incidents.jsonl`: Incident similarity and RCA scenarios
- Based on patterns from AIOps Challenge (NetMan) and Loghub

## JSONL Format

Each line is a JSON object with:

```json
{
  "id": "unique_id",
  "name": "Scenario Description",
  "memories": [
    {"id": "m1", "content": "Memory content...", "timestamp": 1234567890}
  ],
  "query": "The question to ask the agent",
  "relevant_ids": ["m1"],
  "category": "metric_category",
  "user_id": "optional_user_id"
}
```
