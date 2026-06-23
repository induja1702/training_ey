### **Scenario 2: Claims Adjudication (Insurance)**

**Selected Pattern: GraphFlow**

 

**Justification**

The problem clearly states:

Three independent checks running in parallel

    * Fraud
    * Policy coverage
    * Medical coding
Outputs are then combined into a final decision:
 This matches a Directed Graph Workflow:
 Parallel execution nodes
 Aggregation node at the end


Why GraphFlow:
Explicit control over:
1. Parallel branches
2. Dependency (final step depends on all results)


**Other patterns fail:**

* Swarm → too unstructured
* Selector → single-agent routing only
* Round-robin → no parallelism

 
**BLOCK DIAGRAM:**

                +----------------------+

                |   Claim Input        |

                +----------+-----------+

                           |

                           v

        ---------------------------------------------

        |                    |                     |

        v                    v                     v

    +----------------+  +----------------+  +----------------------+
    
    | Fraud Check    |  | Policy Check   |  | Medical Coding Check |
    
    +--------+-------+  +--------+-------+  +----------+-----------+

         \                 |                     /

          \                |                    /

           \---------------+-------------------/

                           v

                +----------------------+

                | Decision Agent       |

                | (Approve / Deny)     |

                +----------+-----------+

                           |

                           v

                +----------------------+

                | Final Output         |

                +----------------------+
