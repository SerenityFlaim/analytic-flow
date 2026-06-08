import pandas as pd
from typing import Dict, Any, List
from dal.repositories import UserScenarioRepository, AnalysisResultRepository, DatasetRepository
from bll.scenario_interface import ScenarioInterface

class AnalysisService:
    def __init__(self, us_repo: UserScenarioRepository, result_repo: AnalysisResultRepository, dataset_repo: DatasetRepository):
        self.us_repo = us_repo
        self.result_repo = result_repo
        self.dataset_repo = dataset_repo


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
    
    def get_project_scenarios(self, project_id: int) -> List[Dict[str, Any]]:
        user_scenarios = self.us_repo.get_all_by_project(project_id)
        result = []
        for us in user_scenarios:
            dataset = self.dataset_repo.get_by_id(us.dataset_id)
            result.append({
                'user_scenario_id': us.user_scenario_id,
                'scenario_id': us.scenario_id,
                'dataset_id': us.dataset_id,
                'dataset_name': dataset.file_name if dataset else '(Файл удалён)',
                'config': us.config_json,
                'updated_at': us.updated_at,
            })

        result.sort(key=lambda x: x['updated_at'], reverse=True)
        return result
    
    def delete_user_scenario(self, user_scenario_id: int) -> None:
        results = self.result_repo.get_all_by_user_scenario_id(user_scenario_id)
        for r in results:
            self.result_repo.delete(r.results_id)
        self.us_repo.delete(user_scenario_id)
        self.us_repo.session.commit()

    
    def delete_result(self, results_id: int) -> None:
        self.result_repo.delete(results_id)

    def get_latest_result(self, user_scenario_id: int) -> pd.DataFrame:
        results = self.result_repo.get_all_by_user_scenario_id(user_scenario_id)
        if not results:
            raise ValueError("Сохранённых результатов для этого сценария не найдено.")
        latest = max(results, key=lambda r: r.created_at)
        raw = latest.result_json
        restored = {}
        for key, value in raw.items():
            if isinstance(value, list):
                restored[key] = pd.DataFrame(value)
            else:
                restored[key] = value
        return restored