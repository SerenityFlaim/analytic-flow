import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from .scenario_interface import ScenarioInterface

class FinancialScoringScenario(ScenarioInterface):
    def validate_config(self) -> bool:
        required_mapping = ['debtor_id', 'invoice_date', 'due_date', 'fact_date', 'amount']
        mapping = self.config.get('mapping', {})
        weights = self.config.get('weights', {})
        risk_classes = self.config.get('risk_classes', {})
        pd_by_class = self.config.get('pd_by_class', {})
        business_params = self.config.get('business_params', {})

        mapping_ok = all(field in mapping for field in required_mapping)

        weights_ok = (
            all(k in weights for k in ('dpd', 'concentration', 'discipline'))
            and abs(sum(weights.values()) - 1.0) < 0.01
        )

        risk_classes_ok = len(risk_classes) > 0
        pd_ok = all(cls in pd_by_class for cls in risk_classes.keys())
        business_ok = 'margin_pct' in business_params and 'credit_horizon_days' in business_params
        return mapping_ok and weights_ok and risk_classes_ok and pd_ok and business_ok
    
    def preprocess(self):
        m = self.config['mapping']

        self.df[m['invoice_date']] = pd.to_datetime(self.df[m['invoice_date']], errors='coerce')
        self.df[m['due_date']] = pd.to_datetime(self.df[m['due_date']], errors='coerce')
        self.df[m['fact_date']] = pd.to_datetime(self.df[m['fact_date']], errors='coerce')
        self.df[m['amount']] = pd.to_numeric(self.df[m['amount']], errors='coerce')

        self.df = self.df.dropna(subset=[m['invoice_date'], m['due_date'], m['amount']])

        report_date_str = self.config.get('report_date')
        self.report_date = pd.to_datetime(report_date_str) if report_date_str else pd.Timestamp(datetime.now())

        self.df = self.df[self.df[m['invoice_date']] <= self.report_date]
        self.df = self.df.sort_values(by=m['invoice_date'])

    def _calculate_dpd(self, row, m) -> float:
        if pd.isna(row[m['fact_date']]):
            return np.nan
        delta = (row[m['fact_date']] - row[m['due_date']]).days
        return max(delta, 0)
    
    def _build_debtor_profile(self) -> pd.DataFrame:
        m = self.config['mapping']

        self.df['is_paid'] = self.df[m['fact_date']].notna()
        self.df['dpd'] = self.df.apply(lambda r: self._calculate_dpd(r, m), axis=1)
        self.df['is_violation'] = self.df['dpd'] > 0

        profiles = []
        total_debt_all = self.df.loc[~self.df['is_paid'], m['amount']].sum()
        
        for debtor_id, group in self.df.groupby(m['debtor_id']):
            total_invoiced = group[m['amount']].sum()

            paid = group[group['is_paid']]
            unpaid = group[~group['is_paid']]

            current_debt = unpaid[m['amount']].sum()
            paid_amount = paid[m['amount']].sum()

            dpd_avg = paid['dpd'].mean() if not paid.empty else 0.0
            dpd_avg = 0.0 if pd.isna(dpd_avg) else dpd_avg

            concentration_pct = (
                round(current_debt / total_debt_all * 100, 2) if total_debt_all > 0 else 0.0
            )
            collection_rate = (
                round(paid_amount / total_invoiced * 100, 2) if total_invoiced > 0 else 0.0
            )
            violation_rate = (
                round(paid['is_violation'].sum() / len(paid) * 100, 2) if len(paid) > 0 else 0.0
            )

            profiles.append({
                'debtor_id': debtor_id,
                'total_invoiced': round(total_invoiced, 2),
                'current_debt': round(current_debt, 2),
                'dpd_avg': round(dpd_avg, 2),
                'concentration_pct': concentration_pct,
                'collection_rate': collection_rate,
                'violation_rate': violation_rate,
            })

        return pd.DataFrame(profiles)
    
    def _calculate_scores(self, profile: pd.DataFrame) -> pd.DataFrame:
        weights = self.config['weights']

        max_dpd = profile['dpd_avg'].max()
        max_conc = profile['concentration_pct'].max()

        if max_dpd > 0:
            profile['dpd_score'] = (100 - (profile['dpd_avg'] / max_dpd * 100)).clip(0, 100)
        else:
            profile['dpd_score'] = 100.0

        if max_conc > 0:
            profile['concentration_score'] = (100 - (profile['concentration_pct'] / max_conc * 100)).clip(0, 100)
        else:
            profile['concentration_score'] = 100.0

        profile['discipline_score'] = (100 - profile['violation_rate']).clip(0, 100)

        profile['credit_score'] = (
            profile['dpd_score'] * weights['dpd']
            + profile['concentration_score'] * weights['concentration']
            + profile['discipline_score'] * weights['discipline']
        ).round(2)

        return profile
    
    def _assign_risk_class(self, profile: pd.DataFrame) -> pd.DataFrame:
        risk_classes = self.config['risk_classes']

        def get_class(score: float) -> str:
            for cls_name, cls_def in risk_classes.items():
                if cls_def['min_score'] <= score <= cls_def['max_score']:
                    return cls_name
            return list(risk_classes.keys())[-1]
        
        profile['risk_class'] = profile['credit_score'].apply(get_class)
        return profile
    
    def _calculate_expected_loss_and_limits(self, profile: pd.DataFrame) -> pd.DataFrame:
        pd_by_class = self.config['pd_by_class']
        risk_classes = self.config['risk_classes']
        business = self.config['business_params']
        margin = business['margin_pct'] / 100

        profile['pd'] = profile['risk_class'].map(pd_by_class)
        profile['expected_loss'] = (profile['current_debt'] * profile['pd']).round(2)

        def calc_limit(row) -> float:
            pd_val = row['pd']
            if pd_val <= 0:
                return float('inf')
            avg_invoice = row['total_invoiced'] / max(row.get('_invoice_count', 1), 1)
            limit = (margin / pd_val) * avg_invoice
            return round(max(limit, 0), 2)
        
        m = self.config['mapping']
        invoice_counts = self.df.groupby(m['debtor_id']).size().rename('_invoice_count')
        profile = profile.merge(invoice_counts, left_on='debtor_id', right_index=True, how='left')

        profile['credit_limit'] = profile.apply(calc_limit, axis=1)
        profile['strategy'] = profile['risk_class'].map(
            lambda c: risk_classes.get(c, {}).get('strategy', '—')
        )

        profile = profile.drop(columns=['_invoice_count'])
        return profile
    
    def _build_risk_summary(self, profile: pd.DataFrame) -> pd.DataFrame:
        summary = profile.groupby('risk_class').agg(
            count=('debtor_id', 'count'),
            total_debt=('current_debt', 'sum'),
            total_expected_loss=('expected_loss', 'sum'),
            avg_score=('credit_score', 'mean')
        ).reset_index()

        summary['total_debt'] = summary['total_debt'].round(2)
        summary['total_expected_loss'] = summary['total_expected_loss'].round(2)
        summary['avg_score'] = summary['avg_score'].round(2)

        order = ['A', 'B', 'C', 'D']
        summary['_sort'] = summary['risk_class'].apply(
            lambda c: order.index(c) if c in order else len(order)
        )
        summary = summary.sort_values('_sort').drop(columns=['_sort']).reset_index(drop=True)

        return summary
    
    def execute(self) -> Dict[str, Any]:
        if not self.validate_config():
            raise ValueError("Неверная конфигурация: проверьте маппинг, веса (сумма=1.0), классы риска и PD")

        self.preprocess()

        profile = self._build_debtor_profile()
        if profile.empty:
            raise ValueError("После обработки данных не осталось контрагентов для анализа")

        profile = self._calculate_scores(profile)
        profile = self._assign_risk_class(profile)
        profile = self._calculate_expected_loss_and_limits(profile)

        risk_summary = self._build_risk_summary(profile)

        self.results['debtor_profile'] = profile
        self.results['risk_summary'] = risk_summary
        self.results['summary'] = {
            'total_debtors': len(profile),
            'total_invoiced': round(profile['total_invoiced'].sum(), 2),
            'total_current_debt': round(profile['current_debt'].sum(), 2),
            'total_expected_loss': round(profile['expected_loss'].sum(), 2),
            'risk_distribution': profile['risk_class'].value_counts().to_dict(),
            'avg_credit_score': round(profile['credit_score'].mean(), 2)
        }

        return self.results