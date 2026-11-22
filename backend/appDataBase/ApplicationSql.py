# Database librarys
from sqlalchemy import create_engine, String, select, Integer, text, delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.engine import Engine

# Data librarys
import pandas as pd, json

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


class NotFoundError(Exception):
    """Data not found in DataBased"""


class Base(DeclarativeBase):
    pass


class Projects(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[str] = mapped_column(String(20), unique=True)
    processing_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
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
):

    # makeing Session
    Session = sessionmaker(bind=sql_engine)
    session = Session()

    if table_name == "projects":

        if update:

            if not row_id or not isinstance(row_id, int):
                raise ValueError(f"Invalid or missing row ID: {row_id}")

            row_to_update = (
                session.query(Projects).filter(Projects.project_id == row_id).first()
            )

            if row_to_update:

                for key, value in data.items():
                    if hasattr(row_to_update, key):
                        setattr(row_to_update, key, value)

                session.commit()
                return True

            else:
                raise NotFoundError(f"Unable to locate row: {row_id}")

        else:
            new_data = Projects(
                project_name=data.get("project_name", None),
                created_at=data.get("created_at", "No data"),
                input_video=data.get("input_video", None),
                stt_output=data.get("stt_output", None),
                trans_output=data.get("trans_output", None),
                tts_output=data.get("tts_output", None),
                final_output=data.get("final_output", None),
            )

            session.add(new_data)
            session.commit()

            return True

    elif table_name == "models":

        if update:
            pass
        else:
            pass

    else:
        raise NotFoundError(f"Invalid table Name.")


def load_data_from_sql(sql_engine: Engine = sql_engine):

    tables = {"projects": None, "models": None}

    for table_name in tables.keys():
        sql_query = f"SELECT * FROM {table_name}"

        df = pd.read_sql_query(text(sql_query), con=sql_engine)
        tables[table_name] = json.loads(df.to_json(orient="records"))

    logging.info("Load data succesfully!")
    return {
        "CM": "Data loaded successfully.",
        "UM": tables,
    }


def fetch_record(sql_engine: Engine = sql_engine, row_id: int = None):

    Session = sessionmaker(bind=sql_engine)
    session = Session()

    row = session.query(Projects).filter(Projects.project_id == row_id).first()

    if row:
        data = {
            column.name: getattr(row, column.name)
            for column in Projects.__table__.columns
        }

        json.dumps(data, default=str)

        return {"CM": f"Data loaded successfully for id: {row_id}", "UM": data}

    else:
        raise ValueError(f"Data not found for Id: {row_id}")


def remove_record(sql_engine: Engine = sql_engine, row_id: int = None):

    Session = sessionmaker(bind=sql_engine)

    with Session() as session:
        try:
            stmt = delete(Projects).where(Projects.project_id == row_id)
            result = session.execute(stmt)
            session.commit()

            if result.rowcount > 0:
                return True

        except Exception:
            session.rollback()
            raise
