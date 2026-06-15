import streamlit as st
import pandas as pd
import plotly.express as px
from bll.inventory_scenario import InventoryScenario
from utils.dt_util import _col_index
    
def _render_abc_chart(res: dict):
    fig_abc = px.pie(
        res['analysis_table'], names='abc_category', 
        title="Распределение позиций по выручке (ABC)", hole=0.6)
    st.plotly_chart(fig_abc, use_container_width=True)

def _render_forecast(res: dict):
    st.write("#### Детализация прогноза")
    st.dataframe(res['forecast_report'], use_container_width=True)
    top_item = res['forecast_report'].iloc[0]['item_id']
    st.info(f"Рекомендация для {top_item}: Страховой запас - {res['forecast_report'].iloc[0]['safety_stock']} ед.")

def _render_table(res: dict):
    st.dataframe(res['analysis_table'], use_container_width=True)

def _render_matrix(res: dict):
    st.subheader("Тепловая карта распределения SKU")
    matrix_data = res['analysis_table'].groupby(
        ['abc_category', 'xyz_category']
    ).size().reset_index(name='count')
    pivot_matrix = matrix_data.pivot(
        index='abc_category', columns='xyz_category', values='count'
    ).fillna(0)
    
    # Сортировка (для красоты)
    pivot_matrix = pivot_matrix.reindex(index=['A', 'B', 'C'], columns=['X', 'Y', 'Z'])
    
    fig_heatmap = px.imshow(
        pivot_matrix,
        text_auto=True,
        aspect="auto",
        color_continuous_scale='RdYlGn_r',
        labels=dict(x="XYZ (Стабильность)", y="ABC (Важность)", color="Кол-во SKU")
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

def render_inventory_dashboard(res: dict, use_tabs: bool = True):
    if use_tabs:
        tab1, tab2, tab3, tab4 = st.tabs([
            "Структура групп", "Прогноз и спрос",
            "Итоговая таблица", "Матрица ABC-XYZ"
        ])
        with tab1:
            _render_abc_chart(res)
        with tab2:
            _render_forecast(res)
        with tab3:
            _render_table(res)
        with tab4:
            _render_matrix(res)

    else:
        st.subheader("Структура групп")
        _render_abc_chart(res)
        st.divider()
        st.subheader("Прогноз и спрос")
        _render_forecast(res)
        st.divider()
        st.subheader("Итоговая таблица")
        _render_table(res)
        st.divider()
        st.subheader("Матрица ABC-XYZ")
        _render_matrix(res)
        st.divider()


def render_inventory_ui(ds_service, an_service, user_id: int):
    st.title("📦 Настройка инвентарного анализа")

    lc = st.session_state.get('loaded_config')
    lc_mapping = lc.get('mapping', {}) if lc else {}
    lc_methods = lc.get('methods', {}) if lc else {}
    lc_ss = lc.get('ss_params', {}) if lc else {}
    lc_cleaning = lc.get('cleaning', {}) if lc else {}
    loaded_dataset_id = st.session_state.get('loaded_dataset_id')

    if lc:
        st.info("✅ Загружен сохранённый сценарий. Параметры предзаполнены — вы можете их изменить перед запуском.")

    st.subheader("1. Подготовка данных")
    datasets = ds_service.get_user_datasets(user_id=user_id)
    ds_options = {d.dataset_id: d.file_name for d in datasets}

    ds_ids = list(ds_options.keys())
    default_ds_index = ds_ids.index(loaded_dataset_id) if (loaded_dataset_id and loaded_dataset_id in ds_ids) else 0

    selected_ds_id = st.selectbox(
        "Выберите датасет для анализа",
        options=ds_ids,
        format_func=lambda x: ds_options[x],
        index=default_ds_index
    )

    df = ds_service.get_dataframe(selected_ds_id)
    cols = df.columns.tolist()

    st.info("Укажите, какие столбцы соответствуют требуемым параметрам")
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        m_id = st.selectbox("ID товара / SKU", cols, index=_col_index(cols, lc_mapping.get('id', cols[0])))
    with c2: 
        m_date = st.selectbox("Дата транзакции", cols, index=_col_index(cols, lc_mapping.get('date', cols[0])))
    with c3: 
        m_vol = st.selectbox("Количество (Объём)", cols, index=_col_index(cols, lc_mapping.get('volume', cols[0])))
    with c4: 
        m_rev = st.selectbox("Выручка (Сумма)", cols, index=_col_index(cols, lc_mapping.get('revenue', cols[0])))

    mapping = {"id": m_id, "date": m_date, "volume": m_vol, "revenue": m_rev}

    st.divider()

    st.subheader("2. Параметры расчета")
    col_ss1, col_ss2 = st.columns(2)

    z_mapping = {0.80: 0.84, 0.85: 1.04, 0.90: 1.28, 0.95: 1.65, 0.99: 2.33}
    z_reverse = {v: k for k, v in z_mapping.items()}
    sl_options = [0.80, 0.85, 0.90, 0.95, 0.99]

    default_z = lc_ss.get('z_score', 1.65)
    default_sl = z_reverse.get(default_z, 0.95)
    
    with col_ss1:
        st.write("**Страховой запас (Safety Stock)**")
        lead_time = st.number_input(
            "Lead Time (Время поставки, мес.)",
            min_value=0.1,
            value=float(lc_ss.get('lead_time', 1.0)),
            step=0.1
        )
        service_level = st.select_slider(
            "Уровень сервиса",
            options=sl_options,
            value=default_sl,
            help="Влияет на коэффициент Z"
        )
        z_score = z_mapping[service_level]

    method_options = ["holt", "sma", "naive"]

    with col_ss2:
        st.write("**Методы прогнозирования**")
        method_a = st.selectbox(
            "Метод для группы A", 
            method_options,
            index=method_options.index(lc_methods.get('A', 'holt'))
        )
        method_b = st.selectbox(
            "Метод для группы B", 
            method_options,
            index=method_options.index(lc_methods.get('B', 'sma'))
        )
        method_c = st.selectbox(
            "Метод для группы C",
            method_options,
            index=method_options.index(lc_methods.get('C', 'naive'))
        )

    current_config = {
        "mapping": mapping,
        # "cleaning": {"fill_voids": "zeros"},
        "methods": {"A": method_a, "B": method_b, "C": method_c},
        "ss_params": {"z_score": z_score, "lead_time": lead_time}
    }

    st.divider()
    
    st.subheader("3. Параметры алгоритмов")
    fill_options = ["zeros", "mean"]
    default_fill = lc_cleaning.get('fill_voids', 'zeros')

    with st.expander("Настройки классификации и очистки"):
        col_cl1, _ = st.columns(2)
        fill_val = col_cl1.radio(
            "Заполнение пустот",
            fill_options,
            index=fill_options.index(default_fill)
        )

        st.write("Пороги ABC-анализа (%)")
        abc_threshold = st.slider("Граница группы А", 0, 100, lc.get('abc_threshold', 80) if lc else 80)

    if st.button("Выполнить расчёт", type="primary", use_container_width=True):
        current_config["abc_threshold"] = abc_threshold
        current_config["cleaning"] = {"fill_voids": fill_val}


        try:
            strategy = InventoryScenario(df, current_config)
            results = an_service.run_analysis(strategy)
            st.session_state.last_results = results
            st.session_state.active_config = current_config
            st.session_state.pop('loaded_config', None)
            st.session_state.pop('loaded_dataset_id', None)
            st.success("Расчёт завершён успешно!")
        except Exception as ex:
            st.error(f"Ошибка: {ex}")

    if 'last_results' in st.session_state:
        res = st.session_state.last_results

        st.divider()
        st.subheader("Аналитический дашборд")

        render_inventory_dashboard(res)

        if st.button("Сохранить результат в историю проекта"):
            active_project_id = st.session_state.get('current_project')
            
            if active_project_id is None:
                st.error("Ошибка: Не выбран активный проект! Выберите проект в боковой панели.")
            else:
                try:
                    us_id = an_service.save_scenario_settings(
                        user_id=user_id,
                        project_id=active_project_id,
                        dataset_id=selected_ds_id,
                        scenario_id=2, #исправить хардкод
                        config=st.session_state.get('active_config', current_config)
                    )

                    an_service.save_analysis_result(us_id, res)
                    st.success(f"Результат успешно сохранен! ID сценария: {us_id}")
                    # st.balloons()
                except Exception as e:
                    st.error(f"Ошибка при сохранении: {e}")