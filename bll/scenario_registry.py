import streamlit as st
from typing import Dict, Any, Optional
from ui.inventory_ui import render_inventory_dashboard
from ui.rfm_ui import render_rfm_dashboard

def render_inventory_config(config: dict):
    mapping = config.get('mapping', {})
    methods = config.get('methods', {})
    ss = config.get('ss_params', {})
    cleaning = config.get('cleaning', {})
    st.write(f"- **Колонка ID:** `{mapping.get('id', '—')}`")
    st.write(f"- **Колонка даты:** `{mapping.get('date', '—')}`")
    st.write(f"- **Колонка объёма:** `{mapping.get('volume', '—')}`")
    st.write(f"- **Колонка выручки:** `{mapping.get('revenue', '—')}`")
    st.write(f"- **Методы прогноза:** `A = {methods.get('A')}`, `B = {methods.get('B')}` , `C = {methods.get('C')}`")
    st.write(f"- **Lead Time:** {ss.get('lead_time', '—')} мес.")
    st.write(f"- **Z-score:** {ss.get('z_score', '—')}")
    st.write(f"- **Порог A:** {config.get('abc_threshold', 80)}%")
    st.write(f"- **Заполнение:** `{cleaning.get('fill_voids', '—')}`")

def render_rfm_config(config: dict):
    mapping = config.get('mapping', {})
    ltv = config.get('ltv', {})
    segments = config.get('segments', [])
    filters = config.get('filters', {})
    st.write(f"- **Колонка клиента:** `{mapping.get('client_id', '—')}`")
    st.write(f"- **Колонка даты:** `{mapping.get('date', '—')}`")
    st.write(f"- **Колонка суммы:** `{mapping.get('amount', '—')}`")
    st.write(f"- **Период:** {filters.get('date_from', '—')} — {filters.get('date_to', '—')}")
    st.write(f"- **Мин. чек:** {filters.get('min_monetary', 0)} ₽")
    st.write(f"- **Горизонт LTV:** {ltv.get('horizon_months', '—')} мес.")
    st.write(f"- **Маржинальность:** {ltv.get('margin_pct', '—')}%")
    st.write(f"- **Сегментов:** {len(segments)}: {', '.join(s['name'] for s in segments)}")

_SCENARIO_DEFINITIONS: list[tuple[str, Dict[str, Any]]] = [
    ("Инвентарный анализ", {
        "name": "Инвентарный анализ",
        "icon": "📦",
        "page": "inventory",
        "render_config": render_inventory_config,
        "render_dashboard": render_inventory_dashboard,
    }),
    ("RFM-анализ", {
        "name": "RFM-анализ",
        "icon": "👥",
        "page": "rfm",
        "render_config": render_rfm_config,
        "render_dashboard": render_rfm_dashboard,
    }),
]

class ScenarioRegistry:
    def __init__(self):
        self._registry: Dict[int, Dict[str, Any]] = {}

    def build(self, scenario_service) -> None:
        self._registry = {}
        for title, meta in _SCENARIO_DEFINITIONS:
            try:
                scenario_id = scenario_service.get_id_by_title(title)
                self._registry[scenario_id] = meta
            except ValueError as ex:
                print(f"⚠️ ScenarioRegistry.build: {ex}")

    def get(self, scenario_id: int, default=None) -> Optional[Dict[str, Any]]:
        return self._registry.get(scenario_id, default)
    
    def get_id_by_page(self, page: str) -> Optional[int]:
        for sid, meta in self._registry.items():
            if meta['page'] == page:
                return sid
        return None
        
    def keys(self):
        return self._registry.keys()
    
    def items(self):
        return self._registry.items()
    
    def __contains__(self, item):
        return item in self._registry
    
registry = ScenarioRegistry()