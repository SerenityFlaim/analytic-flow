from typing import Optional, Sequence
from dal.repositories import ProjectRepository
from dal import Project

class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo = project_repo

    def create_project(self, user_id: int, title: str, description: str = "") -> Project:
        if not title.strip():
            raise ValueError("Название проекта не может быть пустым.")
        return self.project_repo.create(user_id, title, description)
    
    def get_user_projects(self, user_id: int) -> Sequence[Project]:
        return self.project_repo.get_all_by_user(user_id)
    
    def get_project_details(self, project_id: int) -> Optional[Project]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError("Проект не найден.")
        return project
    
    def update_project(self, project_id: int, title: str = None, description: str = None):
        update_data = {}
        if title is not None:
            if not title.strip():
                raise ValueError("Название проекта не может быть пустым.")
            update_data['title'] = title
        if description is not None:
            update_data['description'] = description

        self.project_repo.update(project_id, **update_data)

    def delete_project(self, project_id: int):
        self.project_repo.delete(project_id)