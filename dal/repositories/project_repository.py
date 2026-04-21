from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import Project

class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, title: str, description="") -> Project:
        project = Project(
            user_id = user_id,
            title = title, 
            description = description
        )
        self.session.add(project)
        self.session.flush()
        return project
    
    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.session.get(Project, project_id)
    
    def get_all_by_user(self, user_id: int) -> Sequence[Project]:
        statement = select(Project).where(Project.user_id == user_id)
        return self.session.execute(statement).scalars().all()
    
    def update(self, project_id: int, **values) -> None:
        if not values:
            return
        statement = update(Project).where(Project.project_id == project_id).values(**values)
        self.session.execute(statement)

    def delete(self, project_id: int) -> None:
        statement = delete(Project).where(Project.project_id == project_id)
        self.session.execute(statement)