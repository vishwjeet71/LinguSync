from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Input Data validation & other
from pydantic import BaseModel
from datetime import datetime

# Data base
from backend.appDataBase.ApplicationSql import (
    app_data_path,
    sql_path,
    load_data_from_sql,
    add_sql_data,
)

app = FastAPI(
    title="LinguSync", description="Local video Dudding System.", version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Input schema
class SaveProject(BaseModel):
    project_name: str


@app.get("/lingusync")
async def get_health():
    return {"status": "ok"}


@app.get("/system-paths")
async def get_paths():
    return {"app_data_path": app_data_path, "sql_path": sql_path}


@app.get("/load_data")
async def get_data():
    return load_data_from_sql()


@app.post("/save_project")
async def save_project(body: SaveProject):
    now = datetime.now()
    return add_sql_data(
        table_name="projects",
        data={
            "project_name": body.project_name,
            "created_at": now.strftime("On %Y-%m-%d at %H:%M"),
        },
    )