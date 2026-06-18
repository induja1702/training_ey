
| ID | Integration                 | Classification | Key deciding factor                                                                              |

| -- | --------------------------- | -------------- | ------------------------------------------------------------------------------------------------ |

| A  | Settlement command          | **Queue**      | It is a command where exactly one consumer must process the request and ensure work is completed |

 

| B  | Payment received broadcast  | **Event Bus**  | Multiple independent services may need to react to the payment event (fan-out scenario)          |

 

| C  | SMS / push notifications    | **Event Bus**  | Same event can trigger multiple notification services (email, SMS, push)                         |

 

| D  | Fraud score request         | **Queue**      | Request-response pattern where only one service should process the scoring                       |

 

| E  | Account state change events | **Event Bus**  | Broadcasting state changes to multiple subscribers without coupling                              |

 

| F  | End-of-day reconciliation   | **Queue**      | A specific job/task that must be processed reliably by a controlled consumer set                 |

 

***

 

 

Merchant API → Payment Core → Ledger Service

                            → Fraud Engine

                            → Notification Hub

                            → Analytics Pipeline

 

 

Merchant API----Receives payment requests

Payment Core----Coordinates the transaction flow

Ledger Service----Final source of truth for money

Fraud Engine----Calculates fraud risk in real-time

Notification Hub----Sends SMS, email, push notifications.

 

 
BLOCK DIAGRAM
 

[Merchant API]

                       |

                    (Queue)

                       |

                [Payment Core]

                   /    \

          (Queue) /      \ (Queue)

               /          \

     [Fraud Engine]   [Ledger Service]

                             |

                       (Event Bus)

                             |

         -----------------------------------

         |             |                  |

[Notification Hub] [Analytics]   [Future services]
