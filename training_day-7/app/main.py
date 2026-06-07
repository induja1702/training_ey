import uvicorn
from fastapi import FastAPI, HTTPException

from pydantic import BaseModel, Field

from typing import List

import uuid

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],  # allow all (for testing)

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)

tasks = []


class Task(BaseModel):
    title: str = Field(..., min_length=1)

    priority: str | None = None


@app.get("/")
def list_tasks():
    return tasks


@app.post("/tasks", status_code=201)
def create_task(task: Task):
    new_task = task.dict()

    new_task["id"] = str(uuid.uuid4())

    tasks.append(new_task)

    return new_task


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    for task in tasks:

        if task["id"] == task_id:
            return task

    raise HTTPException(status_code=404, detail="Task not found")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)