import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from .scenario_interface import ScenarioInterface
from typing import Dict, Any

class InventoryScenario(ScenarioInterface):

    def validate_config(self) -> bool:
        required_fields = ['id', 'date', 'volume', 'revenue']
        mapping = self.config.get('mapping', {})
        ss_params = self.config.get('ss_params', {})
        return all(field in mapping for field in required_fields) and 'lead_time' in ss_params
    
    
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

        a_threshold = self.config.get('abc_threshold', 80) / 100

        abc_df = data.groupby(m['id'])[m['revenue']].sum().reset_index()
        abc_df = abc_df.sort_values(by=m['revenue'], ascending=False)
        total_rev = abc_df[m['revenue']].sum()
        abc_df['cum_share'] = abc_df[m['revenue']].cumsum() / total_rev

        b_threshold = a_threshold + 0.15

        def get_abc(share):
            if share <= a_threshold: return 'A'
            if share <= b_threshold: return 'B'
            return 'C'
        
        abc_df['abc_category'] = abc_df['cum_share'].apply(get_abc)
        return abc_df[[m['id'], 'abc_category', m['revenue']]]
    
    
    def _calculate_xyz(self, data: pd.DataFrame) -> pd.DataFrame:
        m = self.config['mapping']

        ts = data.set_index(m['date']).groupby(m['id'])[m['volume']].resample('ME').sum().reset_index()
        xyz_df = ts.groupby(m['id'])[m['volume']].agg(['mean', 'std']).reset_index()
        xyz_df['xyz_cv'] = (xyz_df['std'] / xyz_df['mean']).replace([np.inf, -np.inf], np.nan).fillna(1.0) #.fillna(0)

        def get_xyz(cv):
            if cv <= 0.10: return 'X'
            if cv <= 0.25: return 'Y'
            return 'Z'
        
        xyz_df['xyz_category'] = xyz_df['xyz_cv'].apply(get_xyz).fillna('Z')
        return xyz_df[[m['id'], 'xyz_category', 'xyz_cv']]
    
    
    def _get_forecast(self, series: pd.Series, method: str) -> float:
        if len(series) < 3 or method == 'naive':
            return series.iloc[-1] if not series.empty else 0
        
        try:
            if method == 'holt':
                model = ExponentialSmoothing(series, trend='add', seasonal=None).fit()
                return max(0, model.forecast(1).iloc[0])
            elif method == 'sma':
                return series.tail(3).mean()
            else:
                return series.iloc[-1]
        except Exception as ex:
            print(f"Forecast error for method={method}: {ex}")
            return series.iloc[-1]
        
        
    def _calculate_safety_stock(self, series: pd.Series, z_score: float, lead_time: float) -> float:
        sigma = series.std()
        if pd.isna(sigma) or sigma == 0:
            return 0.0
        ss = z_score * sigma * np.sqrt(lead_time)
        return round(ss, 2)
    
    
    def execute(self) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Неверная конфигурация маппинга")
        

        m = self.config['mapping']
        ss_p = self.config.get('ss_params', {'z_score': 1.65, 'lead_time': 1.0})
        self.preprocess()

        abc_res = self._calculate_abc(self.df)
        xyz_res = self._calculate_xyz(self.df)

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
            ss = self._calculate_safety_stock(p_series, ss_p['z_score'], ss_p['lead_time'])

            report_data.append({
                'item_id': p_id,
                'category': row['final_category'],
                'forecast': round(forecast, 2),
                'safety_stock': ss,
                'total_need': round(forecast + ss, 2)
            })


        self.results['analysis_table'] = analysis_df
        self.results['forecast_report'] = pd.DataFrame(report_data)
        self.results['summary'] = {
            'total_items': len(analysis_df),
            'abc_counts': abc_res['abc_category'].value_counts().to_dict(),
            'xyz_counts': xyz_res['xyz_category'].value_counts().to_dict(),
            'final_categories': analysis_df['final_category'].value_counts().to_dict()
        }

        return self.results