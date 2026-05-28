from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def hello_world():
    return {"message": "Hello, World! This is my First program"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)


