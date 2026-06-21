# app.py  —  Voice Emotion Research Assistant
# Researcher-Supervisor-Writer pattern via LangGraph + Groq + Tavily
# Run:  streamlit run app.py

import operator
import os
import streamlit as st
from typing import Annotated, List, TypedDict, Literal

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Emotion Research Agent",
    page_icon="🎙️",
    layout="wide",
)

st.markdown("""
<style>
.agent-box {
    border-radius: 10px;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 14px;
    line-height: 1.6;
}
.supervisor { background: #f0edff; border-left: 4px solid #7F77DD; color: #3C3489; }
.researcher { background: #e1f5ee; border-left: 4px solid #1D9E75; color: #085041; }
.writer     { background: #faece7; border-left: 4px solid #D85A30; color: #4A1B0C; }
.system     { background: #f1f5fb; border-left: 4px solid #378ADD; color: #042C53; }
.pause      { background: #faeeda; border-left: 4px solid #BA7517; color: #412402; }
.final      { background: #eaf3de; border-left: 4px solid #639922; color: #173404; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar — API Keys
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🎙️ Voice Emotion Agent")
    st.caption("Researcher → Supervisor → Writer pattern")
    st.divider()

    st.subheader("API Keys")
    groq_key   = st.text_input("Groq API Key",   type="password",
                                value=os.environ.get("GROQ_API_KEY", ""))
    tavily_key = st.text_input("Tavily API Key", type="password",
                                value=os.environ.get("TAVILY_API_KEY", ""))

    st.divider()
    st.subheader("Graph settings")
    use_breakpoint = st.toggle("⏸ Pause before Writer", value=True,
                                help="Mirrors interrupt_before=['writer'] from the notebook")
    max_iterations = st.slider("Max supervisor loops", 2, 8, 4)

    st.divider()
    st.subheader("Architecture")
    st.markdown("""
**Nodes**
- 🧠 `supervisor` — Groq LLaMA-3.3-70b routes via structured `Router`
- 🔍 `researcher` — Tavily web search → appends `research_notes`
- ✍️ `writer` — Groq LLaMA composes final report from notes

**State fields**
```
task            str
research_notes  List[str]  (reducer: append)
draft           str
next_node       str
retry_count     int
revision_feedback str
```
**Edges**
- supervisor → {researcher | writer | FINISH}
- researcher → supervisor
- writer → supervisor
""")


# ─────────────────────────────────────────────
# State + Schema
# ─────────────────────────────────────────────
class AgentState(TypedDict):
    task:              str
    research_notes:    Annotated[List[str], operator.add]
    draft:             str
    next_node:         str
    retry_count:       int
    revision_feedback: str


class Router(BaseModel):
    """Decide which worker to call next."""
    next_worker:  Literal["researcher", "writer", "FINISH"] = Field(
        description="The next node to act")
    instructions: str  = Field(description="Specific instructions for the worker")
    is_critical:  bool = Field(description="If True, system will pause for human review")


# ─────────────────────────────────────────────
# Build graph (cached so it's only compiled once)
# ─────────────────────────────────────────────
@st.cache_resource
def build_graph(groq_api_key: str, tavily_api_key: str,
                with_breakpoint: bool, max_loops: int):

    os.environ["GROQ_API_KEY"]   = groq_api_key
    os.environ["TAVILY_API_KEY"] = tavily_api_key

    llm         = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0,
                           api_key=groq_api_key)
    search_tool = TavilySearchResults(k=3, tavily_api_key=tavily_api_key)

    loop_counter = {"n": 0}

    def researcher(state: AgentState):
        query   = state["task"]
        results = search_tool.invoke(query)
        return {"research_notes": [str(results)], "retry_count": 0}

    def writer(state: AgentState):
        context = "\n\n".join(state["research_notes"])
        prompt  = (
            f"You are an expert analyst. Write a detailed, structured report on:\n\n"
            f"**Topic:** {state['task']}\n\n"
            f"**Research gathered:**\n{context}\n\n"
            f"Supervisor instructions: {state.get('revision_feedback','')}\n\n"
            f"Format with: Executive Summary, Key Findings, Emotional Dimensions, "
            f"Practical Implications, References."
        )
        res = llm.invoke(prompt)
        return {"draft": res.content}

    def supervisor(state: AgentState):
        loop_counter["n"] += 1
        structured_llm = llm.with_structured_output(Router)
        prompt = (
            f"Task: {state['task']}\n"
            f"Research notes collected: {len(state['research_notes'])}\n"
            f"Current draft length: {len(state.get('draft',''))}\n"
            f"Loop number: {loop_counter['n']} of {max_loops}\n\n"
            f"Rules:\n"
            f"- If no research notes exist → choose 'researcher'\n"
            f"- If notes exist but no draft → choose 'writer'\n"
            f"- If loop >= {max_loops} OR a good draft exists → choose 'FINISH'\n"
            f"- If notes exist but research seems thin → choose 'researcher' again\n"
        )
        decision = structured_llm.invoke(prompt)
        if loop_counter["n"] >= max_loops:
            decision.next_worker = "FINISH"
        return {
            "next_node":         decision.next_worker,
            "revision_feedback": decision.instructions,
        }

    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("researcher", researcher)
    builder.add_node("writer",     writer)
    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {"researcher": "researcher", "writer": "writer", "FINISH": END},
    )
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer",     "supervisor")

    memory = MemorySaver()
    compile_kwargs = {"checkpointer": memory}
    if with_breakpoint:
        compile_kwargs["interrupt_before"] = ["writer"]

    graph = builder.compile(**compile_kwargs)
    return graph, loop_counter


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
EMOTION_TASKS = {
    "Custom topic (type below)": "",
    "🎙️ Voice emotion detection methods & deep learning":
        "Latest methods for voice emotion recognition using deep learning in 2024-2025",
    "😢 Emotional patterns in speech: sadness vs depression":
        "How do speech patterns differ between sadness and clinical depression in voice analysis",
    "😡 Anger detection in customer service calls":
        "Real-time anger and frustration detection in customer service voice calls",
    "😄 Joy and positive emotion markers in speech":
        "Acoustic and linguistic markers of joy happiness and positive emotions in speech",
    "😨 Stress and anxiety detection from voice":
        "Detecting stress anxiety and fear from voice biomarkers in real-time audio",
    "🎭 Multi-modal emotion recognition (voice + face)":
        "Combining voice audio and facial expression analysis for multimodal emotion recognition",
}


def log(cls: str, icon: str, title: str, body: str = ""):
    st.markdown(
        f'<div class="agent-box {cls}"><strong>{icon} {title}</strong>'
        + (f"<br>{body}" if body else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────
st.title("🎙️ Voice Emotion Research Agent")
st.caption(
    "Multi-agent LangGraph system: **Supervisor** orchestrates a **Researcher** "
    "(Tavily search) and a **Writer** (Groq LLaMA) to produce emotion-detection reports."
)

col1, col2 = st.columns([2, 1])

with col1:
    preset = st.selectbox("Choose a topic preset", list(EMOTION_TASKS.keys()))
    if preset == "Custom topic (type below)":
        task = st.text_area("Your research question", height=80,
                             placeholder="e.g. How does whisper-large-v3 perform on emotional speech datasets?")
    else:
        task = st.text_area("Edit if needed", value=EMOTION_TASKS[preset], height=80)

with col2:
    st.metric("Model", "LLaMA 3.3 70b")
    st.metric("Search", "Tavily")
    st.metric("Framework", "LangGraph")

run_btn = st.button("🚀 Run Agent Pipeline", type="primary",
                     disabled=not (groq_key and tavily_key and task.strip()))

if not groq_key or not tavily_key:
    st.info("Enter your Groq and Tavily API keys in the sidebar to get started.")

# ─────────────────────────────────────────────
# Execution
# ─────────────────────────────────────────────
if run_btn and task.strip():
    st.divider()
    st.subheader("Agent execution log")

    try:
        graph, loop_ctr = build_graph(groq_key, tavily_key,
                                       use_breakpoint, max_iterations)
        loop_ctr["n"] = 0  # reset counter for new run

        config        = {"configurable": {"thread_id": "streamlit_session"}}
        initial_state = {
            "task":              task,
            "research_notes":    [],
            "retry_count":       0,
            "draft":             "",
            "next_node":         "",
            "revision_feedback": "",
        }

        log("system", "▶", "Graph started", f"Task: <em>{task}</em>")

        # Phase 1 — stream until breakpoint or end
        for event in graph.stream(initial_state, config, stream_mode="values"):
            nxt   = event.get("next_node", "")
            notes = event.get("research_notes", [])
            draft = event.get("draft", "")
            fb    = event.get("revision_feedback", "")

            if nxt == "researcher":
                log("supervisor", "🧠", "Supervisor → Researcher",
                    f"Instructions: {fb or 'Gather research on the topic'}")
            elif nxt == "writer":
                log("supervisor", "🧠", "Supervisor → Writer",
                    f"Notes collected: {len(notes)} | Instructions: {fb}")
            elif nxt == "FINISH":
                log("supervisor", "🧠", "Supervisor → FINISH",
                    "Sufficient research and draft produced.")

            if notes and len(notes) > (len(event.get("research_notes", [])) - 1):
                log("researcher", "🔍", f"Researcher returned {len(notes)} note(s)",
                    f"Latest: {str(notes[-1])[:300]}…")

            if draft:
                log("writer", "✍️", "Writer produced draft",
                    f"{len(draft)} characters")

        # Check for breakpoint pause
        snapshot = graph.get_state(config)
        if snapshot.next:
            log("pause", "⏸", f"Paused — next step: {snapshot.next}",
                f"Supervisor feedback: {snapshot.values.get('revision_feedback','')}")

            col_a, col_b = st.columns(2)
            with col_a:
                resume_btn = st.button("▶ Resume (approve & continue writing)",
                                        type="primary")
            with col_b:
                abort_btn = st.button("✖ Abort")

            if resume_btn:
                log("system", "▶", "Resuming graph after human approval")
                for event in graph.stream(None, config, stream_mode="values"):
                    nxt   = event.get("next_node", "")
                    draft = event.get("draft", "")
                    if nxt:
                        log("supervisor", "🧠", f"Supervisor → {nxt}")
                    if draft:
                        log("writer", "✍️", "Writer produced draft",
                            f"{len(draft)} characters")

            if abort_btn:
                log("system", "✖", "Run aborted by user.")
                st.stop()

        # Final result
        final = graph.get_state(config).values
        draft = final.get("draft", "")

        if draft:
            st.divider()
            st.subheader("📄 Final Report")
            st.markdown(draft)

            with st.expander("🗂 Raw research notes"):
                for i, note in enumerate(final.get("research_notes", []), 1):
                    st.markdown(f"**Note {i}:**")
                    st.text(note[:1500] + ("…" if len(note) > 1500 else ""))

            st.download_button(
                "⬇ Download report (.md)",
                data=draft,
                file_name="emotion_research_report.md",
                mime="text/markdown",
            )
        else:
            st.warning("Graph finished without producing a draft. Try increasing max loops.")

    except Exception as e:
        st.error(f"**Error:** {e}")
        st.exception(e)
