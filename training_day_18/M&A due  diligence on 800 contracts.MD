
   Ans : Multi Agent

 

Justification (Why Multi-Agent over Single-Agent)

800 contracts
Parallel extraction stage
Cross-document dependency at synthesis stage
Strict SLA: < 4 hours
Tasks involved:
Clause extraction (NLP-heavy)
Regulatory checklist matching
Cross-contract dependency analysis
Risk scoring + executive summary
Why Multi-agent

 

| Advantage                    | Explanation                                                                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Massive Parallelism**      | Up to **800 contracts** can be processed concurrently, significantly reducing overall processing time.                                          |
| **Task Specialization**      | Dedicated agents handle specific functions such as **data extraction, synthesis, and compliance validation**, improving efficiency and quality. |
| **Two-Stage Design Support** | Supports a workflow where agents operate in **parallel during extraction** and then perform **coordinated synthesis** for final outputs.        |
| **Faster Turnaround**        | Parallel execution helps meet the required **< 4-hour Service Level Agreement (SLA)**.                                                          |
| **Better Accuracy**          | Each agent is optimized for its domain, leading to more precise and reliable results.                                                           |
| **Clear Orchestration**      | Well-defined agent responsibilities make the system easier to **debug, monitor, and maintain**.                                                 |


Multi-Agent Architecture Design
Agents Overview

Stage 1 (Parallel Processing)

Document Extraction Agents (parallel workers)
Extract clauses (obligations, risks, terms)
Regulatory Matching Agent
Compares clauses with jurisdiction checklist
 

Stage 2 (Cross-Document Synthesis)

Dependency Analysis Agent
Detects cross-contract issues (e.g., cascading clauses)
Risk Scoring Agent
Assigns Red / Amber / Green
Executive Summary Agent
Generates final report
                       _____________________________________
                      |       Orchestrator Agent           |
                      |  Controls workflow and aggregation |
                      |____________________________________|             
                                      |
                         ┌────────────────────────────┐
                         │     Orchestrator Agent     │
                         │ (workflow + aggregation)   │
                         └────────────┬───────────────┘
                                      │

─── Stage 1: Parallel Processing ───
                                      │
            ┌───────────────┬───────────────┬───────────────┐
            ▼               ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Contract 1 │  │ Contract 2 │  │ Contract 3 │  │ Contract N │
   │ Extraction │  │ Extraction │  │ Extraction │  │ Extraction │
   │  Agent     │  │  Agent     │  │  Agent     │  │  Agent     │
   └────────────┘  └────────────┘  └────────────┘  └────────────┘
            │               │               │               │
            └───────┬───────┴───────┬───────┴───────┬───────┘
                    ▼               ▼               ▼

┌─────────────────────────────────────────────┐
           │ Regulatory Matching Agent                   │
           │ (check clauses vs compliance checklist)     │
           └─────────────────────────────────────────────┘
                                      │
                                      ▼

─── Stage 2: Cross-Document Synthesis ───
                                      │
           ┌──────────────────────────────────────────┐
           │ Dependency Analysis Agent                │
           │ (inter-contract clause relationships)    │
           └──────────────────────────────────────────┘
                                      │
                                      ▼
           ┌──────────────────────────────────────────┐
           │ Risk Scoring Agent                       │
           │ (Red / Amber / Green classification)     │
           └──────────────────────────────────────────┘
                                      │
                                      ▼
           ┌──────────────────────────────────────────┐
           │ Executive Summary Agent                  │
           │ (final M&A due diligence report)         │
           └──────────────────────────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │ Final Output Report  │
                          │ (Heatmap + Summary)  │
                          └──────────────────────┘

