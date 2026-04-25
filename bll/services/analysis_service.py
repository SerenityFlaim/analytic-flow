import pandas as pd
from typing import Dict, Any
from dal.repositories import UserScenarioRepository, AnalysisResultRepository
from bll.services.dataset_service import DatasetService
from bll.scenario_interface import ScenarioInterface

class AnalysisService:
    def __init__(self, us_repo: UserScenarioRepository, result_repo: AnalysisResultRepository, dataset_service: DatasetService):
        self.us_repo = us_repo
        self.result_repo = result_repo
        self.dataset_service = dataset_service


    def run_analysis(self, strategy: ScenarioInterface) -> Dict[str, Any]:
        try:
            return strategy.execute()
        except Exception as ex:
            raise ValueError(f"Ошибка при выполнении сценария: {str(ex)}")
        
    def save_scenario_settings(self, user_id: int, project_id: int, dataset_id: int, scenario_id: int, config: Dict[str, Any]) -> int:
        user_scenario = self.us_repo.create(
        user_id=user_id, 
        project_id=project_id,
        dataset_id=dataset_id,
        scenario_id=scenario_id,
        config_json=config
        )
        self.us_repo.session.commit()
        return user_scenario.user_scenario_id
    
    def save_analysis_result(self, user_scenario_id: int, raw_results: Dict[str, Any]) -> int:
        processed_results ={}
        for key, value in raw_results.items():
            if isinstance(value, pd.DataFrame):
                processed_results[key] = value.to_dict(orient='records')
            else:
                processed_results[key] = value

        analysis_result_record = self.result_repo.create(
            user_scenario_id=user_scenario_id,
            result_json=processed_results,
            metrics_json=raw_results.get('summary')
        )
        self.result_repo.session.commit()
        return analysis_result_record.results_id
    
    def delete_result(self, results_id: int) -> None:
        self.result_repo.delete(results_id)