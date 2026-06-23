from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    count = 1

    while True:
        message = f"Notification #{count}"
        await websocket.send_text(message)

        count += 1

        await asyncio.sleep(5)


# output
# INFO:     Will watch for changes in these directories: ['C:\\Users\\Administrator\\Downloads\\training_ey\\training_day_19\\Homework_2\\push_demo']
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [19128] using StatReload
# INFO:     Started server process [8548]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     ('127.0.0.1', 52709) - "WebSocket /ws" [accepted]
# INFO:     connection open