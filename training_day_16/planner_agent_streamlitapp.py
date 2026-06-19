import streamlit as st
import os, json, time
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Planner",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Background */
.stApp {
    background: #0d0f14;
    color: #e2e8f0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111318 !important;
    border-right: 1px solid #1e2330;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 2rem;
}

/* Headers */
h1, h2, h3 { color: #f1f5f9; }

/* Cards */
.agent-card {
    background: #151820;
    border: 1px solid #1e2330;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.agent-card.active {
    border-color: #6366f1;
    box-shadow: 0 0 0 1px #6366f120, 0 4px 24px #6366f115;
}
.agent-card.done {
    border-color: #10b981;
    box-shadow: 0 0 0 1px #10b98120;
}
.agent-card.failed {
    border-color: #ef4444;
}

/* Agent badge */
.agent-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 10px;
}
.badge-planner  { background: #312e81; color: #a5b4fc; }
.badge-executor { background: #164e63; color: #67e8f9; }
.badge-verifier { background: #14532d; color: #86efac; }

/* Task pills */
.task-pill {
    display: inline-block;
    background: #1e2330;
    border: 1px solid #2d3550;
    color: #94a3b8;
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 20px;
    margin: 3px 3px 3px 0;
    font-family: 'Inter', sans-serif;
}

/* Score bar */
.score-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 6px 0;
}
.score-label {
    font-size: 12px;
    color: #64748b;
    width: 110px;
    flex-shrink: 0;
}
.score-bar-bg {
    flex: 1;
    height: 6px;
    background: #1e2330;
    border-radius: 3px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.4s;
}
.score-value {
    font-size: 12px;
    color: #94a3b8;
    width: 36px;
    text-align: right;
}

/* Result block */
.result-block {
    background: #0d0f14;
    border: 1px solid #1e2330;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    line-height: 1.7;
    color: #cbd5e1;
    margin-top: 8px;
    font-family: 'Inter', sans-serif;
    max-height: 200px;
    overflow-y: auto;
}

/* Iteration badge */
.iter-badge {
    font-size: 11px;
    background: #1e2330;
    color: #64748b;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
}

/* Status line */
.status-line {
    font-size: 12px;
    color: #6366f1;
    font-family: 'JetBrains Mono', monospace;
    padding: 8px 0;
}

/* Metric boxes */
.metric-box {
    background: #151820;
    border: 1px solid #1e2330;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
}
.metric-val {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}
.metric-lbl {
    font-size: 11px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 4px;
}

/* Input override */
.stTextInput input, .stTextArea textarea {
    background: #151820 !important;
    border: 1px solid #1e2330 !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px #6366f120 !important;
}

/* Button */
.stButton > button {
    background: #6366f1 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.2s !important;
}
.stButton > button:hover {
    background: #4f46e5 !important;
}

/* Pipeline connector */
.pipeline-connector {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #334155;
    font-size: 20px;
    margin: -4px 0;
    padding-left: 20px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0d0f14; }
::-webkit-scrollbar-thumb { background: #1e2330; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── State schema ─────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    goal: str
    tasks: List[str]
    results: List[str]
    critique: str
    approved: bool
    iterations: int
    scores: dict
    log: List[str]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.markdown("---")

    st.markdown("**Model**")
    model_name = st.selectbox("", [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
    ], label_visibility="collapsed")

    st.markdown("**Max Iterations**")
    max_iter = st.slider("", 1, 5, 3, label_visibility="collapsed")

    st.markdown("**Approval Threshold**")
    threshold = st.slider("", 0.0, 1.0, 0.7, 0.05, label_visibility="collapsed",
                          help="Minimum score for auto-approval")

    st.markdown("**Web Search**")
    # Use checkbox for broader Streamlit compatibility (st.toggle may not exist)
    use_search = st.checkbox("Enable DuckDuckGo search", value=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:11px;color:#334155;line-height:1.7">
    <b style="color:#475569">Architecture</b><br>
    🟣 Planner → decomposes goal<br>
    🔵 Executor → runs each task<br>
    🟢 Validator → scores & critiques<br>
    ↩️ Loop until approved or max iter
    </div>
    """, unsafe_allow_html=True)


# ── Main header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 2rem 0 1.5rem">
  <div style="font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#6366f1;margin-bottom:8px">
    Multi-Agent System
  </div>
  <h1 style="margin:0;font-size:2rem;font-weight:700;background:linear-gradient(90deg,#f1f5f9,#94a3b8);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
    Planner · Executor · Validator
  </h1>
  <p style="color:#475569;margin:8px 0 0;font-size:14px">
    Give it a goal. Watch the agents reason, execute, and self-correct.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Example goals ─────────────────────────────────────────────────────────────
examples = [
    "Research and summarise the top 3 trends in agriculture for 2025",
    "Create a beginner's study plan for learning Python in 30 days",
    "Write a competitive analysis of the top 3 cloud providers in 2025",
    "Outline a marketing strategy for a new mobile fitness app",
]

st.markdown("**Try an example goal:**")
ecols = st.columns(2)
for i, ex in enumerate(examples):
    if ecols[i % 2].button(f"↗ {ex[:55]}...", key=f"ex_{i}"):
        st.session_state["goal_input"] = ex

goal = st.text_area(
    "**Your goal**",
    value=st.session_state.get("goal_input", ""),
    placeholder="e.g. Research the top 3 AI trends shaping healthcare in 2025...",
    height=90,
    key="goal_text",
)

run_col, _ = st.columns([1, 4])
run_btn = run_col.button("▶ Run Agents", use_container_width=True)

st.markdown("---")


# ── Agent builders ────────────────────────────────────────────────────────────
def build_agents(llm, use_search, max_iter_val, threshold_val, log_placeholder, card_placeholders):

    search = DuckDuckGoSearchRun() if use_search else None
    logs = []

    def add_log(msg):
        logs.append(msg)

    def planner(state: AgentState) -> AgentState:
        add_log("🟣 Planner: decomposing goal into tasks...")
        system = """You are a planning agent. Break the user's goal into
at most 5 concrete, actionable tasks. Respond ONLY with a
valid JSON array of strings. No preamble, no markdown."""
        messages = [SystemMessage(content=system),
                    HumanMessage(content=f"Goal: {state['goal']}")]
        response = llm.invoke(messages).content.strip()
        try:
            clean = response.replace("```json", "").replace("```", "").strip()
            tasks = json.loads(clean)
        except json.JSONDecodeError:
            tasks = [response]
        add_log(f"🟣 Planner: generated {len(tasks)} tasks")
        return {**state, "tasks": tasks, "log": logs[:]}

    def executor(state: AgentState) -> AgentState:
        results = []
        critique_ctx = ""
        if state.get("critique"):
            critique_ctx = f"\n\nPrevious attempt was rejected. Critique: {state['critique']}"
        for i, task in enumerate(state["tasks"]):
            add_log(f"🔵 Executor: working on task {i+1}/{len(state['tasks'])}...")
            system = f"You are an execution agent. Complete the task thoroughly. {critique_ctx}"
            search_ctx = ""
            if search:
                try:
                    sr = search.run(task[:100])
                    search_ctx = f"\n\nWeb search result:\n{sr[:600]}"
                except Exception:
                    pass
            messages = [SystemMessage(content=system),
                        HumanMessage(content=f"Task: {task}{search_ctx}")]
            result = llm.invoke(messages).content
            results.append(result)
        add_log(f"🔵 Executor: completed {len(results)} tasks (iteration {state['iterations']+1})")
        return {**state, "results": results, "iterations": state["iterations"] + 1, "log": logs[:]}

    def verifier(state: AgentState) -> AgentState:
        if state["iterations"] >= max_iter_val:
            add_log("🟢 Validator: max iterations reached — force approving")
            return {**state, "approved": True, "log": logs[:]}

        combined = "\n\n".join(
            f"Task {i+1}: {t}\nResult: {r}"
            for i, (t, r) in enumerate(zip(state["tasks"], state["results"]))
        )
        system = f"""You are a quality verifier. Evaluate results against the original goal.
Score each dimension and return ONLY valid JSON (no markdown, no extra text):
{{"score": 0.85, "completeness_score": 0.35, "accuracy_score": 0.25, "clarity_score": 0.25, "approved": true, "critique": "reason if rejected"}}

Scoring rubric:
- completeness_score: Does it fully address the goal? (0–0.4)
- accuracy_score: Is it correct and specific? (0–0.3)  
- clarity_score: Is it well-structured and clear? (0–0.3)
- score: sum of above (0–1.0)
- approved: true if score >= {threshold_val}, else false"""

        messages = [SystemMessage(content=system),
                    HumanMessage(content=f"Original goal: {state['goal']}\n\nResults:\n{combined}")]
        raw = llm.invoke(messages).content.strip()
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            verdict = json.loads(clean)
            scores = {
                "completeness": float(verdict.get("completeness_score", 0)),
                "accuracy":     float(verdict.get("accuracy_score", 0)),
                "clarity":      float(verdict.get("clarity_score", 0)),
                "total":        float(verdict.get("score", 0)),
            }
            approved = verdict.get("approved", scores["total"] >= threshold_val)
            critique = verdict.get("critique", "")
        except Exception:
            scores = {"completeness": 0, "accuracy": 0, "clarity": 0, "total": 0}
            approved, critique = False, raw

        add_log(f"🟢 Validator: score={scores['total']:.2f} | approved={approved}")
        if not approved:
            add_log(f"   ↩ Critique: {critique[:120]}")
        return {**state, "approved": approved, "critique": critique, "scores": scores, "log": logs[:]}

    def route(state: AgentState) -> str:
        return "end" if state["approved"] else "executor"

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("verifier", verifier)
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "verifier")
    graph.add_conditional_edges("verifier", route, {"end": END, "executor": "executor"})
    graph.set_entry_point("planner")
    return graph.compile()


# ── Run ───────────────────────────────────────────────────────────────────────
if run_btn:
    if not groq_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar.")
        st.stop()
    if not goal.strip():
        st.error("⚠️ Please enter a goal.")
        st.stop()

    os.environ["GROQ_API_KEY"] = groq_key
    llm = ChatGroq(temperature=0, model_name=model_name, groq_api_key=groq_key)

    # ── Live pipeline display ────────────────────────────────────────────────
    st.markdown("### 🔄 Agent Pipeline")
    col1, a1, col2, a2, col3 = st.columns([3, 0.3, 3, 0.3, 3])

    with col1:
        planner_ph = st.empty()
    with a1:
        st.markdown("<div style='text-align:center;color:#1e2330;font-size:22px;padding-top:60px'>→</div>", unsafe_allow_html=True)
    with col2:
        executor_ph = st.empty()
    with a2:
        st.markdown("<div style='text-align:center;color:#1e2330;font-size:22px;padding-top:60px'>→</div>", unsafe_allow_html=True)
    with col3:
        verifier_ph = st.empty()

    log_ph = st.empty()
    results_ph = st.empty()

    def render_planner(tasks=None, status="idle"):
        css = "active" if status == "active" else ("done" if status == "done" else "")
        tasks_html = ""
        if tasks:
            tasks_html = "".join(f'<div class="task-pill">📌 {t[:55]}{"…" if len(t)>55 else ""}</div>' for t in tasks)
        planner_ph.markdown(f"""
        <div class="agent-card {css}">
          <div class="agent-badge badge-planner">🟣 Planner</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:8px">Decomposes your goal into actionable tasks</div>
          {f'<div style="margin-top:8px">{tasks_html}</div>' if tasks_html else '<div style="color:#334155;font-size:12px">Waiting...</div>'}
        </div>
        """, unsafe_allow_html=True)

    def render_executor(results=None, iteration=0, status="idle"):
        css = "active" if status == "active" else ("done" if status == "done" else "")
        content = f'<div style="color:#334155;font-size:12px">Waiting...</div>'
        if results:
            content = f"""
            <div class="iter-badge">Iteration {iteration}</div>
            <div class="result-block">{results[0][:500]}{"…" if len(results[0])>500 else ""}</div>
            <div style="font-size:11px;color:#334155;margin-top:6px">{len(results)} task(s) completed</div>
            """
        executor_ph.markdown(f"""
        <div class="agent-card {css}">
          <div class="agent-badge badge-executor">🔵 Executor</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:8px">Runs tasks, optionally with web search</div>
          {content}
        </div>
        """, unsafe_allow_html=True)

    def render_verifier(scores=None, approved=None, critique="", iteration=0, status="idle"):
        css = "active" if status == "active" else ("done" if (status=="done" and approved) else ("failed" if (status=="done" and not approved) else ""))
        content = '<div style="color:#334155;font-size:12px">Waiting...</div>'
        if scores:
            def bar(val, color):
                pct = min(int(val * 100), 100)
                return f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%;background:{color}"></div></div>'
            verdict_icon = "✅ Approved" if approved else "❌ Needs revision"
            verdict_color = "#10b981" if approved else "#ef4444"
            content = f"""
            <div style="margin-bottom:10px">
              <span style="font-size:13px;font-weight:600;color:{verdict_color}">{verdict_icon}</span>
              <span class="iter-badge" style="margin-left:8px">iter {iteration}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Completeness</span>
              {bar(scores['completeness']/0.4, '#6366f1')}
              <span class="score-value">{scores['completeness']:.2f}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Accuracy</span>
              {bar(scores['accuracy']/0.3, '#06b6d4')}
              <span class="score-value">{scores['accuracy']:.2f}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Clarity</span>
              {bar(scores['clarity']/0.3, '#8b5cf6')}
              <span class="score-value">{scores['clarity']:.2f}</span>
            </div>
            <div class="score-row" style="margin-top:4px;border-top:1px solid #1e2330;padding-top:6px">
              <span class="score-label" style="color:#94a3b8;font-weight:600">Total</span>
              {bar(scores['total'], '#10b981' if scores['total']>=threshold else '#f59e0b')}
              <span class="score-value" style="color:#f1f5f9;font-weight:600">{scores['total']:.2f}</span>
            </div>
            {f'<div style="font-size:11px;color:#ef4444;margin-top:8px;line-height:1.5">↩ {critique[:150]}</div>' if critique and not approved else ''}
            """
        verifier_ph.markdown(f"""
        <div class="agent-card {css}">
          <div class="agent-badge badge-verifier">🟢 Validator</div>
          <div style="font-size:13px;color:#64748b;margin-bottom:8px">Scores results and decides to approve or retry</div>
          {content}
        </div>
        """, unsafe_allow_html=True)

    # Initial render
    render_planner(status="active")
    render_executor(status="idle")
    render_verifier(status="idle")

    # ── Streaming callback via state polling ──────────────────────────────────
    final_state = None
    start_time = time.time()

    # We'll stream step by step using a custom runner
    initial_state: AgentState = {
        "goal": goal.strip(),
        "tasks": [],
        "results": [],
        "critique": "",
        "approved": False,
        "iterations": 0,
        "scores": {},
        "log": [],
    }

    app = build_agents(llm, use_search, max_iter, threshold,
                       log_placeholder=log_ph, card_placeholders=None)

    with st.spinner(""):
        for step in app.stream(initial_state):
            node = list(step.keys())[0]
            state = step[node]

            # Update log
            if state.get("log"):
                log_html = "".join(
                    f'<div class="status-line">{l}</div>' for l in state["log"][-6:]
                )
                log_ph.markdown(f"""
                <div style="background:#0d1117;border:1px solid #1e2330;border-radius:8px;padding:12px 16px;margin-top:1rem;font-family:'JetBrains Mono',monospace">
                  <div style="font-size:10px;color:#334155;margin-bottom:6px;letter-spacing:0.08em;text-transform:uppercase">Agent Log</div>
                  {log_html}
                </div>
                """, unsafe_allow_html=True)

            if node == "planner":
                render_planner(tasks=state.get("tasks", []), status="done")
                render_executor(status="active")
                render_verifier(status="idle")

            elif node == "executor":
                render_planner(tasks=state.get("tasks", []), status="done")
                render_executor(results=state.get("results", []),
                                iteration=state.get("iterations", 1), status="done")
                render_verifier(status="active")

            elif node == "verifier":
                scores = state.get("scores", {})
                approved = state.get("approved", False)
                critique = state.get("critique", "")
                render_planner(tasks=state.get("tasks", []), status="done")
                render_executor(results=state.get("results", []),
                                iteration=state.get("iterations", 1),
                                status="done")
                render_verifier(scores=scores, approved=approved,
                                critique=critique,
                                iteration=state.get("iterations", 1),
                                status="done")
                if not approved and state.get("iterations", 1) < max_iter:
                    time.sleep(0.3)
                    render_executor(status="active")

            final_state = state

    elapsed = time.time() - start_time

    # ── Final results ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Results")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    scores = final_state.get("scores", {})
    with m1:
        st.markdown(f"""<div class="metric-box">
          <div class="metric-val">{final_state.get('iterations',0)}</div>
          <div class="metric-lbl">Iterations</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="metric-box">
          <div class="metric-val">{len(final_state.get('tasks',[]))}</div>
          <div class="metric-lbl">Tasks run</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        total = scores.get('total', 0)
        col = "#10b981" if total >= threshold else "#f59e0b"
        st.markdown(f"""<div class="metric-box">
          <div class="metric-val" style="color:{col}">{total:.0%}</div>
          <div class="metric-lbl">Quality score</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        status_txt = "✅ Approved" if final_state.get("approved") else "⚠️ Max iter"
        status_col = "#10b981" if final_state.get("approved") else "#f59e0b"
        st.markdown(f"""<div class="metric-box">
          <div class="metric-val" style="font-size:18px;color:{status_col}">{status_txt}</div>
          <div class="metric-lbl">Final status · {elapsed:.1f}s</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)

    # Task + result tabs
    tasks = final_state.get("tasks", [])
    results = final_state.get("results", [])

    if tasks and results:
        st.markdown("**Completed Tasks**")
        tabs = st.tabs([f"Task {i+1}" for i in range(len(tasks))])
        for i, (tab, task, result) in enumerate(zip(tabs, tasks, results)):
            with tab:
                st.markdown(f"""
                <div style="background:#151820;border:1px solid #1e2330;border-radius:10px;padding:16px;margin-bottom:12px">
                  <div style="font-size:11px;color:#6366f1;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:6px">Task {i+1}</div>
                  <div style="font-size:14px;color:#e2e8f0;line-height:1.6">{task}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background:#0d0f14;border:1px solid #1e2330;border-radius:10px;padding:16px">
                  <div style="font-size:11px;color:#10b981;font-weight:600;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:8px">Result</div>
                  <div style="font-size:13px;color:#cbd5e1;line-height:1.75">{result}</div>
                </div>
                """, unsafe_allow_html=True)

    # Download
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
    export = {
        "goal": final_state.get("goal"),
        "tasks": tasks,
        "results": results,
        "scores": scores,
        "iterations": final_state.get("iterations"),
        "approved": final_state.get("approved"),
        "elapsed_seconds": round(elapsed, 2),
    }
    st.download_button(
        "⬇ Export results as JSON",
        data=json.dumps(export, indent=2),
        file_name="agent_results.json",
        mime="application/json",
    )

else:
    # ── Empty state ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;color:#334155">
      <div style="font-size:48px;margin-bottom:16px">🧠</div>
      <div style="font-size:16px;color:#475569;margin-bottom:8px">Enter a goal above and press <b style="color:#6366f1">Run Agents</b></div>
      <div style="font-size:13px;color:#334155">The planner will decompose it → executor will tackle each task → validator scores and retries if needed</div>
    </div>
    """, unsafe_allow_html=True)