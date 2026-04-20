import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, JSON, DateTime, Identity
from sqlalchemy.dialects.postgresql import JSONB, TEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    type_annotation_map = {
        dict: JSONB
    }

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    email: Mapped[int] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[int] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    surname: Mapped[str] = mapped_column(String(512))
    patronymic: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime.datetime] = mapped_column(server_default="now()")


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(TEXT)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default="now()")

class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(512))
    file_name: Mapped[str] = mapped_column(String(255))

class Scenario(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(TEXT)

class UserScenario(Base):
    __tablename__ = "user_scenarios"

    user_scenario_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id", ondelete="CASCADE"))
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.dataset_id"))
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=False)
    config_json: Mapped[dict] = mapped_column()
    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default="now()",
        onupdate=datetime.datetime.now
    )

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    results_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    user_scenario_id: Mapped[int] = mapped_column(ForeignKey("user_scenarios.user_scenario_id", ondelete="CASCADE"))
    result_json: Mapped[dict] = mapped_column()
    metrics_json: Mapped[dict] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(server_default="now()")
