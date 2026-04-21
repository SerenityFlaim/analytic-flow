from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import AnalysisResult

class AnalysisResultRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_scenario_id: int, result_json: dict, metrics_json: Optional[dict] = None) -> AnalysisResult:
        analysis_result = AnalysisResult(
            user_scenario_id = user_scenario_id,
            result_json = result_json,
            metrics_json = metrics_json
        )
        self.session.add(analysis_result)
        self.session.flush()
        return analysis_result
    
    def get_by_id(self, results_id: int) -> Optional[AnalysisResult]:
        return self.session.get(AnalysisResult, results_id)
    
    def get_all_by_user_scenario_id(self, user_scenario_id: int) -> Sequence[AnalysisResult]:
        statement = select(AnalysisResult).where(AnalysisResult.user_scenario_id == user_scenario_id)
        return self.session.execute(statement).scalars().all()
    
    def update(self, results_id: int, **values) -> None:
        if not values:
            return
        statement = update(AnalysisResult).where(AnalysisResult.results_id == results_id).values(**values)
        self.session.execute(statement)

    def delete(self, results_id: int) -> None:
        statement = delete(AnalysisResult).where(AnalysisResult.results_id == results_id)
        self.session.execute(statement)