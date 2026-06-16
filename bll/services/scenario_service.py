from typing import Optional
from dal.repositories import ScenarioRepository

class ScenarioService:
    def __init__(self, scenario_repo: ScenarioRepository):
        self.scenario_repo = scenario_repo

    def get_id_by_title(self, title: str) -> Optional[int]:
        scenario = self.scenario_repo.get_by_title(title)
        if not scenario:
            raise ValueError()(f"Сценарий '{title}' не найден в БД. Проверьте таблицу scenarios.")
        return scenario.scenario_id