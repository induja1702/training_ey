import json
import logging
import os
from enum import Enum
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -----------------------------
# Enums
# -----------------------------

class Workflow(str, Enum):
    KNOWLEDGE_RAG = "KnowledgeRAG"
    AGENTIC_RAG = "AgenticRAG"


class TaskType(str, Enum):
    LOOKUP = "lookup"
    SUMMARY = "summary"
    COMPARISON = "comparison"
    COMPLIANCE = "compliance"
    REASONING = "reasoning"
    RISK_ANALYSIS = "risk_analysis"
    MULTI_STEP = "multi_step"


# -----------------------------
# Response Model
# -----------------------------

class IntentResult(BaseModel):
    workflow: Workflow
    task: TaskType
    reason: str
    confidence: float


# -----------------------------
# Intent Detector
# -----------------------------

class IntentDetector:

    def __init__(
        self,
        model: str = "gpt-4.1",
        temperature: float = 0.0,
    ):
        self.client = client
        self.model = model
        self.temperature = temperature

    def detect(self, query: str) -> IntentResult:

        system_prompt = """
You are an Intent Detection Agent for a Contract Intelligence System.

Your ONLY responsibility is deciding which workflow should process
the user's question.

Never answer the question.

There are only TWO workflows.

1. KnowledgeRAG

Choose this when the question is

- factual lookup
- clause lookup
- definition
- payment term
- governing law
- notice period
- contract duration
- single document summary
- direct question

Examples

What is the payment term?

Show clause 7.

Explain force majeure.

What is the governing law?


2. AgenticRAG

Choose this when the question requires

- comparison
- compliance
- reasoning
- multiple retrievals
- multi-step reasoning
- cross-document reasoning
- risk analysis

Examples

Compare payment terms across contracts.

Compare termination clauses.

Which contracts expire within 90 days?

Which contracts have unlimited liability?

Find contracts expiring next month and summarize renewal clauses.

Is this contract compliant with procurement policy?

Return ONLY valid JSON.

Example

{
    "workflow":"KnowledgeRAG",
    "task":"lookup",
    "reason":"Direct factual lookup",
    "confidence":0.99
}
"""

        response = self.client.responses.create(
            model=self.model,
            temperature=self.temperature,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
        )

        text = response.output_text.strip()

        try:
            result = IntentResult.model_validate(json.loads(text))

            logger.info(
                "Intent detected | workflow=%s task=%s confidence=%.2f",
                result.workflow,
                result.task,
                result.confidence,
            )

            return result

        except (ValidationError, json.JSONDecodeError) as e:

            logger.exception("Intent detection failed: %s", e)

            return IntentResult(
                workflow=Workflow.KNOWLEDGE_RAG,
                task=TaskType.LOOKUP,
                reason="Fallback due to parsing failure",
                confidence=0.50,
            )