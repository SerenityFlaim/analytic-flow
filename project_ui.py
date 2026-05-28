import streamlit as st
from bll.services.analysis_service import AnalysisService
from bll.scenario_registry import SCENARIO_REGISTRY

SCENARIO_META = {
    1: {"name": "Инвентарный анализ", "icon": "📦", "page": "inventory"},
    2: {"name": "Инвентарный анализ", "icon": "📦", "page": "inventory"}
}

def render_project_ui(an_service: AnalysisService, project_title: str):
    st.title(f"📁 {project_title}")
    st.subheader("Сохранённые сценарии проекта")

    project_id = st.session_state.current_project
    scenarios = an_service.get_project_scenarios(project_id)

    if not scenarios:
        st.info("В этом проекте пока нет сохранённых сценариев. Запустите анализ и сохраните результат.")
        if st.button("Перейти к сценариям", use_container_width=True):
            st.session_state.page = 'hub'
            st.rerun()
        return
    
    if 'confirm_delete_scenario' not in st.session_state:
        st.session_state.confirm_delete_scenario = None

    for sc in scenarios:
        meta = SCENARIO_REGISTRY.get(sc['scenario_id'], {
            "name": "Неизвестный сценарий",
            "icon": "📊",
            "page": "hub",
            "render_config": lambda cfg: st.json(cfg)
        })
        config = sc['config']
        

        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"### {meta['icon']} {meta['name']}")
                st.write(f"**Датасет:** {sc['dataset_name']}")
                st.write(f"**Сохранён** {sc['updated_at'].strftime('%d.%m.%Y %H:%M')}")

                with st.expander("Параметры конфигурации"):
                    meta['render_config'](config)

            with col_actions:
                if st.button(
                    "▶️ Загрузить и запустить",
                    key=f"load_{sc['user_scenario_id']}",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.loaded_config = config
                    st.session_state.loaded_dataset_id = sc['dataset_id']

                    st.session_state.pop('last_results', None)
                    st.session_state.pop('active_config', None)
                    st.session_state.page = meta['page']
                    st.rerun()

                st.write("")

                sc_id = sc['user_scenario_id']
                if st.session_state.confirm_delete_scenario != sc_id:
                    if st.button(
                        "🗑️ Удалить",
                        key=f"del_{sc_id}",
                        use_container_width=True
                    ):
                        st.session_state.confirm_delete_scenario = sc_id
                        st.rerun()
                else:
                    st.warning("Удалить этот сценарий?")
                    if st.button("Да", key=f"del_yes_{sc_id}", use_container_width=True, type="primary"):
                        an_service.delete_user_scenario(sc_id)
                        st.session_state.confirm_delete_scenario = None
                        st.rerun()
                    if st.button("Отмена", key=f"del_no_{sc_id}", use_container_width=True):
                        st.session_state.confirm_delete_scenario = None
                        st.rerun()