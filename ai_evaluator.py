"""
AI-powered evaluator for micro-saas ideas.
"""

import os
import json

# import openai
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import requests
from config import Config
import logging
import re  # for regex matching in _extract_json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvaluatedIdea:
    idea: str
    description: str
    score: float  # 0-100
    market_size: str  # "large", "medium", "small"
    competition: str  # "high", "medium", "low"
    build_difficulty: str  # "easy", "medium", "hard"
    mvp_budget: float
    summary: str  # 1-2 sentences

    # SYSTEM_PROMPT = (
    #     "You are a startup analyst.  "
    #     "Return a JSON list with keys: score, market_size, competition, build_difficulty, summary.  "
    #     "score is 0-100.  "
    #     "market_size ∈ {large,medium,small}.  "
    #     "competition ∈ {high,medium,low}.  "
    #     "build_difficulty ∈ {easy,medium,hard}.  "
    #     "summary is 1-2 sentences."
    # )


class AIEvaluator:
    """
    AI evaluator for micro-saas ideas using DeepSeek API.
    It evaluates a list of ideas and returns a list of EvaluatedIdea instances.
    """

    SYSTEM_PROMPT = (
        "You are a startup analyst.  "
        "Return a JSON list with keys: score, market_size, competition, build_difficulty, mvp_budget, summary.  "
        "score is 0-100.  "
        "market_size ∈ {large,medium,small}.  "
        "competition ∈ {high,medium,low}.  "
        "build_difficulty ∈ {easy,medium,hard}.  "
        "mvp_budget is a float in EUR based on the fiverr prices.  "
        "summary is 2-3 sentences."
    )

    def __init__(self, keyword: str):
        self.url = "https://api.deepseek.com/v1/chat/completions"
        self.key = os.getenv(
            "DEEPSEEK_APIKEY"
        )  # or open("deepseek.key").read().strip()
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        self.keyword = keyword

    def _extract_json(self, text: str) -> list:
        """Pull the first JSON array from the response."""
        # 1. look for ```json [...] ```
        match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
        if not match:
            # 2. fallback: first bare [...]
            match = re.search(r"(\[.*?\])", text, re.DOTALL)
        if not match:
            logger.error("No JSON block found in response:\n%s", text)
            raise ValueError("Invalid JSON from DeepSeek")
        return json.loads(match.group(1))

    def _merge_list_dictionaries(self, original: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge two lists of dictionaries, updating the original with new values.
        If a key exists in both, the value from the new dictionary is used.
        """
        merged = original.copy()
        for idx, new_dict in enumerate(new):
            for key, value in new_dict.items():
                if key in merged[idx]:
                    logger.warning(f"Overwriting key '{key}' with new value: {value}")
                    continue  # Skip if key already exists
                merged[idx][key] = value
        return merged

    def evaluate(self, ideas: List[Dict[str, str]]) -> List[EvaluatedIdea]:
        """
        Evaluate a list of micro-saas ideas using AI.
        Each idea is a dictionary with 'idea' and 'description' keys.
        Returns a list of EvaluatedIdea instances.
        """
        prompt = "\n".join(
            f"{i+1}. Idea: {key}\n   Description: {value}"
            for i, row in enumerate(ideas)
            for key, value in row.items()
        )

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 300 * len(ideas),
        }
        print(f"Evaluating {len(ideas)} ideas...")
        resp = requests.post(
            self.url,
            headers=self.headers,
            json=payload,
            timeout=Config.DEEPSEEK_TIMEOUT,
        )
        print(f"Response status: {resp.status_code}")
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        # print(f"Raw response: {raw}")
        results = self._extract_json(raw)
        # results = [
        #     {**idea, **result}          # merge original keys + AI keys
        #     for idea, result in zip(ideas, results)
        # ]
        results = self._merge_list_dictionaries(ideas, results)

        with open(Path(Config.CACHE_DIR, f"deepseek_{self.keyword}.json"), "w") as f:
            json.dump(results, f, indent=2)
        # return [
        #     EvaluatedIdea(
        #         idea=ideas[i]["idea"], description=ideas[i]["description"], **r
        #     )
        #     for i, r in enumerate(results)
        # ]
        return results