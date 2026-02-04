import asyncio
import json
import logging
import time
import argparse
import statistics
from pathlib import Path
from typing import List, Dict, Any
from ai_worker.eval.agent import MemAgent
from ai_worker.eval.metrics import (
    precision_at_k,
    recall_at_k,
    mrr,
    latency_stats,
    count_tokens,
)
from ai_worker.eval.judge import LLMJudge

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("eval_runner")


class EvaluationRunner:
    """
    Runs memory evaluation benchmarks using MemAgent.
    Executes scenarios defined in JSONL files and generates reports.
    """

    def __init__(self, provider_name: str, metric_type: str = "exact"):
        self.provider_name = provider_name
        self.metric_type = metric_type
        self.agent = MemAgent(provider_name)
        self.results: List[Dict[str, Any]] = []
        self.judge = None

    async def initialize(self):
        """Initialize the agent and judge."""
        await self.agent.initialize()
        if self.metric_type == "llm_judge":
            logger.info("Initializing LLM Judge...")
            self.judge = LLMJudge()

    async def run_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single evaluation scenario.
        """
        scenario_id = scenario.get("id", "unknown")
        user_id = scenario.get("user_id", f"user_{scenario_id}")

        logger.info(f"Running scenario: {scenario_id} - {scenario.get('name')}")

        # 1. Setup: Reset memory and add scenario memories
        await self.agent.reset(user_id)

        scenario_memories = scenario.get("memories", [])
        for mem in scenario_memories:
            content = mem.get("content", "")
            mid = mem.get("id", "")
            # We track original ID in metadata for "exact" matching
            await self.agent.add_memory(content, user_id, metadata={"original_id": mid})

        # 2. Query execution
        start_time = time.perf_counter()
        retrieved_items = await self.agent.search(scenario["query"], user_id, limit=5)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # 3. Collect metrics

        # A. Exact Match Metrics (ID based)
        retrieved_ids = []
        retrieved_contents = []
        for item in retrieved_items:
            # Try to get original ID from metadata, or fallback to item.id
            orig_id = item.metadata.get("original_id") if item.metadata else None
            retrieved_ids.append(orig_id if orig_id else item.id)
            retrieved_contents.append(item.content)

        relevant_ids = set(scenario["relevant_ids"])

        p5 = precision_at_k(retrieved_ids, relevant_ids, 5)
        r5 = recall_at_k(retrieved_ids, relevant_ids, 5)
        mrr_score = mrr(retrieved_ids, relevant_ids)
        tokens = count_tokens(scenario["query"])

        # B. LLM Judge Metrics (Semantic/Content based)
        context_recall = 0.0
        if self.metric_type == "llm_judge" and self.judge:
            # Get ground truth content
            relevant_content_list = [
                m["content"] for m in scenario_memories if m["id"] in relevant_ids
            ]
            ground_truth_text = "\n".join(relevant_content_list)

            # Run judge (sync call in async wrapper if needed, but OpenAI client is sync usually)
            # LLMJudge.evaluate_recall is sync. We should run in executor to not block.
            loop = asyncio.get_running_loop()
            context_recall = await loop.run_in_executor(
                None,
                lambda: self.judge.evaluate_recall(
                    scenario["query"], ground_truth_text, retrieved_contents
                ),
            )
            logger.info(f"  -> Context Recall Score: {context_recall}")

        result = {
            "scenario_id": scenario_id,
            "provider": self.provider_name,
            "precision_at_5": p5,
            "recall_at_5": r5,
            "mrr": mrr_score,
            "context_recall": context_recall,  # New metric
            "latency_ms": latency_ms,
            "tokens": tokens,
            "retrieved_count": len(retrieved_ids),
            "relevant_count": len(relevant_ids),
        }

        self.results.append(result)
        return result

    async def run_dataset(self, dataset_path: str):
        """Run all scenarios in a JSONL dataset."""
        path = Path(dataset_path)
        if not path.exists():
            logger.error(f"Dataset not found: {path}")
            return

        logger.info(f"Loading dataset: {path}")
        with open(path, "r") as f:
            scenarios = [json.loads(line) for line in f if line.strip()]

        for scenario in scenarios:
            try:
                await self.run_scenario(scenario)
            except Exception as e:
                logger.error(f"Error running scenario {scenario.get('id')}: {e}")

    def generate_report(self, output_path: str):
        """Generate a Markdown report from collected results."""
        if not self.results:
            logger.warning("No results to report.")
            return

        # Calculate aggregate stats
        avg_p5 = (
            statistics.mean([r["precision_at_5"] for r in self.results])
            if self.results
            else 0
        )
        avg_r5 = (
            statistics.mean([r["recall_at_5"] for r in self.results])
            if self.results
            else 0
        )
        avg_mrr = (
            statistics.mean([r["mrr"] for r in self.results]) if self.results else 0
        )
        avg_context_recall = (
            statistics.mean([r.get("context_recall", 0.0) for r in self.results])
            if self.results
            else 0
        )

        latencies = [r["latency_ms"] for r in self.results]
        lat_stats = latency_stats(latencies)

        report = [
            f"# Memory Evaluation Report: {self.provider_name.upper()}",
            f"\n**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Metric Type**: {self.metric_type.upper()}",
            f"**Total Scenarios**: {len(self.results)}",
            "\n## Aggregate Metrics",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Precision@5 (ID) | {avg_p5:.4f} |",
            f"| Recall@5 (ID) | {avg_r5:.4f} |",
            f"| MRR (ID) | {avg_mrr:.4f} |",
            f"| **Context Recall (LLM)** | **{avg_context_recall:.4f}** |",
            f"| Latency (p50) | {lat_stats['p50']:.2f} ms |",
            f"| Latency (p95) | {lat_stats['p95']:.2f} ms |",
            "\n## Detailed Results",
            "| ID | P@5 | Context Recall | Latency |",
            "|----|-----|----------------|---------|",
        ]

        for r in self.results:
            report.append(
                f"| {r['scenario_id']} | {r['precision_at_5']:.2f} | {r.get('context_recall', 0.0):.2f} | "
                f"{r['latency_ms']:.0f} ms |"
            )

        with open(output_path, "w") as f:
            f.write("\n".join(report))
        logger.info(f"Report saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description="Memory Evaluation Runner")
    parser.add_argument(
        "--provider", type=str, required=True, help="Provider name (local, memu)"
    )
    parser.add_argument(
        "--datasets",
        type=str,
        required=True,
        help="Comma-separated paths to JSONL datasets",
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output path for Markdown report"
    )
    parser.add_argument(
        "--metric-type",
        type=str,
        default="exact",
        choices=["exact", "llm_judge"],
        help="Evaluation metric type",
    )

    args = parser.parse_args()

    runner = EvaluationRunner(args.provider, args.metric_type)
    await runner.initialize()

    dataset_paths = args.datasets.split(",")
    for path in dataset_paths:
        await runner.run_dataset(path.strip())

    runner.generate_report(args.output)


if __name__ == "__main__":
    asyncio.run(main())
