import streamlit as st
from bll.services.analysis_service import AnalysisService
from bll.scenario_registry import SCENARIO_REGISTRY

def render_report_ui(an_service: AnalysisService):
    user_scenario_id = st.session_state.get('report_scenario_id')

    if user_scenario_id is None:
        st.error("Не указан сценарий для просмотра.")
        if st.button("Вернуться к проекту"):
            st.session_state.page = 'project'
            st.rerun()
        return
    
    report_meta = st.session_state.get('report_meta', {})
    scenario_id = report_meta.get('scenario_id')
    meta = SCENARIO_REGISTRY.get(scenario_id, {
        "name": "Отчёт",
        "icon": "📊",
    })

    st.title(f"{meta['icon']} {meta['name']} — Отчёт")
    st.caption(
        f"Датасет: **{report_meta.get('dataset_name', '—')}** · "
        f"Сохранён: **{report_meta.get('updated_at', '—')}**"
    )

    if st.button("← Вернуться к проекту", use_container_width=False):
        st.session_state.page = 'project'
        st.session_state.pop('report_scenario_id', None)
        st.session_state.pop('report_meta', None)
        st.rerun()

    st.divider()

    try:
        with st.spinner("Загрузка результатов..."):
            results = an_service.get_latest_result(user_scenario_id)
    except ValueError as ex:
        st.warning(str(ex))
        st.info("Результаты для этого сценария не были сохранены. Попробуйте загрузить и запустить его заново.")
        return
    
    if scenario_id in SCENARIO_REGISTRY.keys():
        from ui.inventory_ui import render_inventory_dashboard
        render_inventory_dashboard(results, use_tabs=False)
    else:
        st.json(results.get('summary', {}))