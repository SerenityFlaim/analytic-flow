import pandas as pd
import numpy as np
from .scenario_interface import ScenarioInterface
from typing import Dict, Any

class InventoryScenario(ScenarioInterface):
    def validate_config(self) -> bool:
        required_fields = ['id', 'date', 'volume', 'revenue']
        mapping = self.config.get('mapping', {})
        return all(field in mapping for field in required_fields)
    
    def preprocess(self):
        m = self.config['mapping']

        self.df[m['date']] = pd.to_datetime(self.df[m['date']])
        self.df[m['volume']] = pd.to_numeric(self.df[m['volume']])
        self.df[m['revenue']] = pd.to_numeric(self.df[m['revenue']])

        if self.config.get('cleaning', {}).get('fill_voids') == 'zeros':
            self.df = self.df.fillna(0)

        self.df = self.df.sort_values(by=m['date'])

    def _calculate_abc(self, data: pd.DataFrame) -> pd.DataFrame:
        m = self.config['mapping']

        abc_df = data.groupby(m['id'])[m['revenue']].sum().reset_index()
        abc_df = abc_df.sort_values(by=m['revenue'], ascending=False)

        total_rev = abc_df[m['revenue']].sum()
        abc_df['share'] = abc_df[m['revenue']] / total_rev
        abc_df['cum_share'] = abc_df['share'].cumsum()

        def get_abc(share):
            if share <= 0.50: return 'A'
            if share <= 0.80: return 'B'
            return 'C'
        
        abc_df['abc_category'] = abc_df['cum_share'].apply(get_abc)
        return abc_df[[m['id'], 'abc_category']]
    
    def _calculate_xyz(self, data: pd.DataFrame) -> pd.DataFrame:
        m = self.config['mapping']

        xyz_df = data.groupby(m['id'])[m['volume']].agg(['mean', 'std']).reset_index()
        xyz_df['cv'] = xyz_df['std'] / xyz_df['mean']

        def get_xyz(cv):
            if cv <= 0.10: return 'X'
            if cv <= 0.25: return 'Y'
            return 'Z'
        
        xyz_df['xyz_category'] = xyz_df['cv'].apply(get_xyz)
        return xyz_df[[m['id']], 'xyz_category']
    
    def execute(self) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Неверная конфигурация маппинга")
        
        self.preprocess()

        abc_res = self._calculate_abc(self.df)
        xyz_res = self._calculate_xyz(self.df)

        m = self.config['mapping']
        final_df = pd.merge(abc_res, xyz_res, on=m['id'])
        final_df['final_category'] = final_df['abc_category'] + final_df['xyz_category']

        self.results['analysis_table'] = final_df
        self.results['summary'] = final_df['final_category'].value_counts().to_dict()

        return self.results

