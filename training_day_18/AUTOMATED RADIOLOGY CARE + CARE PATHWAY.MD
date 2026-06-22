

ANS: Multi-agent

 

Justification (Why Multi-Agent over Single-Agent)

From the problem statement:

 

 

4 distinct domains:

 

Radiology image interpretation

Clinical decision support (medications + contraindications)

Scheduling workflows (EMR integration)

Communication (GP letter + patient summary)

Sequential workflow with gating

Different tools & expertise required

Different failure modes (high risk in healthcare)

 

why Multi-agent


| Advantage                     | Explanation                              |

| ----------------------------- | ---------------------------------------- |

| **Domain specialization**     | Each agent is expert in its task         |

| **Sequential gating**         | Validate output before next step         |

| **Tool-specific integration** | Vision model, EMR APIs, scheduling tools |

| **Fault isolation**           | If one step fails → stop safely          |

| **Regulatory compliance**     | Easier auditing & logging                |

| **Safety-first design**       | Critical in healthcare workflows        

 

Multi-Agent Architecture Design

 

Agents Overview

Radiology Report Agent
Clinical Decision Support Agent
Care Pathway / Scheduling Agent
Communication Agent
Orchestrator (Controller with Gates)
Tentative Block Diagram

                    ┌──────────────────────────────┐
                    │      Orchestrator Agent      │
                    │ (workflow + gating control)  │
                    └────────────┬─────────────────┘
                                 │
                  Shared Patient Context Object
                                 │
Step 1: Imaging Analysis (Gate 1 Validation)
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │ Radiology Report Agent   │
                  │ (CT Scan → Findings)     │
                  │ (Vision + LLM model)     │
                  └──────────────────────────┘
                                 │
                     Radiologist-grade validation
                                 │

Step 2: Clinical Reasoning (Gate 2 Safety Check)
                                 │
                                 ▼
           ┌──────────────────────────────────────┐
           │ Clinical Decision Support Agent      │
           │ - Cross-check medications            │
           │ - Detect contraindications           │
           │ - Recommend diagnostics              │
           └──────────────────────────────────────┘
                                 │
                      Medical safety validation
                                 │

Step 3: Care Pathway Execution
                                 │
                                 ▼
              ┌─────────────────────────────┐
              │ Scheduling Agent            │
              │ - Book biopsy / PET scan    │
              │ - Integrate with EMR        │
              └─────────────────────────────┘
                                 │

Step 4: Communication Layer
                                 │
                                 ▼
        ┌──────────────────────────────────────┐
        │ Communication Agent                  │
        │ - GP letter generation               │
        │ - Patient-friendly summary           │
        └──────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ Final Output Delivery  │
                    │ EMR + Reports + Letters│
                    └────────────────────────┘