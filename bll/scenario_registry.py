import streamlit as st

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

SCENARIO_REGISTRY = {
    1: {
        "name": "Инвентарный анализ",
        "icon": "📦",
        "page": "inventory",
        "render_config": render_inventory_config,
    },
    2: {
        "name": "Инвентарный анализ",
        "icon": "📦",
        "page": "inventory",
        "render_config": render_inventory_config,
    }
}