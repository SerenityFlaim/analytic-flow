import streamlit as st
from database.connection import SessionLocal
from dal.repositories import ( 
    DatasetRepository, UserScenarioRepository, 
    AnalysisResultRepository, ProjectRepository, 
    UserRepository
)
from bll.services.dataset_service import DatasetService
from bll.services.analysis_service import AnalysisService
from bll.services.project_service import ProjectService
from bll.services.auth_service import AuthService
from auth_ui import render_auth_ui

st.set_page_config(page_title="AnalyticFlow", layout="wide")

@st.cache_resource
def get_services():
    session = SessionLocal()

    ds_repo = DatasetRepository(session)
    us_repo = UserScenarioRepository(session)
    res_repo = AnalysisResultRepository(session)
    proj_repo = ProjectRepository(session)
    user_repo = UserRepository(session)

    ds_service = DatasetService(ds_repo)
    an_service = AnalysisService(us_repo, res_repo, ds_repo)
    proj_service = ProjectService(proj_repo)
    auth_service = AuthService(user_repo)

    return ds_service, an_service, proj_service, auth_service

ds_service, an_service, proj_service, auth_service = get_services()

if 'user' not in st.session_state:
    render_auth_ui(auth_service)
    st.stop()

user_id = st.session_state.user['id']
user_name = st.session_state.user['name']

if 'page' not in st.session_state:
    st.session_state.page = 'hub'
if 'current_project' not in st.session_state:
    st.session_state.current_project = None

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

with st.sidebar:
    st.title("AnalyticFlow")
    st.caption("Интерактивный инструмент бизнес-анализа")
    st.divider()

    st.write(f"👤 **{user_name}**")
    if st.button("Выйти", use_container_width=True):
        del st.session_state.user
        st.session_state.page = 'hub'
        st.session_state.current_project = None
        st.rerun()

    st.divider()

    projects = proj_service.get_user_projects(user_id=user_id)
    project_titles = {p.project_id: p.title for p in projects}

    if project_titles:
        selected_proj_id = st.selectbox(
            "Текущий проект",
            options=list(project_titles.keys()),
            format_func=lambda x: project_titles[x]
        )
        st.session_state.current_project = selected_proj_id
    else:
        st.info("У вас нет проектов. Создайте первый!")
        selected_proj_id = None
        st.session_state.current_project = None

    with st.expander("➕ Новый проект"):
        new_proj_title = st.text_input("Название проекта", key="new_proj_title")
        new_proj_desc = st.text_area("Описание (необязательно)", key="new_proj_desc")
        if st.button("Создать проект"):
            if new_proj_title.strip():
                proj_service.create_project(
                    user_id=user_id,
                    title=new_proj_title,
                    description=new_proj_desc
                )
                st.success("Проект создан!")
                st.rerun()
            else:
                st.error("Введите название проекта.")

    st.divider()

    st.write("### Загрузка данных")
    uploaded_file = st.file_uploader("Выбраь CSV/Excel", type=["csv", "xlsx", "xls"])
    if uploaded_file:
        if st.button("Сохранить датасет"):
            with st.spinner("Загрузка..."):
                try:
                    ds_service.upload_dataset(user_id=user_id,
                                            file_bytes=uploaded_file.getvalue(),
                                            filename=uploaded_file.name
                                            )
                    st.success("Файл загружен!")
                    st.rerun()
                except ValueError as ex:
                    st.error(str(ex))


    if st.button("На главную", use_container_width=True):
        navigate_to('hub')

    if selected_proj_id:
        st.info(f"Активный проект: {project_titles.get(selected_proj_id, 'Не выбран')}")



if st.session_state.page == 'hub':
    st.title("Меню сценариев")
    st.subheader("Выберите аналитический сценарий для запуска")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/box.png", width=80)
            st.markdown("### 📦 Инвентарный анализ")
            st.write("Классификация запасов (ABC/XYZ), прогнозирование спроса и рассчёт страхового запаса. Сценарий для оптимизации склада.")
            if st.button("Запустить сценарий", key="btn_inv", use_container_width="True"):
                navigate_to('inventory')
                # if st.session_state.current_project is None:
                #     st.error("Сначала выберите или создайте проект.")
                # else:
                #     navigate_to('inventory')

    with col2:
        with st.container(border=True):
            st.image("https://img.icons8.com/fluency/96/line-chart.png", width=80)
            st.markdown("### 📊 Финансовый скоринг (В разработке)")
            st.write("Анализ маржинальности, поиск точек роста прибыли и факторный анализ отклонений. Сценарий для финансового планирования.")
            st.button("Скоро", disabled=True, use_container_width=True)

elif st.session_state.page == 'inventory':
    from inventory_ui import render_inventory_ui
    render_inventory_ui(ds_service, an_service, user_id)