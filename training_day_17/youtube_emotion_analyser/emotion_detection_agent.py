from typing import TypedDict
from collections import Counter
from langgraph.graph import StateGraph, END

from hume_client import analyze_video

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from config import OPENAI_API_KEY

# ----------------------------
# LLM
# ----------------------------

llm = ChatOpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0
)

# ----------------------------
# STATE
# ----------------------------

class AgentState(TypedDict):

    video_path: str

    emotions: list

    status: str

    suggestions: str


# ----------------------------
# AGENT 1
# Emotion Detection
# ----------------------------

def emotion_agent(state):

    video_path = state["video_path"]

    emotions = analyze_video(video_path)

    return {
        "emotions": emotions
    }


# ----------------------------
# AGENT 2
# Decision Agent
# ----------------------------

def decision_agent(state):

    emotions = state["emotions"]

    detected = [
        x["dominant_emotion"]
        for x in emotions
    ]

    counts = Counter(detected)

    dominant = counts.most_common(1)[0][0]

    satisfied_emotions = [
        "happy",
        "neutral"
    ]

    if dominant in satisfied_emotions:
        status = "SATISFIED"
    else:
        status = "UNSATISFIED"

    print(f"\nOverall Emotion: {dominant}")
    print(f"Customer Status: {status}")

    return {
        "status": status
    }


# ----------------------------
# ROUTER
# ----------------------------

def route_decision(state):

    if state["status"] == "SATISFIED":
        return "end"

    return "recommendation"


# ----------------------------
# AGENT 3
# GPT Recommendation Agent
# ----------------------------

def recommendation_agent(state):

    emotions = state["emotions"]

    emotion_summary = []

    for e in emotions:

        emotion_summary.append(
            f"""
            Time:{e['timestamp_sec']}
            Emotion:{e['dominant_emotion']}
            Scores:{e['emotions']}
            """
        )

    prompt = f"""
You are a customer experience analyst.

A customer interaction video was analyzed.

Emotion Timeline:

{emotion_summary}

The customer appears dissatisfied.

Perform the following:

1. Explain why the customer may be unhappy.
2. Identify likely issues.
3. Recommend actions for support team.
4. Suggest next best response.
5. Give urgency level (Low/Medium/High).

Return in markdown format.
"""

    response = llm.invoke(
        [HumanMessage(content=prompt)]
    )

    return {
        "suggestions": response.content
    }


# ----------------------------
# END AGENT
# ----------------------------

def end_agent(state):

    print("\nCustomer satisfied.")
    print("No further action required.")

    return state


# ----------------------------
# GRAPH
# ----------------------------

graph = StateGraph(AgentState)

graph.add_node(
    "emotion",
    emotion_agent
)

graph.add_node(
    "decision",
    decision_agent
)

graph.add_node(
    "recommendation",
    recommendation_agent
)

graph.add_node(
    "end",
    end_agent
)

graph.set_entry_point("emotion")

graph.add_edge(
    "emotion",
    "decision"
)

graph.add_conditional_edges(
    "decision",
    route_decision,
    {
        "recommendation": "recommendation",
        "end": "end"
    }
)

graph.add_edge(
    "recommendation",
    END
)

graph.add_edge(
    "end",
    END
)

app = graph.compile()


# ----------------------------
# RUN
# ----------------------------

if __name__ == "__main__":

    VIDEO_FILE = "customer.mp4"

    result = app.invoke(
        {
            "video_path": VIDEO_FILE
        }
    )

    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)

    if result.get("suggestions"):
        print(result["suggestions"])