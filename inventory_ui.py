import streamlit as st
import pandas as pd
import plotly.express as px
from bll.inventory_scenario import InventoryScenario

def render_inventory_ui(ds_service, an_service, user_id: int):
    st.title("📦 Настройка инвентарного анализа")

    st.subheader("1. Подготовка данных")
    datasets = ds_service.get_user_datasets(user_id=user_id)
    ds_options = {d.dataset_id: d.file_name for d in datasets}

    selected_ds_id = st.selectbox("Выберите датасет для анализа",
                                  options=list(ds_options.keys()),
                                  format_func=lambda x: ds_options[x])
    
    df = ds_service.get_dataframe(selected_ds_id)
    cols = df.columns.tolist()

    st.info("Укажите, какие столбцы соответствуют требуемым параметрам")
    c1, c2, c3, c4 = st.columns(4)
    with c1: m_id = st.selectbox("ID товара / SKU", cols)
    with c2: m_date = st.selectbox("Дата транзакции", cols)
    with c3: m_vol = st.selectbox("Количество (Объём)", cols)
    with c4: m_rev = st.selectbox("Выручка (Сумма)", cols)

    mapping = {"id": m_id, "date": m_date, "volume": m_vol, "revenue": m_rev}

    st.divider()

    st.subheader("2. Параметры расчета")
    col_ss1, col_ss2 = st.columns(2)
    
    with col_ss1:
        st.write("**Страховой запас (Safety Stock)**")
        lead_time = st.number_input("Lead Time (Время поставки, мес.)", min_value=0.1, value=1.0, step=0.1)
        service_level = st.select_slider(
            "Уровень сервиса",
            options=[0.80, 0.85, 0.90, 0.95, 0.99],
            value=0.95,
            help="Влияет на коэффициент Z"
        )
        z_mapping = {0.80: 0.84, 0.85: 1.04, 0.90: 1.28, 0.95: 1.65, 0.99: 2.33}
        z_score = z_mapping[service_level]

    with col_ss2:
        st.write("**Методы прогнозирования**")
        method_a = st.selectbox("Метод для группы A", ["holt", "sma", "naive"], index=0)
        method_b = st.selectbox("Метод для группы B", ["holt", "sma", "naive"], index=1)
        method_c = st.selectbox("Метод для группы C", ["holt", "sma", "naive"], index=2)

    current_config = {
        "mapping": mapping,
        # "cleaning": {"fill_voids": "zeros"},
        "methods": {"A": method_a, "B": method_b, "C": method_c},
        "ss_params": {"z_score": z_score, "lead_time": lead_time}
    }

    st.divider()
    st.subheader("3. Параметры алгоритмов")
    with st.expander("Настройки классификации и очистки"):
        col_cl1, col_cl2 = st.columns(2)
        fill_val = col_cl1.radio("Заполнение пустот", ["zeros", "mean"])

        st.write("Пороги ABC-анализа (%)")
        abc_threshold = st.slider("Граница группы А", 0, 100, 80)

    if st.button("Выполнить расчёт", type="primary", use_container_width=True):
        current_config["abc_threshold"] = abc_threshold
        current_config["cleaning"] = {"fill_voids": fill_val}


        try:
            strategy = InventoryScenario(df, current_config)
            results = an_service.run_analysis(strategy)
            st.session_state.last_results = results
            st.session_state.active_config = current_config
            st.success("Расчёт завершён успешно!")
        except Exception as ex:
            st.error(f"Ошибка: {ex}")

    if 'last_results' in st.session_state:
        res = st.session_state.last_results
        full_table = res['analysis_table']



        st.divider()
        st.subheader("Аналитический дашборд")

        tab1, tab2, tab3, tab4 = st.tabs(["Структура групп", "Прогноз и спрос", "Итоговая таблица", "Матрица ABC-XYZ"])

        with tab1:
            fig_abc = px.pie(res['analysis_table'], names='abc_category', title="Распределение позиций по выручке (ABC)", hole=0.6)
            st.plotly_chart(fig_abc, use_container_width=True)

        with tab2:
            st.write("#### Детализация прогноза")
            st.dataframe(res['forecast_report'], use_container_width=True)

            top_item = res['forecast_report'].iloc[0]['item_id']
            st.info(f"Рекомендация для {top_item}: Страховой запас - {res['forecast_report'].iloc[0]['safety_stock']} ед.")

        with tab3:
            st.dataframe(res['analysis_table'], use_container_width=True)

        with tab4:
            st.subheader("Тепловая карта распределения SKU")
            matrix_data = res['analysis_table'].groupby(['abc_category', 'xyz_category']).size().reset_index(name='count')
            pivot_matrix = matrix_data.pivot(index='abc_category', columns='xyz_category', values='count').fillna(0)
            
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
                            scenario_id=2,
                            config=current_config
                        )

                        an_service.save_analysis_result(us_id, res)
                        st.success(f"Результат успешно сохранен! ID сценария: {us_id}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Ошибка при сохранении: {e}")