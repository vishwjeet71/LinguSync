# Database librarys
from sqlalchemy import create_engine, String, select, Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.engine import Engine

# Data librarys
import pandas as pd, json, os

# Directorie librarys
from platformdirs import PlatformDirs
from pathlib import Path

# FastApi & info
from fastapi import Response, status
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

APP_NAME = "com.vishwjeet.lingusync"

dirs = PlatformDirs(appname=APP_NAME, appauthor=False)
app_data_path = Path(dirs.user_data_path)
app_data_path.mkdir(parents=True, exist_ok=True)

db_path = str(app_data_path) + "/lingusync.db"
sql_path = f"sqlite:///{db_path}"

sql_engine = create_engine(sql_path)


class Base(DeclarativeBase):
    pass


class Projects(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(100), unique=True)
    input_video: Mapped[str] = mapped_column(String(100), nullable=True)
    stt_output: Mapped[str] = mapped_column(String(100), nullable=True)
    trans_output: Mapped[str] = mapped_column(String(100), nullable=True)
    tts_output: Mapped[str] = mapped_column(String(100), nullable=True)
    final_output: Mapped[str] = mapped_column(String(100), nullable=True)


class Models(Base):
    __tablename__ = "models"

    model_id: Mapped[int] = mapped_column(
        primary_key=True
    )  # Model ID corresponds to the model's position in the processing pipeline.
    model_name: Mapped[str] = mapped_column(String(30), unique=True)
    model_type: Mapped[str] = mapped_column(String(3))
    file_size: Mapped[int] = mapped_column(Integer())
    model_parameters: Mapped[str] = mapped_column(String(10))
    quantization: Mapped[str] = mapped_column(String(5))
    installed_at: Mapped[str] = mapped_column(String(10))
    model_status: Mapped[int] = mapped_column(Integer())


Base.metadata.create_all(sql_engine)


def add_sql_data(
    table_name: str = None,
    update: bool = False,
    row_id: int = None,
    sql_engine: Engine = sql_engine,
    data: dict = None,
    response: Response = None,
):
    if response is None:
        logging.warning("Response Object not provided!")
        response = Response()

    # makeing Session
    Session = sessionmaker(bind=sql_engine)
    session = Session()

    try:
        if table_name == "projects":

            if update:

                if not row_id or not isinstance(row_id, int):
                    response.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
                    return {
                        "CM": f"Invalid or missing row ID: {row_id}",
                        "UM": "Invalid data. Please provide a valid row ID.",
                    }

                row_to_update = (
                    session.query(Projects)
                    .filter(Projects.project_id == row_id)
                    .first()
                )

                if row_to_update:

                    for key, value in data.items():
                        if hasattr(row_to_update, key):
                            setattr(row_to_update, key, value)

                    session.commit()
                    return {
                        "CM": "Data updated.",
                        "UM": "Data updated successfully!",
                    }

                else:
                    response.status_code = status.HTTP_404_NOT_FOUND
                    return {
                        "CM": f"Unable to locate row: {row_id}",
                        "UM": "Data not found.",
                    }

            else:
                try:
                    new_data = Projects(
                        input_video=data.get("input_video", None),
                        stt_output=data.get("stt_output", None),
                        trans_output=data.get("trans_output", None),
                        tts_output=data.get("tts_output", None),
                        final_output=data.get("final_output", None),
                    )

                    session.add(new_data)
                    session.commit()

                    return {
                        "CM": "Project created successfully.",
                        "UM": "Project created successfully!",
                    }

                except Exception as projectCreationError:
                    response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    logging.error("Unable to created project!")
                    return {
                        "CM": f"Unable to create project: {projectCreationError}",
                        "UM": "An unexpected error occurred while creating the project.",
                    }

        elif table_name == "models":

            if update:
                pass
            else:
                pass

        else:
            response.status_code = status.HTTP_404_NOT_FOUND
            logging.error("Invalid Table Name!")
            return {
                "CM": f"Unable to locate table: '{table_name}'",
                "UM": "Unable to load data.",
            }

    except Exception as mainBodyError:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        logging.error("Unable to perform opration on Data.")
        return {
            "CM": f"Operation failed: {mainBodyError}",
            "UM": "Something went wrong. Please try again later.",
        }


def load_data_from_sql(sql_engine: Engine = sql_engine, response: Response = None):

    if response is None:
        logging.warning("Response Object not provided!")
        response = Response()

    tables = {"projects": None, "models": None}

    try:
        for table_name in tables.keys():
            sql_query = f"SELECT * FROM {table_name}"

            df = pd.read_sql_query(text(sql_query), con=sql_engine)
            tables[table_name] = json.loads(df.to_json(orient="records"))

        logging.info("Load data succesfully!")
        return {
            "CM": "Data loaded successfully.",
            "UM": tables,
        }

    except Exception as e:
        response.status_code
        logging.error("Unable to load data:", e)
        return {
            "CM": f"Unable to load data: {e}",
            "UM": tables,
        }