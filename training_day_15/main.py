import os
import asyncio
from fastapi import FastAPI
import uvicorn
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.cosmos import CosmosClient
from groq import Groq

app = FastAPI(title="Pipeline API with Groq")

# Environment Variables
SB_CONN_STR = os.getenv("SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = "input-queue"
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialization
cosmos_client = CosmosClient(COSMOS_URI, credential=COSMOS_KEY)
db = cosmos_client.get_database_client("PipelineDB")
container = db.get_container_client("Items")

# Initialize the Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

@app.post("/ingest")
async def ingest_data(payload: dict):
    """Step 1: Input Queue - Accepts data and pushes it onto the queue."""
    async with ServiceBusClient.from_connection_string(SB_CONN_STR) as client:
        sender = client.get_queue_sender(queue_name=QUEUE_NAME)
        message = ServiceBusMessage(str(payload))
        await sender.send_messages(message)
    return {"status": "Message queued successfully"}

@app.get("/extend/{item_id}")
async def extend_with_groq(item_id: str):
    """Step 4 & 5: Fetch from Store, FastAPI processing, and Extend via Groq API."""
    # Read raw document from Cosmos DB
    item = container.read_item(item=item_id, partition_key=item_id)
    
    # Send processing request to Groq using an open-weights model
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user", 
                "content": f"Summarize and analyze this data cleanly: {item}"
            }
        ],
        temperature=0.2,
        max_tokens=1024
    )
    
    return {
        "original_data": item,
        "groq_analysis": response.choices[0].message.content
    }

async def queue_processor():
    """Step 2 & 3: Background processor reading from Queue and writing to Store."""
    while True:
        try:
            async with ServiceBusClient.from_connection_string(SB_CONN_STR) as client:
                receiver = client.get_queue_receiver(queue_name=QUEUE_NAME)
                async with receiver:
                    messages = await receiver.receive_messages(max_message_count=1, max_wait_time=5)
                    for msg in messages:
                        data_str = str(msg)
                        # Process and write to Cosmos DB
                        container.upsert_item({"id": str(msg.sequence_number), "content": data_str})
                        await receiver.complete_message(msg)
        except Exception as e:
            print(f"Processor Error: {e}")
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    # Start the queue processor loop asynchronously in the background
    asyncio.create_task(queue_processor())

if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )