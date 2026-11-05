from fastapi import FastAPI, Response, status, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Input Data validation & other
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Data base
from backend.appDataBase.ApplicationSql import (
    app_data_path,
    sql_path,
    load_data_from_sql,
    add_sql_data,
    fetch_record,
)

# Downloading Manager
from backend.resourcesManagement import (
    DownloadManager,
    get_file_credentials,
    inverse_file_status,
)
from contextlib import asynccontextmanager
import asyncio, os


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.download_manager = DownloadManager(str(app_data_path))
    yield
    await app.state.download_manager.close()


app = FastAPI(
    title="LinguSync",
    description="Local video Dudding System.",
    version="1.0",
    lifespan=lifespan,
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


class ProjectUpdate(BaseModel):
    project_id: int
    input_video: str


class Resources(BaseModel):
    model_name: str
    file_name: str


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
            response=response,
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


@app.post("/project/update")
async def update_project(body: ProjectUpdate, response: Response):

    try:
        return add_sql_data(
            table_name="projects",
            update=True,
            row_id=body.project_id,
            data={"input_video": body.input_video},
            response=response,
        )

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "CM": f"Failed to update project: {body.project_id}",
            "UM": "Unable to update your details.",
        }


@app.post("/downloads")
async def downloadResources(body: Resources, response: Response):

    manager = app.state.download_manager
    manifest_file_path = str(app_data_path) + "/models_manifest.json"

    if not os.path.exists(manifest_file_path):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "CM": "Model manifest file not found.",
            "UM": "Model information file is missing.",
        }

    model_name = body.model_name
    file_url, file_name, relative_path = get_file_credentials(
        body.file_name, model_name
    )

    isRemoval = inverse_file_status(model_name, file_name)

    # File removal
    if isRemoval:
        try:
            os.remove(f"{str(app_data_path)}/{relative_path + file_name}")

            inverse_file_status(model_name, file_name, inverse=True)

            return {
                "CM": f"{file_name} was removed from the device.",
                "UM": f"{file_name} was removed!",
            }

        except Exception as e:
            response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return {
                "CM": f"Failed to remove file '{file_name}'. Error: {e}",
                "UM": f"Unable to remove '{file_name}' from {model_name}.",
            }

    # Start download
    try:
        download_id = await manager.download_file(
            file_url, file_name, relative_path, model_name=model_name
        )

        return {"CM": download_id, "UM": f"{file_name} started downloading."}

    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"CM": f"Downloading failed: {e}", "UM": "Unable to download!"}

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "CM": f"Failed to download '{file_name}'. Error: {e}",
            "UM": f"Unable to download '{file_name}'. Please try again.",
        }


@app.delete("/downloads/{download_id}")
async def cancel_download(download_id: str, response: Response):

    manager = app.state.download_manager

    success = await manager.cancel_download(download_id)

    if not success:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {
            "CM": f"For {download_id} Download was not found or cannot be cancelled",
            "UM": "Download not found or cannot be cancelled",
        }

    return {"CM": f"process id: {download_id} cancelled", "UM": "cancelled"}


@app.get("/downloads/{download_id}")
async def download_status(download_id: str, response: Response):

    manager = app.state.download_manager
    process_status = manager.get_status(download_id)

    if not process_status:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            "CM": f"Download not found with id: {download_id}",
            "UM": "Download not found",
        }

    return process_status


@app.websocket("/downloads/{download_id}/progress")
async def download_progress(websocket: WebSocket, download_id: str):

    await websocket.accept()

    manager = app.state.download_manager

    try:
        while True:
            status = manager.get_status(download_id)

            if status is None:
                await websocket.send_json({"error": "Download not found"})
                break

            # Remove unnecessary fields before sending.
            status.pop("error", None) if status["error"] is None else None

            await websocket.send_json(status)

            if status["status"] in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(0.5)

    except Exception:
        pass

    finally:
        await websocket.close()


@app.get("/downloads")
async def get_active_downloads():
    manager = app.state.download_manager

    return {"downloads": manager.get_active_downloads()}
