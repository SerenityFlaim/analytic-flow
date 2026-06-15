import streamlit as st
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

SCENARIO_REGISTRY = {
    2: {
        "name": "Инвентарный анализ",
        "icon": "📦",
        "page": "inventory",
        "render_config": render_inventory_config,
        "render_dashboard": render_inventory_dashboard,
    },
    3: {
        "name": "RFM-анализ",
        "icon": "👥",
        "page": "rfm",
        "render_config": render_rfm_config,
        "render_dashboard": render_rfm_dashboard,
    },
}