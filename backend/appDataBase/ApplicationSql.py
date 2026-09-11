# Database librarys
from sqlalchemy import create_engine, String, select, Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

# Data librarys
import pandas as pd, json, os

# Directorie librarys
from platformdirs import PlatformDirs
from pathlib import Path

APP_NAME = "com.vishwjeet.lingusync"

dirs = PlatformDirs(appname=APP_NAME, appauthor=False)
app_data_path = Path(dirs.user_data_path)
app_data_path.mkdir(parents=True, exist_ok=True)

db_path = str(app_data_path) + "/lingusync.db"
sql_path = f"sqlite:///{db_path}"

sql_engine = create_engine(sql_path, echo=True)


class Base(DeclarativeBase):
    pass


class Projects(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(primary_key=True)
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
