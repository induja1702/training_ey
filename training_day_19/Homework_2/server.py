from fastapi import FastAPI
import uvicorn

app = FastAPI()

status = "Processing"

@app.get("/status")
async def get_status():
    return {"status": status}


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )