| Domain                 | Key Question                    | Decision in Amazon MCP Case Study                 |
| ---------------------- | ------------------------------- | ------------------------------------------------- |
| Discovery              | How are tools found?            | Static discovery, pinned MCP servers              |
| Topology               | How components communicate?     | Single orchestrator + multi-server MCP            |
| Trust Boundary         | Who owns what data?             | Ads in Amazon boundary, SP-API in seller boundary |
| Authorization          | What can each component access? | Least privilege + Restricted Data Tokens          |
| Authentication         | How identities are verified?    | Amazon credentials, signed requests               |
| Human-in-the-Loop      | Which actions need approval?    | Pricing, spend, inventory commitments             |
| State Management       | Long-running workflows?         | Async jobs for reports                            |
| Communication Protocol | How services talk?              | MCP → JSON-RPC → HTTPS                            |
| Eventing               | Polling or events?              | Event-driven                                      |
| Governance             | How are tools controlled?       | Allowlist approved servers                        |
| Security               | What are attack vectors?        | Prompt injection, tool misuse                     |
| Multi-Tenancy          | How agencies isolate clients?   | Per-client credentials                            |
| Reliability            | Handling quotas/failures?       | Rate-limit aware MCP server                       |
| Auditability           | How actions are traced?         | Log every tool invocation                         |
| Profitability Data     | Source of truth?                | Amazon data + private COGS                        |


**Design Diagram:**
                  
                     ┌────────────────────┐
                     │  Seller / Agency   │
                     └──────────┬─────────┘
                                │
                                ▼
                 ┌─────────────────────────┐
                 │   Orchestrator Agent    │
                 └──────────┬──────────────┘
                            │
      ┌─────────────────────┼─────────────────────┐
      │                     │                     │
      ▼                     ▼                     ▼
    
    ┌───────────────┐  ┌────────────────┐  ┌────────────────┐
    │ Ads MCP       │  │ SP-API MCP     │  │ Cost Service   │
    │ Server        │  │ Server         │  │ (COGS)         │
    └──────┬────────┘  └───────┬────────┘  └───────┬────────┘
           │                   │                   │
           ▼                   ▼                   ▼
    
     Campaigns         Inventory/Orders       Product Cost
     Reports           Returns/Listings       Margin Data

       └───────────────┬───────────────────┘
                       │
                       ▼

             ┌──────────────────┐
             │ Decision Engine  │
             └─────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │

         ▼             ▼             ▼

     Autonomous     Draft Actions    Human Approval
     Reads          Messages         Price Changes
     Reports         Campaigns       Budget Changes
     Analytics                      Repricing


1. Domain-by-Domain Design Rationale 
Discovery
**Agent**
*   +-- Ads MCP Server
*   +-- SP-API MCP Server
*   +-- COGS Service
Static configuration
No dynamic registry
Smaller attack surface

2. Authorization
**Agent:**
*  +-- Inventory Role
*  +-- Orders Role
*  +-- Ads Role
*  +-- Restricted Data Token
Principle of Least Privilege
RDT only for PII access

3. Human Approval Layer

Action
  |
  ├── Read?  → Execute
  |
  ├── Draft? → Execute + Log
  |
  └── Money?
          |
          ▼
      Human Review

This is the most important enterprise AI pattern.