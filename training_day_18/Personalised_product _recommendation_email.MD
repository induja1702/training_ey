Personalised Product Recommendation Email

 

Ans : Multi-agent-architecture

 

| Advantage                 | Explanation                                                                                                                             |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Parallelism**           | Agents can run independently, enabling faster processing and reduced overall execution time.                                            |
| **Specialization**        | Each agent is optimized for a specific task (e.g., ML inference, rule evaluation, text analysis, HTML processing).                      |
| **Scalability**           | Workloads can be distributed across multiple workers or services, making the system easier to scale.                                    |
| **Fault Isolation**       | If one agent or step fails, it can be handled independently without affecting the entire pipeline, allowing easier fallback mechanisms. |
| **Cost Optimization**     | Expensive LLM calls are used only where necessary (e.g., text understanding), while simpler tasks use cheaper methods.                  |
| **Meets < 3s Constraint** | Concurrent execution of agents helps achieve strict latency requirements and service-level agreements (SLAs).                           |

 

Multi-Agent Architecture Design


High-Level Agents

Data Retrieval Agent
Recommendation Agent (ML Model)
Business Rules Agent
Content Generation Agent (LLM)
Email Assembly Agent
Orchestrator / Controller Agent
 

Tentative Block Diagram

                    ┌──────────────────────────────┐

                    │      Orchestrator Agent      │

                    │ (controls workflow & timing) │

                    └────────────┬─────────────────┘

                                 │

               Shared User Context Object (central memory)

                                 │

     ┌───────────────────────────┼───────────────────────────┐

     │                           │                           │

     ▼                           ▼                           ▼

 

┌───────────────┐       ┌────────────────┐        ┌──────────────────┐

│ Data Retrieval│ ----> │ Recommendation │ -----> │ Business Rules   │

│   Agent       │       │    Agent (ML)  │        │    Agent         │

│ (history)     │       │ (Top-10 items) │        │ (filter items)   │

└───────────────┘       └────────────────┘        └──────────────────┘

                                                           │

                                                           ▼

                                              ┌────────────────────┐

                                              │ Content Generation │

                                              │ Agent (LLM)        │

                                              │ (intro paragraph)  │

                                              └────────────────────┘

                                                           │

                                                           ▼

                                              ┌────────────────────┐

                                              │ Email Assembly     │

                                              │ Agent              │

                                              │ (HTML formatting)  │

                                              └────────────────────┘

                                                           │

                                                           ▼

                                              ┌────────────────────┐

                                              │  Email Output /    │

                                              │  Delivery Queue    │

                                              └────────────────────┘

