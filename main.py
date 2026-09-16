from fastapi import FastAPI, Response, status
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
    fetch_record,
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


class ProjectId(BaseModel):
    project_id: int


@app.get("/lingusync")
async def get_health():
    return {"status": "ok"}


@app.get("/system/paths")
async def get_paths():
    return {"app_data_path": app_data_path, "sql_path": sql_path}


@app.get("/load_data")
async def get_data(response: Response):

    try:
        return load_data_from_sql(response=response)

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"CM": f"Unable to load data: {e}", "UM": "Unable to load Data!"}


@app.post("/save_project")
async def save_project(body: SaveProject, response: Response):

    now = datetime.now()

    try:
        return add_sql_data(
            table_name="projects",
            data={
                "project_name": body.project_name,
                "created_at": now.strftime("On %Y-%m-%d at %H:%M"),
            },
            response=response
        )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "CM": f"Operation failed: {e}",
            "UM": "Something went wrong. Please try again later.",
        }


@app.post("/get/project")
async def get_project_by_id(body: ProjectId, response: Response):

    try:
        return fetch_record(row_id=body.project_id, response=response)

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "CM": f"Failed to load data for id: {body.project_id}: {e}",
            "UM": "Failed to load data.",
        }
