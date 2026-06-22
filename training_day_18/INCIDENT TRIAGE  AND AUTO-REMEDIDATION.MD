ANS: Multi-agent

 

Justification (Why Multi-Agent over Single-Agent)

From the problem statement:

Multiple independent investigations (a–c)
Datadog metrics analysis
GitHub deployment logs analysis
AWS RDS database query check
Concurrent execution required
Different tools/APIs involved
Conditional execution (human approval if confidence < 80%)
Final structured output required (RCA → Slack)
 

| Advantage                     | Explanation                                                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Parallel Investigations**   | Metrics analysis, log inspection, and database checks run simultaneously, accelerating root-cause discovery.                  |
| **Tool Specialization**       | Each agent is integrated with a specific system or tool, enabling deeper expertise and more accurate diagnostics.             |
| **Faster Triaging**           | Concurrent analysis reduces **MTTR (Mean Time to Resolution)** by identifying issues more quickly.                            |
| **Controlled Automation**     | A **Human-in-the-Loop (HITL)** approval gate ensures remediation actions are reviewed before execution.                       |
| **Resilience & Isolation**    | Failures in one agent do not block other agents, improving overall system reliability and fault tolerance.                    |
| **Structured RCA Generation** | A dedicated communication/reporting agent automatically generates clear and consistent **Root Cause Analysis (RCA)** reports. |


Multi-Agent Architecture Design

Agents Overview

Investigation Agents (Concurrent)

Metrics Analysis Agent (Datadog)
Deployment Logs Agent (GitHub Actions)
Database Analysis Agent (AWS RDS)
Decision & Action Agents

Root Cause Aggregator Agent
Remediation Agent (kubectl actions)
Communication Agent (Slack RCA)
Control Layer

Orchestrator Agent (with human approval gate)
 

Tentative Block Diagram

                         ┌────────────────────────────┐
                         │     Orchestrator Agent     │
                         │ (workflow + gating logic)  │
                         └────────────┬───────────────┘
                                      │

─── Step 1: Concurrent Sub-Investigations ───
                                      │
        ┌───────────────┬───────────────┬───────────────┐
        ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Metrics Agent  │ │ Deployment     │ │ Database       │
│ (Datadog API)  │ │ Logs Agent     │ │ Agent (RDS)    │
│ (latency spike)│ │ (GitHub logs)  │ │ (slow queries) │
└────────────────┘ └────────────────┘ └────────────────┘
        │               │               │
        └───────────────┴───────────────┘
                        ▼
          ┌────────────────────────────────┐
          │ Root Cause Aggregator Agent    │
          │ (correlates signals, confidence)│
          └────────────────────────────────┘
                        │
                        ▼
         Confidence Score Computed (e.g., 85%)

│
            ─── Decision Gate (Human-in-loop) ───
                        │
     ┌──────────────────┴──────────────────┐
     │                                     │
     ▼                                     ▼
Confidence ≥ 80%                    Confidence < 80%
Auto Remediation                    Require Approval
     │                                     │
     ▼                                     ▼
┌──────────────────────────┐      ┌────────────────────────┐
│ Remediation Agent        │      │ Human Approval System  │
│ (kubectl rollback/restart)│     │ (Manual validation)    │
└──────────────────────────┘      └────────────────────────┘
                │
                ▼

─── Final Step: Communication ───
                │
                ▼
   ┌───────────────────────────────────┐
   │ Communication Agent (Slack)       │
   │ - RCA summary                     │
   │ - Actions taken                  │
   │ - Impact + metrics               │
   └───────────────────────────────────┘
                │
                ▼
        ┌──────────────────────┐
        │ Incident Closed      │
        └──────────────────────┘

