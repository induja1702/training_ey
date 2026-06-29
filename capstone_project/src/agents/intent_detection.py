import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is required for intent detection.")

client = OpenAI(api_key=api_key)


def detect_intent(query: str) -> dict:
    """Classify the user's query intent into 'simple' or 'complex'.

    - 'simple' = fact lookup / straightforward Q&A suitable for similarity search + short answer
    - 'complex' = multi-document comparison, risk/compliance, or multi-step tasks requiring an agent
    """

    system = (
        "You are an intent classifier. Classify the user's question into either 'simple' or 'complex'.\n"
        "Return a JSON object with fields: intent, reason, confidence (0-1).\n"
        "Simple = direct factual question suitable for a retrieval from passages.\n"
        "Complex = multi-document reasoning, comparisons, risk assessment, or multi-step tasks.\n"
    )

    prompt = f"Question: {query}\n\nClassify and provide a short reason."

    resp = client.responses.create(
        model="gpt-4o",
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_output_tokens=200,
    )

    # Try to extract output text
    output_text = getattr(resp, "output_text", None)
    if not output_text and getattr(resp, "output", None):
        for item in resp.output:
            if getattr(item, "type", None) == "message":
                for content_item in getattr(item, "content", []) or []:
                    if getattr(content_item, "type", None) == "output_text":
                        output_text = getattr(content_item, "text", "")
                        break
                if output_text:
                    break

    if not output_text:
        logger.warning("Intent detection returned no text; defaulting to simple.")
        return {"intent": "simple", "reason": "no response", "confidence": 0.5}

    # Very lightweight extraction: look for keywords
    text = output_text.strip().lower()
    intent = "complex" if "complex" in text or "multi" in text or "compare" in text or "risk" in text else "simple"
    # confidence heuristic: look for numbers
    import re
    m = re.search(r"(0\.?\d+|1(?:\.0+)?)", text)
    confidence = float(m.group(1)) if m else 0.8

    return {"intent": intent, "reason": output_text.strip(), "confidence": confidence}


class IntentAgent:
    """Simple agent to handle complex intents by synthesizing multiple retrieved chunks."""

    def __init__(self, client: OpenAI = client):
        self.client = client

    def run(self, question: str, docs: list[dict]) -> dict:
        """Return {'answer': str, 'explanations': str} using the LLM to synthesize."""
        joined = "\n\n".join(f"Source: {d.get('source')}\n{d.get('content')}" for d in docs)
        prompt = (
            "You are an expert assistant. Use the following document passages to answer the question. "
            "Be explicit about reasoning, list sources used, and flag uncertainty.\n\n"
            f"{joined}\n\nQuestion: {question}\n\nAnswer:"
        )

        resp = self.client.responses.create(
            model="gpt-4o",
            input=[
                {"role": "system", "content": "You are an expert assistant specialized in document analysis."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_output_tokens=600,
        )

        output_text = getattr(resp, "output_text", None)
        if not output_text and getattr(resp, "output", None):
            for item in resp.output:
                if getattr(item, "type", None) == "message":
                    for content_item in getattr(item, "content", []) or []:
                        if getattr(content_item, "type", None) == "output_text":
                            output_text = getattr(content_item, "text", "")
                            break
                    if output_text:
                        break

        return {"answer": (output_text or "" ).strip()}
