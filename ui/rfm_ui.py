import streamlit as st
import pandas as pd
import plotly.express as px
from bll.rfm_scenario import RFMScenario
from utils.dt_util import _col_index

def _render_segment_distribution(res: dict):
    summary_df = res['segment_summary']
    fig = px.pie(
        summary_df, names='segment', values='count',
        title="Распределение клиентов по сегментам", hole=0.6
    )
    st.plotly_chart(fig, use_container_width=True)

def _render_ltv_by_segment(res: dict):
    summary_df = res['segment_summary']
    fig = px.bar(
        summary_df, x='segment', y='total_ltv',
        title="Суммарный LTV-прогноз по сегментам",
        labels={'segment': 'Сегмент', 'total_ltv': 'LTV (руб.)'},
        color='segment'
    )
    st.plotly_chart(fig, use_container_width=True)

def _render_rfm_heatmap(res: dict):
    rfm_df = res['rfm_table']

    rfm_df = rfm_df.copy()
    rfm_df['r_bin'] = pd.cut(rfm_df['r_percentile'], bins=5, labels=[1, 2, 3, 4, 5])
    rfm_df['f_bin'] = pd.cut(rfm_df['f_percentile'], bins=5, labels=[1, 2, 3, 4, 5])

    matrix = rfm_df.groupby(
        ['r_bin', 'f_bin'], observed=True
    ).size().reset_index(name='count')

    pivot = matrix.pivot(index='r_bin', columns='f_bin', values='count').fillna(0)

    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect='auto',
        color_continuous_scale='Blues',
        labels=dict(x='Frequency (квинтиль)', y='Recency (квинтиль)', color='Клиентов'),
        title='Матрица плотности клиентов R×F'
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Плотность — количество клиентов в ячейке матрицы. Квинтиль 5 = лучший показатель.")

def _render_segment_summary_table(res: dict):
    st.write("#### Сводка по сегментам")
    st.dataframe(res['segment_summary'], use_container_width=True)

def _render_rfm_table(res: dict):
    st.write("#### Детальная таблица клиентов")
    st.dataframe(res['rfm_table'], use_container_width=True)



def render_rfm_dashboard(res: dict, use_tabs: bool = True):
    s = res['summary']
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Клиентов всего", s['total_clients'])
    m2.metric("Общая выручка", f"{s['total_revenue']:,.0f} ₽")
    m3.metric("LTV-прогноз (итого)", f"{s['total_ltv_forecast']:,.0f} ₽")
    m4.metric("Сегментов", s['segments_count'])

    st.divider()

    if use_tabs:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Сегменты", "LTV по сегментам",
            "Матрица R×F", "Сводная таблица", "Все клиенты"
        ])
        with tab1:
            _render_segment_distribution(res)
        with tab2:
            _render_ltv_by_segment(res)
        with tab3:
            _render_rfm_heatmap(res)
        with tab4:
            _render_segment_summary_table(res)
        with tab5:
            _render_rfm_table(res)
    else:
        st.subheader("Распределение по сегментам")
        _render_segment_distribution(res)
        st.divider()
        st.subheader("LTV по сегментам")
        _render_ltv_by_segment(res)
        st.divider()
        st.subheader("Матрица R×F")
        _render_rfm_heatmap(res)
        st.divider()
        st.subheader("Сводная таблица")
        _render_segment_summary_table(res)
        st.divider()
        st.subheader("Все клиенты")
        _render_rfm_table(res)



def _render_step1(ds_service, user_id: int, lc: dict):
    lc_mapping = lc.get('mapping', {}) if lc else {}
    lc_filters = lc.get('filters', {}) if lc else {}
    loaded_dataset_id = st.session_state.get('loaded_dataset_id')

    st.subheader("1. Подготовка данных")

    datasets = ds_service.get_user_datasets(user_id=user_id)
    ds_options = {d.dataset_id: d.file_name for d in datasets}
    ds_ids = list(ds_options.keys())

    if not ds_ids:
        st.warning("Нет загруженных датасетов. Загрузите файл в боковой панели.")
        return

    default_ds_index = ds_ids.index(loaded_dataset_id) if (
        loaded_dataset_id and loaded_dataset_id in ds_ids
    ) else 0

    selected_ds_id = st.selectbox(
        "Выберите датасет",
        options=ds_ids,
        format_func=lambda x: ds_options[x],
        index=default_ds_index,
        key='rfm_selected_ds_id'
    )
    st.session_state.rfm_dataset_id = selected_ds_id

    df_raw = ds_service.get_dataframe(selected_ds_id)
    cols = df_raw.columns.tolist()

    st.info("Укажите, какие столбцы соответствуют требуемым параметрам")
    c1, c2, c3 = st.columns(3)
    with c1:
        m_client = st.selectbox(
            "ID клиента", cols,
            index=_col_index(cols, lc_mapping.get('client_id', cols[0])),
            key='rfm_m_client'
        )
    with c2:
        m_date = st.selectbox(
            "Дата транзакции", cols,
            index=_col_index(cols, lc_mapping.get('date', cols[0])),
            key='rfm_m_date'
        )
    with c3:
        m_amount = st.selectbox(
            "Сумма транзакции", cols,
            index=_col_index(cols, lc_mapping.get('amount', cols[0])),
            key='rfm_m_amount'
        )

    st.divider()
    st.write("**Фильтры**")

    col_f1, col_f2 = st.columns(2)

    try:
        dates = pd.to_datetime(df_raw[m_date], errors='coerce').dropna()
        min_date = dates.min().date()
        max_date = dates.max().date()
    except Exception:
        import datetime
        min_date = datetime.date(2020, 1, 1)
        max_date = datetime.date.today()

    with col_f1:
        date_from = st.date_input(
            "Дата с",
            value=pd.to_datetime(lc_filters.get('date_from', min_date)).date() if lc_filters.get('date_from') else min_date,
            min_value=min_date,
            max_value=max_date,
            key='rfm_date_from'
        )
    with col_f2:
        date_to = st.date_input(
            "Дата по",
            value=pd.to_datetime(lc_filters.get('date_to', max_date)).date() if lc_filters.get('date_to') else max_date,
            min_value=min_date,
            max_value=max_date,
            key='rfm_date_to'
        )

    min_monetary = st.number_input(
        "Минимальный суммарный чек клиента (руб.)",
        min_value=0,
        value=int(lc_filters.get('min_monetary', 0)),
        step=100,
        help="Клиенты с суммарными тратами ниже этого значения будут исключены",
        key='rfm_min_monetary'
    )

    st.divider()

    with st.expander("👁 Предпросмотр данных"):
        st.write("**Исходная таблица (первые 5 строк):**")
        st.dataframe(df_raw.head(5), use_container_width=True)

    st.session_state.rfm_step1_config = {
        'mapping': {
            'client_id': m_client,
            'date': m_date,
            'amount': m_amount
        },
        'filters': {
            'date_from': str(date_from),
            'date_to': str(date_to),
            'min_monetary': min_monetary
        }
    }

    if st.button("Далее →", type="primary", use_container_width=True, key='rfm_step1_next'):
        st.session_state.rfm_step = 2
        st.rerun()

def _render_step2(lc: dict):
    lc_segments = lc.get('segments', []) if lc else []

    st.subheader("2. Настройка сегментов")
    st.caption("Каждый клиент попадает в первый подходящий сегмент (порядок = приоритет).")

    if 'rfm_segments' not in st.session_state or st.session_state.get('rfm_segments_just_loaded'):
        if lc_segments:
            st.session_state.rfm_segments = lc_segments.copy()
        else:
            st.session_state.rfm_segments = [
                {"name": "Приоритетные",  "r_range": [75, 100], "f_range": [75, 100], "m_range": [75, 100]},
                {"name": "Лояльные",  "r_range": [50, 100], "f_range": [50, 100], "m_range": [0, 100]},
                {"name": "Малоактивные",    "r_range": [0, 25],   "f_range": [0, 100],  "m_range": [0, 100]},
            ]
        st.session_state.rfm_segments_just_loaded = False

    segments = st.session_state.rfm_segments

    for i, seg in enumerate(segments):
        with st.container(border=True):
            col_name, col_del = st.columns([4, 1])

            seg['name'] = col_name.text_input(
                "Название сегмента", value=seg['name'], key=f"seg_name_{i}"
            )
            if col_del.button("🗑️", key=f"seg_del_{i}", help="Удалить сегмент"):
                segments.pop(i)
                st.rerun()

            c1, c2, c3 = st.columns(3)
            seg['r_range'] = list(c1.slider(
                "R — Давность (перцентиль)",
                0, 100, tuple(seg['r_range']), key=f"r_{i}",
                help="100 = покупал совсем недавно"
            ))
            seg['f_range'] = list(c2.slider(
                "F — Частота (перцентиль)",
                0, 100, tuple(seg['f_range']), key=f"f_{i}",
                help="100 = очень часто покупает"
            ))
            seg['m_range'] = list(c3.slider(
                "M — Деньги (перцентиль)",
                0, 100, tuple(seg['m_range']), key=f"m_{i}",
                help="100 = максимальные траты"
            ))

    st.divider()

    if st.button("➕ Добавить сегмент", use_container_width=True):
        segments.append({
            "name": f"Сегмент {len(segments) + 1}",
            "r_range": [0, 100],
            "f_range": [0, 100],
            "m_range": [0, 100]
        })
        st.rerun()

    st.divider()

    col_back, col_next = st.columns(2)
    if col_back.button("← Назад", use_container_width=True, key='rfm_step2_back'):
        st.session_state.rfm_step = 1
        st.rerun()
    if col_next.button("Далее →", type="primary", use_container_width=True, key='rfm_step2_next'):
        if not segments:
            st.error("Добавьте хотя бы один сегмент.")
        else:
            st.session_state.rfm_step = 3
            st.rerun()

def _render_step3(lc: dict):
    lc_ltv = lc.get('ltv', {}) if lc else {}
    lc_actions = lc.get('actions', {}) if lc else {}

    st.subheader("3. LTV и маркетинговые действия")

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        horizon = st.number_input(
            "Горизонт прогноза (мес.)",
            min_value=1, max_value=60,
            value=int(lc_ltv.get('horizon_months', 6)),
            step=1,
            key='rfm_horizon'
        )
    with col_l2:
        margin = st.slider(
            "Маржинальность (%)",
            min_value=1, max_value=100,
            value=int(lc_ltv.get('margin_pct', 20)),
            key='rfm_margin'
        )

    st.divider()
    st.write("**Маркетинговые действия по сегментам**")
    st.caption("Для каждого сегмента выберите тип действия и добавьте комментарий.")

    action_options = ["Ничего", "Скидка", "Подарок", "Консультация", "Персональное предложение"]
    segments = st.session_state.get('rfm_segments', [])
    actions = {}

    all_segment_names = [s['name'] for s in segments] + ['Прочие']

    for seg_name in all_segment_names:
        with st.container(border=True):
            st.write(f"**{seg_name}**")
            col_a, col_c = st.columns([1, 2])

            default_action = lc_actions.get(seg_name, {}).get('action', 'Ничего')
            default_action_idx = action_options.index(default_action) if default_action in action_options else 0

            action = col_a.selectbox(
                "Действие",
                action_options,
                index=default_action_idx,
                key=f"action_{seg_name}"
            )
            comment = col_c.text_input(
                "Комментарий",
                value=lc_actions.get(seg_name, {}).get('comment', ''),
                key=f"comment_{seg_name}"
            )
            actions[seg_name] = {'action': action, 'comment': comment}

    st.session_state.rfm_step3_config = {
        'ltv': {'horizon_months': horizon, 'margin_pct': margin},
        'actions': actions
    }

    st.divider()

    col_back, col_next = st.columns(2)
    if col_back.button("← Назад", use_container_width=True, key='rfm_step3_back'):
        st.session_state.rfm_step = 2
        st.rerun()
    if col_next.button("▶️ Выполнить расчёт", type="primary", use_container_width=True, key='rfm_step3_next'):
        st.session_state.rfm_step = 4
        st.rerun()

def _render_step4(ds_service, an_service, user_id: int):
    st.subheader("4. Результаты анализа")

    config = {
        **st.session_state.get('rfm_step1_config', {}),
        'segments': st.session_state.get('rfm_segments', []),
        **st.session_state.get('rfm_step3_config', {})
    }

    if 'rfm_last_results' not in st.session_state:
        try:
            with st.spinner("Выполняется расчёт..."):
                dataset_id = st.session_state.get('rfm_dataset_id')
                df = ds_service.get_dataframe(dataset_id)
                strategy = RFMScenario(df, config)
                results = an_service.run_analysis(strategy)
                st.session_state.rfm_last_results = results
                st.session_state.rfm_active_config = config
                st.session_state.pop('loaded_config', None)
                st.session_state.pop('loaded_dataset_id', None)
                st.success("Расчёт завершён успешно!")
        except Exception as ex:
            st.error(f"Ошибка при расчёте: {ex}")
            if st.button("← Вернуться к настройкам"):
                st.session_state.rfm_step = 3
                st.rerun()
            return
        
    res = st.session_state.rfm_last_results
    render_rfm_dashboard(res, use_tabs=True)

    st.divider()

    col_back, col_save = st.columns(2)

    if col_back.button("← Изменить параметры", use_container_width=True, key='rfm_step4_back'):
        st.session_state.pop('rfm_last_results', None)
        st.session_state.rfm_step = 3
        st.rerun()

    if col_save.button(
        "💾 Сохранить в историю проекта",
        type="primary",
        use_container_width=True,
        key='rfm_save'
    ):
        active_project_id = st.session_state.get('current_project')
        if active_project_id is None:
            st.error("Не выбран активный проект! Выберите проект в боковой панели.")
        else:
            try:
                dataset_id = st.session_state.get('rfm_dataset_id')
                us_id = an_service.save_scenario_settings(
                    user_id=user_id,
                    project_id=active_project_id,
                    dataset_id=dataset_id,
                    scenario_id=3,
                    config=st.session_state.get('rfm_active_config', config)
                )
                an_service.save_analysis_result(us_id, res)
                st.success(f"Результат сохранён! ID сценария: {us_id}")
            except Exception as e:
                st.error(f"Ошибка при сохранении: {e}")

def render_rfm_ui(ds_service, an_service, user_id: int):
    st.title("👥 Управление клиентским капиталом и лояльностью")

    lc = st.session_state.get('loaded_config')

    if 'rfm_step' not in st.session_state:
        st.session_state.rfm_step = 1
    if lc and not st.session_state.get('rfm_lc_applied'):
        st.session_state.rfm_step = 1
        st.session_state.rfm_segments_just_loaded = True
        st.session_state.pop('rfm_last_results', None)
        st.session_state.rfm_lc_applied = True
    if not lc:
        st.session_state.rfm_lc_applied = False

    if lc:
        st.info("✅ Загружен сохранённый сценарий. Параметры предзаполнены — вы можете их изменить.")

    step = st.session_state.rfm_step
    step_labels = ["Данные", "Сегменты", "LTV и действия", "Результаты"]
    st.progress(step / 4, text=f"Шаг {step} из 4: {step_labels[step - 1]}")
    st.divider()

    if step == 1:
        _render_step1(ds_service, user_id, lc)
    elif step == 2:
        _render_step2(lc)
    elif step == 3:
        _render_step3(lc)
    elif step == 4:
        _render_step4(ds_service, an_service, user_id)