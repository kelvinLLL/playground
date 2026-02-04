import os
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM-as-a-Judge evaluator for memory retrieval.
    Evaluates if retrieved context semantically matches ground truth.
    """

    def __init__(self, model: str = "gpt-4o"):
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def evaluate_recall(
        self, query: str, ground_truth: str, retrieved_items: List[str]
    ) -> float:
        """
        Score (0.0 - 1.0) indicating if retrieved items contain the ground truth information.
        """
        if not retrieved_items:
            return 0.0

        context_text = "\n---\n".join(retrieved_items)

        prompt = f"""
You are an expert evaluator for Information Retrieval systems.
Your task is to determine if the RETRIEVED CONTEXT contains the information necessary to answer the QUERY, based on the GROUND TRUTH.

QUERY: {query}
GROUND TRUTH: {ground_truth}

RETRIEVED CONTEXT:
{context_text}

INSTRUCTIONS:
1. Compare the semantic information in the RETRIEVED CONTEXT with the GROUND TRUTH.
2. Ignore minor wording differences. Focus on key facts (dates, names, values, causality).
3. If the Retrieved Context contains the core facts from Ground Truth, score 1.0.
4. If it contains partial facts, score 0.5.
5. If it is irrelevant or missing the facts, score 0.0.

OUTPUT FORMAT:
Return ONLY the numeric score (0.0, 0.5, or 1.0). Do not output explanation.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a strict evaluator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            score_str = response.choices[0].message.content.strip()
            return float(score_str)
        except Exception as e:
            logger.error(f"Judge evaluation failed: {e}")
            return 0.0
