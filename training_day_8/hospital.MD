Application Gateway or Load Balancer


| # | Requirement                   | Classification          | Key deciding factor                              |

| - | ----------------------------- | ----------------------- | ------------------------------------------------ |

| 1 | Patient web portal            | **Application Gateway** | HTTPS traffic + WAF + URL-based routing required |

| 2 | Clinical API (internal)       | **Load Balancer**       | Internal TCP traffic, no HTTP awareness          |

| 3 | DICOM image streaming         | **Load Balancer**       | Raw TCP + long-lived sessions + high throughput  |

| 4 | Auth service (header routing) | **Application Gateway** | Header-based routing + Layer 7 inspection        |

| 5 | Legacy SOAP lab service       | **Load Balancer**       | TCP only + no inspection + simple failover       |

| 6 | Admin dashboard (hostname)    | **Application Gateway** | Host-based routing + HTTPS                       |


BLOCK DIAGRAM

Internet Users

   |

   v

Public DNS

(site1.com, site2.com)

   |

   v

Azure Application Gateway

   |-- Listener: site1.com  ---> Rule ---> Backend Pool 1

   |                                      |

   |                                      v

   |                              Azure Load Balancer (optional)

   |                                      |

   |                                      v

   |                              Site 1 App Servers / VMSS

   |

   |-- Listener: site2.com  ---> Rule ---> Backend Pool 2

                                          |

                                          v

                                  Azure Load Balancer (optional)

                                          |

                                          v

                                  Site 2 App Servers / VMSS