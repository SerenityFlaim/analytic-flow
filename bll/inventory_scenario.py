import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
# from scenario_interface import ScenarioInterface
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
            if share <= 0.80: return 'A'
            if share <= 0.95: return 'B'
            return 'C'
        
        abc_df['abc_category'] = abc_df['cum_share'].apply(get_abc)
        return abc_df[[m['id'], 'abc_category']]
    
    
    def _calculate_xyz(self, data: pd.DataFrame) -> pd.DataFrame:
        m = self.config['mapping']

        xyz_df = data.groupby(m['id'])[m['volume']].agg(['mean', 'std']).reset_index()
        xyz_df['cv'] = xyz_df['std'] / xyz_df['mean'] #.fillna(0)

        def get_xyz(cv):
            if cv <= 0.10: return 'X'
            if cv <= 0.25: return 'Y'
            return 'Z'
        
        xyz_df['xyz_category'] = xyz_df['cv'].apply(get_xyz)
        return xyz_df[[m['id'], 'xyz_category']]
    
    
    def _get_forecast(self, series: pd.Series, method: str) -> float:
        if len(series) < 2:
            return series.iloc[-1] if not series.empty else 0
        
        try:
            if method == 'holt':
                model = ExponentialSmoothing(series, trend='add').fit()
                return max(0, model.forecast(1).iloc[0])
            elif method == 'sma':
                return series.tail(3).mean()
            else:
                return series.iloc[-1]
        except:
            return series.iloc[-1]
        
        
    def _calculate_safety_stock(self, series: pd.Series) -> float:
        params = self.config.get('params', {})
        z = params.get('z_score', 1.65)
        lt = params.get('lead_time', 7)
        return z * series.std() * np.sqrt(lt)
    
    
    def execute(self) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Неверная конфигурация маппинга")
        
        self.preprocess()

        abc_res = self._calculate_abc(self.df)
        xyz_res = self._calculate_xyz(self.df)

        m = self.config['mapping']
        analysis_df = pd.merge(abc_res, xyz_res, on=m['id'])
        analysis_df['final_category'] = analysis_df['abc_category'] + analysis_df['xyz_category']

        ts_data = self.df.set_index(m['date']).groupby(m['id'])[m['volume']].resample('ME').sum().reset_index()

        methods_config = self.config.get('methods', {'A': 'holt', 'B': 'sma', 'C': 'naive'})

        report_data = []
        for _, row in analysis_df.iterrows():
            p_id = row[m['id']]
            abc_cat = row['abc_category']

            p_series = ts_data[ts_data[m['id']] == p_id][m['volume']]
            method = methods_config.get(abc_cat, 'naive')
            forecast = self._get_forecast(p_series, method)
            ss = self._calculate_safety_stock(p_series)

            report_data.append({
                'item_id': p_id,
                'category': row['final_category'],
                'forecast': round(forecast, 2),
                'safety_stock': round(ss, 2),
                'total_need': round(forecast + ss, 2)
            })


        self.results['analysis_table'] = analysis_df
        self.results['forecast_report'] = pd.DataFrame(report_data)
        self.results['summary'] = analysis_df['final_category'].value_counts().to_dict()

        return self.results