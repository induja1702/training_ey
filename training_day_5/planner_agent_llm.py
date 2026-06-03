
import os, json

from dotenv import load_dotenv

from typing import TypedDict, List

from langchain_core.messages import SystemMessage, HumanMessage

from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(

    temperature=0,

    model_name="llama-3.1-8b-instant",

    groq_api_key=GROQ_API_KEY

)


# --- shared state schema ---

class AgentState(TypedDict):
    goal: str

    tasks: List[str]

    results: List[str]

    critique: str

    approved: bool

    iterations: int


def planner(state: AgentState) -> AgentState:
    system = """You are a planning agent. Break the user's goal into

at most 5 concrete, actionable tasks. Respond ONLY with a

valid JSON array of strings. No preamble, no markdown."""

    messages = [

        SystemMessage(content=system),

        HumanMessage(content=f"Goal: {state['goal']}")

    ]

    response = llm.invoke(messages).content.strip()

    try:

        clean = response.replace("```json", "").replace("```", "").strip()

        tasks = json.loads(clean)

    except json.JSONDecodeError:

        tasks = [response]  # fallback: treat whole response as one task

    print(f"\n[Planner] Generated {len(tasks)} tasks:")

    for i, t in enumerate(tasks): print(f"  {i + 1}. {t}")

    return {**state, "tasks": tasks}


initial_state: AgentState = {

    "goal": "Research and summarise the top 3 trends in agriculture for 2025",

    "tasks": [],

    "results": [],

    "critique": "",

    "approved": False,

    "iterations": 0

}

planner(initial_state)