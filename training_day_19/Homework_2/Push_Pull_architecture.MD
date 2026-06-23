Homework 2: Push vs Pull Notification Architecture

**Pull Architecture**
Client periodically checks server.

Client ---> Server
Client ---> Server
Client ---> Server

**Example:**
* Email refresh
* Polling API
* Job status checks


**Push Architecture**

Server initiates notification.

Server ---> Client

**Example:**

* WhatsApp message
* Mobile notifications
* WebSocket alerts