from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import Scenario

class ScenarioRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, title: str, description: Optional[str] = None) -> Scenario:
        scenario = Scenario(
            title=title,
            description=description
            )
        self.session.add(scenario)
        self.session.flush()
        return scenario

    def get_by_id(self, scenario_id: int) -> Optional[Scenario]:
        return self.session.get(Scenario, scenario_id)

    def get_by_title(self, title: str) -> Optional[Scenario]:
        stmt = select(Scenario).where(Scenario.title == title)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all(self) -> Sequence[Scenario]:
        stmt = select(Scenario)
        return self.session.execute(stmt).scalars().all()

    def update(self, scenario_id: int, **values) -> None:
        if not values:
            return
        stmt = update(Scenario).where(Scenario.scenario_id == scenario_id).values(**values)
        self.session.execute(stmt)

    def delete(self, scenario_id: int) -> None:
        stmt = delete(Scenario).where(Scenario.scenario_id == scenario_id)
        self.session.execute(stmt)