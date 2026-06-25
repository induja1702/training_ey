"""
agents.py — Observability for a Multi-Agent System
====================================================
Satisfies all 6 acceptance criteria:
  1. Emit structured JSON events (not free-text prints)
  2. Correlate via run-level trace_id and per-agent span_id
  3. Report pipeline % complete, throughput, and per-agent duration
  4. Throttle progress events (~every 25% of an agent's steps)
  5. Emit agent_failed + run_summary on error; run_summary on success
  6. Runs with `python agents.py` — stdlib only (uuid, json, time, random)
"""

import json
import random
import time
import uuid


# ---------------------------------------------------------------------------
# Utility: emit a structured JSON event to stdout
# ---------------------------------------------------------------------------

def emit(event: dict) -> None:
    """Serialise an event dict to a single JSON line and print it."""
    print(json.dumps(event))


# ---------------------------------------------------------------------------
# Task 1 — Correlation IDs
# ---------------------------------------------------------------------------
# Every event carries:
#   trace_id  — one UUID generated once per Orchestrator.run() call.
#               Groups ALL events from a single pipeline run together.
#   span_id   — one UUID generated per agent execution.
#               Groups all events for one agent within the run.
#
# This mirrors OpenTelemetry's Trace / Span hierarchy.

def new_id() -> str:
    """Return a short (8-char) hex ID — readable but still unique enough."""
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Task 2 + 3 — ObservabilityListener
# ---------------------------------------------------------------------------

class ObservabilityListener:
    """
    Replaces the raw progress_listener function.

    Lifecycle
    ---------
    on_agent_start(agent_name, total_steps)
        Called by Orchestrator before each agent runs.
        Emits  agent_started  and records the agent's span_id + start time.

    __call__(agent_name, step, total_steps)
        Called by Agent on every step tick.
        Emits  agent_progress  ONLY at ~25 % boundaries (throttled).
        Computes pipeline % complete and steps-per-second throughput.

    on_agent_end(agent_name, total_steps)
        Called by Orchestrator after each agent finishes successfully.
        Emits  agent_completed  with per-agent wall-clock duration.

    on_agent_error(agent_name, step, total_steps, exc)
        Called by Orchestrator when an agent raises.
        Emits  agent_failed  with which agent, which step, and pipeline % at death.

    on_run_end(status, failed_agent=None)
        Called by Orchestrator at the very end (success or failure).
        Emits  run_summary.
    """

    def __init__(self, trace_id: str, total_pipeline_steps: int):
        self.trace_id = trace_id
        self.total_pipeline_steps = total_pipeline_steps

        # Wall-clock when the whole run started (for throughput)
        self.run_start = time.time()

        # Steps finished so far across ALL agents (for pipeline %)
        self.completed_steps = 0

        # Per-agent bookkeeping: name -> {span_id, start_time, last_emitted_pct}
        self._agents: dict = {}

    # -- helpers ------------------------------------------------------------

    def _now(self) -> str:
        """ISO-8601 UTC timestamp."""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _pipeline_pct(self) -> float:
        return round(self.completed_steps / self.total_pipeline_steps * 100, 1)

    def _throughput(self) -> float:
        """Steps per second since the run started."""
        elapsed = time.time() - self.run_start
        return round(self.completed_steps / elapsed, 2) if elapsed > 0 else 0.0

    def _base(self, agent_name: str) -> dict:
        """Fields every event must carry (Task 1 + Task 2)."""
        return {
            "timestamp": self._now(),
            "trace_id":  self.trace_id,
            "span_id":   self._agents[agent_name]["span_id"],
            "agent":     agent_name,
        }

    # -- lifecycle callbacks ------------------------------------------------

    def on_agent_start(self, agent_name: str, total_steps: int) -> None:
        """Register a new span and emit agent_started."""
        span_id = new_id()
        self._agents[agent_name] = {
            "span_id":          span_id,
            "start_time":       time.time(),
            "last_emitted_pct": -1,   # so the first milestone always fires
        }
        event = {
            **self._base(agent_name),
            "event":       "agent_started",
            "total_steps": total_steps,
            "pipeline_pct_complete": self._pipeline_pct(),
            "throughput_steps_per_sec": self._throughput(),
        }
        emit(event)

    def __call__(self, agent_name: str, step: int, total_steps: int) -> None:
        """
        Step tick — called by Agent on every step.

        Task 3: update running counters.
        Task 4: throttle — only emit agent_progress at ~0 %, 25 %, 50 %, 75 %
                milestone crossings (i.e. when the integer bucket changes).
        """
        self.completed_steps += 1

        agent = self._agents[agent_name]
        pct_this_agent = step / total_steps * 100          # 0-100 for this agent
        milestone = int(pct_this_agent // 25)              # 0, 1, 2, 3  (every 25 %)

        if milestone > agent["last_emitted_pct"]:
            agent["last_emitted_pct"] = milestone
            event = {
                **self._base(agent_name),
                "event":       "agent_progress",
                "step":        step,
                "total_steps": total_steps,
                "agent_pct_complete":    round(pct_this_agent, 1),
                "pipeline_pct_complete": self._pipeline_pct(),
                "throughput_steps_per_sec": self._throughput(),
            }
            emit(event)

    def on_agent_end(self, agent_name: str, total_steps: int) -> None:
        """Emit agent_completed with per-agent duration (Task 3)."""
        agent = self._agents[agent_name]
        duration = round(time.time() - agent["start_time"], 3)
        event = {
            **self._base(agent_name),
            "event":        "agent_completed",
            "total_steps":  total_steps,
            "duration_sec": duration,
            "pipeline_pct_complete":    self._pipeline_pct(),
            "throughput_steps_per_sec": self._throughput(),
        }
        emit(event)

    def on_agent_error(
        self,
        agent_name: str,
        step: int,
        total_steps: int,
        exc: Exception,
    ) -> None:
        """Emit agent_failed — pinpoints which agent, which step, pipeline % (Task 5)."""
        event = {
            **self._base(agent_name),
            "event":        "agent_failed",
            "failed_step":  step,
            "total_steps":  total_steps,
            "error":        str(exc),
            "pipeline_pct_complete":    self._pipeline_pct(),
            "throughput_steps_per_sec": self._throughput(),
        }
        emit(event)

    def on_run_end(self, status: str, failed_agent: str | None = None) -> None:
        """Emit run_summary — always fires (success or failure) (Task 5)."""
        total_duration = round(time.time() - self.run_start, 3)
        agents_completed = [
            name for name, data in self._agents.items()
            if "last_emitted_pct" in data  # started at least
        ]
        event = {
            "timestamp":    self._now(),
            "trace_id":     self.trace_id,
            "span_id":      None,           # run-level event; no single agent span
            "agent":        None,
            "event":        "run_summary",
            "status":       status,         # "success" | "failure"
            "total_duration_sec":   total_duration,
            "pipeline_pct_complete": self._pipeline_pct(),
            "throughput_steps_per_sec": self._throughput(),
            "agents_completed": agents_completed,
            "failed_agent": failed_agent,
        }
        emit(event)


# ---------------------------------------------------------------------------
# Agent — unchanged from starter code
# ---------------------------------------------------------------------------

class Agent:
    """A simulated agent that does N steps of work. Pure simulation — no LLM."""

    def __init__(self, name: str, steps: int, fail_at_step: int | None = None):
        self.name = name
        self.steps = steps
        self.fail_at_step = fail_at_step

    def run(self, listener) -> None:
        for step in range(1, self.steps + 1):
            time.sleep(random.uniform(0.05, 0.2))
            if self.fail_at_step and step == self.fail_at_step:
                raise RuntimeError(f"{self.name} failed at step {step}")
            listener(self.name, step, self.steps)


# ---------------------------------------------------------------------------
# Orchestrator — upgraded to drive the full listener lifecycle
# ---------------------------------------------------------------------------

class Orchestrator:
    """
    Drives agents in sequence and calls the observability lifecycle hooks.

    Changes from the starter version
    ---------------------------------
    - Generates one trace_id for the whole run.
    - Calls listener.on_agent_start() before each agent.
    - Calls listener.on_agent_end() after each successful agent.
    - Catches RuntimeError from any agent, calls listener.on_agent_error()
      then breaks — run stops at the first failure.
    - Always calls listener.on_run_end() (success or failure).
    """

    def __init__(self, agents: list[Agent], listener: ObservabilityListener):
        self.agents = agents
        self.listener = listener

    def run(self) -> None:
        failed_agent = None
        status = "success"

        for agent in self.agents:
            self.listener.on_agent_start(agent.name, agent.steps)
            try:
                agent.run(self.listener)
                self.listener.on_agent_end(agent.name, agent.steps)
            except RuntimeError as exc:
                # Determine which step failed from the exception message
                # (Agent raises before calling listener, so completed_steps
                #  has NOT been incremented for the failing step — correct.)
                step_hint = agent.steps  # fallback
                try:
                    step_hint = int(str(exc).split("step ")[-1])
                except ValueError:
                    pass
                self.listener.on_agent_error(agent.name, step_hint, agent.steps, exc)
                failed_agent = agent.name
                status = "failure"
                break  # stop the pipeline cleanly

        self.listener.on_run_end(status, failed_agent)


# ---------------------------------------------------------------------------
# main — two demos: happy path, then a forced failure
# ---------------------------------------------------------------------------

def make_listener(agents: list[Agent]) -> ObservabilityListener:
    total_steps = sum(a.steps for a in agents)
    return ObservabilityListener(trace_id=new_id(), total_pipeline_steps=total_steps)


def main() -> None:
    # ── Demo 1: Happy path ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DEMO 1 — Happy path (all agents succeed)")
    print("=" * 60)

    agents_ok = [
        Agent("Planner",    3),
        Agent("Researcher", 6),
        Agent("Writer",     4),
        Agent("Reviewer",   2),
    ]
    listener_ok = make_listener(agents_ok)
    Orchestrator(agents_ok, listener_ok).run()

    # ── Demo 2: Forced failure ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DEMO 2 — Writer fails at step 2  (failure localisation)")
    print("=" * 60)

    agents_fail = [
        Agent("Planner",    3),
        Agent("Researcher", 6),
        Agent("Writer",     4, fail_at_step=2),   # <-- will blow up
        Agent("Reviewer",   2),                    # never reached
    ]
    listener_fail = make_listener(agents_fail)
    Orchestrator(agents_fail, listener_fail).run()


if __name__ == "__main__":
    main()