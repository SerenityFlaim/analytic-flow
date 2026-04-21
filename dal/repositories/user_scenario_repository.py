from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import UserScenario

class UserScenarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, project_id: int, dataset_id: int, scenario_id: int, config_json: dict) -> UserScenario:
        user_scenario = UserScenario(
            user_id = user_id,
            project_id = project_id, 
            dataset_id = dataset_id, 
            scenario_id = scenario_id,
            config_json = config_json
        )
        self.session.add(user_scenario)
        self.session.flush()
        return user_scenario
    
    def get_by_id(self, user_scenario_id: int) -> Optional[UserScenario]:
        return self.session.get(UserScenario, user_scenario_id)
    
    def get_all_by_project(self, project_id: int) -> Sequence[UserScenario]:
        statement = select(UserScenario).where(UserScenario.project_id == project_id)
        return self.session.execute(statement).scalars().all()
    
    def update(self, user_scenario_id: int, **values) -> None:
        if not values:
            return
        statement = update(UserScenario).where(UserScenario.user_scenario_id == user_scenario_id).values(**values)
        self.session.execute(statement)

    def delete(self, user_scenario_id: int) -> None:
        statement = delete(UserScenario).where(UserScenario.user_scenario_id == user_scenario_id)
        self.session.execute(statement)