"""
Prompt Engineering Assignment

1. Zero-shot Earnings Call Summarization
2. Few-shot Earnings Call Summarization
3. ROUGE-L Evaluation
4. 5-Class Ticket Classification (Billing / Tech / Refund / General / Escalate)
5. Uses Grok (xAI)
"""

import os
import pandas as pd
from rouge_score import rouge_scorer
from openai import OpenAI

from langchain_core.prompts import PromptTemplate


# ==========================================================
# CONFIGURATION
# ==========================================================

# OPTION 1: Hardcode for training/demo
GROK_API_KEY = "gsk_vQxw0ezVDGuh0Gq1hJnHWGdyb3FYJ78gad6wKqfwqUlCTgCCHai"

# OPTION 2: Use environment variable
# GROK_API_KEY = os.getenv("GROK_KEY")

if not GROK_API_KEY:
    raise ValueError(
        "Please set GROK_API_KEY before running."
    )


# ==========================================================
# GROK CLIENT
# ==========================================================

client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1"
)



def call_grok(prompt_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": prompt_text
            }
        ]
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content


# ==========================================================
# PART A: EARNINGS CALL SNIPPETS
# ==========================================================

earnings_call_snippets = [
    """
    Q2 Revenue increased by 18% year-over-year to $2.4 billion.
    Cloud business grew 35%, driven by enterprise adoption.
    Operating margin improved from 16% to 21%.
    Management expects strong demand in the second half of the year.
    """,

    """
    The company reported quarterly revenue of $1.8 billion,
    missing analyst expectations.
    Supply chain disruptions impacted product shipments.
    Gross margin declined by 3 percentage points.
    Leadership expects recovery beginning next quarter.
    """,

    """
    Annual recurring revenue reached $950 million, up 28%.
    Customer retention remained above 95%.
    AI product offerings contributed significantly
    to new customer acquisition.
    Management raised full-year guidance.
    """
]


# ==========================================================
# REFERENCE SUMMARIES
# ==========================================================

reference_summaries = [
    """
    Revenue increased significantly to $2.4 billion.
    Cloud business experienced strong growth.
    Operating margins improved and outlook remains positive.
    """,

    """
    Revenue missed expectations.
    Supply chain issues affected operations.
    Management expects recovery next quarter.
    """,

    """
    Recurring revenue grew substantially.
    Customer retention remained strong.
    AI offerings boosted growth and guidance was raised.
    """
]


# ==========================================================
# PART B: PROMPTS
# ==========================================================

zero_shot_prompt = PromptTemplate(
    input_variables=["transcript"],
    template="""
You are a financial analyst.

Summarize the following earnings call snippet
into exactly 3 concise bullet points.

Earnings Call:
{transcript}

Summary:
"""
)

few_shot_prompt = PromptTemplate(
    input_variables=["transcript"],
    template="""
You are an expert financial analyst.

Example 1

Transcript:
Revenue increased 20% YoY.
Operating profit rose 10%.
Management expects continued growth.

Summary:
- Revenue grew strongly.
- Profitability improved.
- Positive outlook.

Example 2

Transcript:
Sales declined 5%.
Supply chain issues impacted deliveries.
Recovery expected next quarter.

Summary:
- Revenue declined.
- Operational challenges impacted performance.
- Recovery expected.

Now summarize:

Transcript:
{transcript}

Summary:
"""
)


# ==========================================================
# GENERATE SUMMARIES
# ==========================================================

zero_shot_summaries = []
few_shot_summaries = []

print("\nGenerating Summaries...\n")

for snippet in earnings_call_snippets:

    prompt_text = zero_shot_prompt.format(
        transcript=snippet
    )

    summary = call_grok(prompt_text)

    zero_shot_summaries.append(summary)

for snippet in earnings_call_snippets:

    prompt_text = few_shot_prompt.format(
        transcript=snippet
    )

    summary = call_grok(prompt_text)
    print("summary", summary)
    few_shot_summaries.append(summary)


# ==========================================================
# DISPLAY SUMMARIES
# ==========================================================

for i in range(len(earnings_call_snippets)):

    print("\n" + "=" * 80)
    print(f"SNIPPET {i+1}")

    print("\nZERO SHOT")
    print(zero_shot_summaries[i])

    print("\nFEW SHOT")
    print(few_shot_summaries[i])


# ==========================================================
# PART C: ROUGE-L EVALUATION
# ==========================================================

print("\n")
print("=" * 80)
print("ROUGE-L EVALUATION")
print("=" * 80)

scorer = rouge_scorer.RougeScorer(
    ["rougeL"],
    use_stemmer=True
)

results = []

for i in range(len(reference_summaries)):

    zero_score = scorer.score(
        reference_summaries[i],
        zero_shot_summaries[i]
    )["rougeL"].fmeasure

    few_score = scorer.score(
        reference_summaries[i],
        few_shot_summaries[i]
    )["rougeL"].fmeasure

    results.append({
        "Snippet": i + 1,
        "Zero-Shot ROUGE-L": round(zero_score, 4),
        "Few-Shot ROUGE-L": round(few_score, 4)
    })

df = pd.DataFrame(results)

print(df)


# ==========================================================
# PART D: TICKET CLASSIFIER
# ==========================================================

ticket_prompt = PromptTemplate(
    input_variables=["ticket"],
    template="""
You are a customer support expert.

Classify the ticket into one of:

- Billing
- Tech
- Refund
- General
- Escalate

Think step-by-step.

Example:

Ticket:
I was charged twice for my subscription.

Reasoning:
Duplicate charge issue.

Class:
Billing

Example:

Ticket:
The application crashes when I upload files.

Reasoning:
Software malfunction.

Class:
Tech

Example:

Ticket:
I cancelled my order and want my money back.

Reasoning:
Customer requests reimbursement.

Class:
Refund

Now classify:

Ticket:
{ticket}

Reasoning:
"""
)


tickets = [
    "I was billed three times for the same invoice.",
    "My password reset link is not working.",
    "I want a refund for my cancelled purchase.",
    "Can you explain the premium plan features?",
    "The system exposed another user's account information."
]


print("\n")
print("=" * 80)
print("TICKET CLASSIFICATION")
print("=" * 80)

for ticket in tickets:

    prompt_text = ticket_prompt.format(
        ticket=ticket
    )

    result = call_grok(prompt_text)

    print("\n" + "=" * 50)
    print("Ticket:")
    print(ticket)

    print("\nResult:")
    print(result)


# ==========================================================
# ESCALATION RULE CHECK
# ==========================================================

escalation_keywords = [
    "security",
    "breach",
    "fraud",
    "legal",
    "sue",
    "data leak",
    "account information",
    "customer data",
    "exposed"
]

print("\n")
print("=" * 80)
print("ESCALATION DETECTION")
print("=" * 80)

for ticket in tickets:

    if any(
        keyword in ticket.lower()
        for keyword in escalation_keywords
    ):
        label = "Escalate"
    else:
        label = "Non-Escalate"

    print(ticket)
    print("Keyword Rule:", label)
    print("-" * 50)

print("\nProgram Completed Successfully.")