import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from .scenario_interface import ScenarioInterface

class RFMScenario(ScenarioInterface):
    def validate_config(self) -> bool:
        required_mapping = ['client_id', 'date', 'amount']
        mapping = self.config.get('mapping', {})
        segments = self.config.get('segments', [])
        ltv = self.config.get('ltv', {})

        mapping_ok =  all(field in mapping for field in required_mapping)
        segments_ok = len(segments) > 0 and all('name' in s for s in segments)
        ltv_ok = 'horizon_months' in ltv and 'margin_pct' in ltv

        return mapping_ok and segments_ok and ltv_ok
    
    def preprocess(self):
        m = self.config['mapping']
        filters = self.config.get('filters', {})

        self.df[m['date']] = pd.to_datetime(self.df[m['date']])
        self.df[m['amount']] = pd.to_numeric(self.df[m['amount']])

        self.df = self.df.dropna(subset=[m['date'], m['amount']])

        if filters.get('date_from'):
            self.df = self.df[self.df[m['date']] >= pd.to_datetime(filters['date_from'])]
        if filters.get('date_to'):
            self.df = self.df[self.df[m['date']] <= pd.to_datetime(filters['date_to'])]

        if filters.get('min_monetary'):
            client_totals = self.df.groupby(m['client_id'])[m['amount']].sum()
            valid_clients = client_totals[client_totals >= filters['min_monetary']].index
            self.df = self.df[self.df[m['client_id']].isin(valid_clients)]

        self.df = self.df.sort_values(by=m['date'])

    def _calculate_rfm(self) -> pd.DataFrame:
        m = self.config['mapping']

        today = datetime.now()

        rfm = self.df.groupby(m['client_id']).agg(
            last_purchase=(m['date'], 'max'),
            frequency=(m['date'], 'count'),
            monetary=(m['amount'], 'sum')
        ).reset_index()

        rfm.columns = ['client_id', 'last_purchase', 'frequency', 'monetary']
        rfm['recency_days'] = (today - rfm['last_purchase']).dt.days

        first_date = self.df[m['date']].min()
        last_date = self.df[m['date']].max()
        self.observation_months = max(
            round((last_date - first_date).days / 30), 1
        )

        return rfm[['client_id', 'recency_days', 'frequency', 'monetary', 'last_purchase']]
    
    def _add_percentiles(self, rfm: pd.DataFrame) -> pd.DataFrame:
        rfm['r_percentile'] = (
            rfm['recency_days'].rank(pct=True, ascending=False) * 100
        ).round(1)

        rfm['f_percentile'] = (
            rfm['frequency'].rank(pct=True, ascending=True) * 100
        ).round(1)
        rfm['m_percentile'] = (
            rfm['monetary'].rank(pct=True, ascending=True) * 100
        ).round(1)

        return rfm
    
    def _assign_segments(self, rfm: pd.DataFrame) -> pd.DataFrame:
        segments = self.config['segments']

        def get_segment(row) -> str:
            for seg in segments:
                r_ok = seg['r_range'][0] <= row['r_percentile'] <= seg['r_range'][1]
                f_ok = seg['f_range'][0] <= row['f_percentile'] <= seg['f_range'][1]
                m_ok = seg['m_range'][0] <= row['m_percentile'] <= seg['m_range'][1]
                if r_ok and f_ok and m_ok:
                    return seg['name']
            return 'Прочие'
        
        rfm['segment'] = rfm.apply(get_segment, axis=1)
        return rfm
    
    def _calculate_ltv(self, rfm: pd.DataFrame) -> pd.DataFrame:
        ltv_cfg = self.config['ltv']
        horizon = ltv_cfg['horizon_months']
        margin = ltv_cfg['margin_pct'] / 100

        monthly_frequency = rfm['frequency'] / self.observation_months

        avg_check = rfm['monetary'] / rfm['frequency'].replace(0, 1)
        rfm['ltv_forecast'] = (
            avg_check * monthly_frequency * horizon * margin
        ).round(2)

        return rfm
    
    def _build_rfm_table(self, rfm: pd.DataFrame) -> pd.DataFrame:
        actions = self.config.get('actions', {})

        rfm['action'] = rfm['segment'].map(
            lambda s: actions.get(s, {}).get('action', '—')
        )
        rfm['comment'] = rfm['segment'].map(
            lambda s: actions.get(s, {}).get('comment', '')
        )

        return rfm
    
    def _build_segment_summary(self, rfm: pd.DataFrame) -> List[Dict]:
        actions = self.config.get('actions', {})
        summary = []

        all_segments = [s['name'] for s in self.config['segments']] + ['Прочие']

        for seg_name in all_segments:
            seg_df = rfm[rfm['segment'] == seg_name]
            if seg_df.empty:
                continue
            summary.append({
                'segment': seg_name,
                'count': len(seg_df),
                'avg_monetary': round(seg_df['monetary'].mean(), 2),
                'avg_ltv': round(seg_df['ltv_forecast'].mean(), 2),
                'total_ltv': round(seg_df['ltv_forecast'].sum(), 2),
                'action': actions.get(seg_name, {}).get('action', '—')
            })

        return summary
    
    def execute(self) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Неверная конфигурация: проверьте маппинг, сегменты и LTV-параметры")
        
        self.preprocess()

        rfm = self._calculate_rfm()
        rfm = self._add_percentiles(rfm)
        rfm = self._assign_segments(rfm)
        rfm = self._calculate_ltv(rfm)
        rfm = self._build_rfm_table(rfm)

        segment_summary = self._build_segment_summary(rfm)

        self.results['rfm_table'] = rfm.drop(columns=['last_purchase'])
        self.results['segment_summary'] = pd.DataFrame(segment_summary)
        self.results['summary'] = {
            'total_clients': len(rfm),
            'total_revenue': round(rfm['monetary'].sum(), 2),
            'total_ltv_forecast': round(rfm['ltv_forecast'].sum(), 2),
            'analysis_period_months': self.observation_months,
            'segments_count': len(self.config['segments']),
            'segment_distribution': rfm['segment'].value_counts().to_dict()
        }

        return self.results