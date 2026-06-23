import asyncio
import websockets


async def listen():

    async with websockets.connect(
        "ws://localhost:8000/ws"
    ) as websocket:

        while True:
            message = await websocket.recv()
            print(f"Received: {message}")


asyncio.run(listen())


# output
# (venv) PS C:\Users\Administrator\Downloads\training_ey\training_day_19\Homework_2\push_demo> python .\push_client.py
# Received: Notification #1
# Received: Notification #2
# Received: Notification #3
# Received: Notification #4
# Received: Notification #5
# Received: Notification #6
# Received: Notification #7