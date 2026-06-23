### **1: Buyer’s Research Assistant (Retail)**

**Selected Pattern: Swarm / Handoff**

**Justification**

**The problem statement clearly mentions:**

* “Number and type of sub-tasks isn’t known in advance”
* May require web search + data lookups

**This implies:**

* Dynamic task decomposition
* Agents need to collaborate and hand off tasks flexibly

**Swarm / Handoff fits because:**

* Agents self-organize based on task needs
* Work is not predefined or sequential
* Each agent can pick or pass work dynamically


**Other patterns fail:**

* Round-robin → too rigid
* Selector → only chooses one agent at a time
* GraphFlow → requires predefined workflow


**BLOCK DIAGRAM**

                +-----------------------+

                |    User Query         |

                +----------+------------+

                           |

                           v

                +-----------------------+

                | Coordinator Agent     |

                +----------+------------+

                           |

        -----------------------------------------

        |                  |                    |

        v                  v                    v

    +----------------+  +----------------+  +----------------+
    
    | Trend Agent    |  | Web Search     |  | Supplier Agent |
    
    | (materials)    |  | Agent          |  | (data lookup)  |
    
    +--------+-------+  +--------+-------+  +--------+-------+

         \                 |                  /

          \                |                 /

           \---------------+----------------/

                           v

                +-----------------------+

                | Summarization Agent   |

                +----------+------------+

                           |

                           v

                +-----------------------+

                | Final Output          |

                +-----------------------+

|

 

 


 

 


