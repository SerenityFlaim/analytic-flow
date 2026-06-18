import streamlit as st
import pandas as pd
import plotly.express as px
from bll.financial_scenario import FinancialScoringScenario
from utils.dt_util import _col_index

RISK_COLORS = {'A': '#2ecc71', 'B': '#f1c40f', 'C': '#e67e22', 'D': '#e74c3c'}

def _render_risk_distribution(res: dict):
    summary_df = res['risk_summary']
    fig = px.pie(
        summary_df, names='risk_class', values='count',
        title="Распределение контрагентов по классам риска", hole=0.6,
        color='risk_class', color_discrete_map=RISK_COLORS
    )
    st.plotly_chart(fig, use_container_width=True)

def _render_expected_loss_by_class(res: dict):
    summary_df = res['risk_summary']
    fig = px.bar(
        summary_df, x='risk_class', y='total_expected_loss',
        title="Ожидаемые потери (Expected Loss) по классам риска",
        labels={'risk_class': 'Класс риска', 'total_expected_loss': 'EL (руб.)'},
        color='risk_class', color_discrete_map=RISK_COLORS
    )
    st.plotly_chart(fig, use_container_width=True)

def _render_risk_quadrant(res: dict):
    profile_df = res['debtor_profile']
    fig = px.scatter(
        profile_df, x='current_debt', y='credit_score',
        color='risk_class', color_discrete_map=RISK_COLORS,
        hover_data=['debtor_id', 'dpd_avg', 'expected_loss'],
        title="Квадрант-матрица: Сумма долга × Скоринговый балл",
        labels={'current_debt': 'Текущий долг (руб.)', 'credit_score': 'Credit Score'}
    )
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Верхний левый угол — безопасная зона. Нижний правый — зона повышенного риска.")


def _render_risk_summary_table(res: dict):
    st.write("#### Сводка по классам риска")
    st.dataframe(res['risk_summary'], use_container_width=True)

def _render_debtor_table(res: dict):
    st.write("#### Реестр контрагентов с рекомендациями")
    cols_order = [
        'debtor_id', 'current_debt', 'dpd_avg', 'risk_class',
        'credit_score', 'expected_loss', 'credit_limit', 'strategy'
    ]
    df = res['debtor_profile']
    display_cols = [c for c in cols_order if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)


def render_financial_dashboard(res: dict, use_tabs: bool = True):
    s = res['summary']
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Контрагентов", s['total_debtors'])
    m2.metric("Текущий долг", f"{s['total_current_debt']:,.0f} ₽")
    m3.metric("Expected Loss", f"{s['total_expected_loss']:,.0f} ₽")
    m4.metric("Средний Credit Score", f"{s['avg_credit_score']:.1f}")

    st.divider()

    if use_tabs:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Классы риска", "Expected Loss",
            "Квадрант риска", "Сводная таблица", "Реестр контрагентов"
        ])
        with tab1:
            _render_risk_distribution(res)
        with tab2:
            _render_expected_loss_by_class(res)
        with tab3:
            _render_risk_quadrant(res)
        with tab4:
            _render_risk_summary_table(res)
        with tab5:
            _render_debtor_table(res)
    else:
        st.subheader("Распределение по классам риска")
        _render_risk_distribution(res)
        st.divider()
        st.subheader("Expected Loss по классам")
        _render_expected_loss_by_class(res)
        st.divider()
        st.subheader("Квадрант риска")
        _render_risk_quadrant(res)
        st.divider()
        st.subheader("Сводная таблица")
        _render_risk_summary_table(res)
        st.divider()
        st.subheader("Реестр контрагентов")
        _render_debtor_table(res)

def _render_step1(ds_service, user_id: int, lc: dict):
    lc_mapping = lc.get('mapping', {}) if lc else {}
    loaded_dataset_id = st.session_state.get('loaded_dataset_id')

    st.subheader("1. Маппинг данных и отчётная дата")

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
        key='fin_selected_ds_id'
    )
    st.session_state.fin_dataset_id = selected_ds_id

    df_raw = ds_service.get_dataframe(selected_ds_id)
    cols = df_raw.columns.tolist()

    st.info("Укажите, какие столбцы соответствуют требуемым параметрам")
    c1, c2 = st.columns(2)
    with c1:
        m_debtor = st.selectbox(
            "ID / Наименование дебитора", cols,
            index=_col_index(cols, lc_mapping.get('debtor_id', cols[0])),
            key='fin_m_debtor'
        )
        m_invoice_date = st.selectbox(
            "Дата выставления счёта", cols,
            index=_col_index(cols, lc_mapping.get('invoice_date', cols[0])),
            key='fin_m_invoice_date'
        )
        m_amount = st.selectbox(
            "Сумма счёта", cols,
            index=_col_index(cols, lc_mapping.get('amount', cols[0])),
            key='fin_m_amount'
        )
    with c2:
        m_due_date = st.selectbox(
            "Плановая дата платежа (Due Date)", cols,
            index=_col_index(cols, lc_mapping.get('due_date', cols[0])),
            key='fin_m_due_date'
        )
        m_fact_date = st.selectbox(
            "Фактическая дата оплаты", cols,
            index=_col_index(cols, lc_mapping.get('fact_date', cols[0])),
            key='fin_m_fact_date'
        )
        st.caption("Если поле фактической оплаты пустое — счёт считается неоплаченным долгом")

    st.divider()

    report_date_default = lc.get('report_date') if lc else None
    report_date = st.date_input(
        "Отчётная дата",
        value=pd.to_datetime(report_date_default).date() if report_date_default else pd.Timestamp.now().date(),
        help="Счета выставленные после этой даты не учитываются",
        key='fin_report_date'
    )

    st.divider()

    with st.expander("👁 Предпросмотр данных"):
        st.write("**Исходная таблица (первые 5 строк):**")
        st.dataframe(df_raw.head(5), use_container_width=True)

    st.session_state.fin_step1_config = {
        'mapping': {
            'debtor_id': m_debtor,
            'invoice_date': m_invoice_date,
            'due_date': m_due_date,
            'fact_date': m_fact_date,
            'amount': m_amount
        },
        'report_date': str(report_date)
    }

    if st.button("Далее →", type="primary", use_container_width=True, key='fin_step1_next'):
        st.session_state.fin_step = 2
        st.rerun()

def _render_step2(lc: dict):
    lc_weights = lc.get('weights', {}) if lc else {}

    st.subheader("2. Конструктор скоринговой модели")
    st.caption("Распределите веса значимости факторов риска. Сумма весов должна равняться 100%.")

    w_dpd = st.slider(
        "Фактор просрочки (DPD)",
        0, 100, int(lc_weights.get('dpd', 0.4) * 100),
        help="Насколько критичен сам факт опоздания платежа",
        key='fin_w_dpd'
    )
    w_conc = st.slider(
        "Фактор объёма долга (Concentration)",
        0, 100, int(lc_weights.get('concentration', 0.3) * 100),
        help="Насколько опасно для компании, если долг этого контрагента вырастет",
        key='fin_w_conc'
    )
    w_disc = st.slider(
        "Фактор частоты нарушений (Discipline)",
        0, 100, int(lc_weights.get('discipline', 0.3) * 100),
        help="Регулярность задержек платежей",
        key='fin_w_disc'
    )

    total = w_dpd + w_conc + w_disc
    if total != 100:
        st.warning(f"Сумма весов: {total}%. Должна быть ровно 100%.")
    else:
        st.success("Сумма весов: 100% ✓")

    st.session_state.fin_step2_config = {
        'weights': {
            'dpd': round(w_dpd / 100, 2),
            'concentration': round(w_conc / 100, 2),
            'discipline': round(w_disc / 100, 2)
        }
    }

    st.divider()
    col_back, col_next = st.columns(2)
    if col_back.button("← Назад", use_container_width=True, key='fin_step2_back'):
        st.session_state.fin_step = 1
        st.rerun()
    if col_next.button("Далее →", type="primary", use_container_width=True, key='fin_step2_next'):
        if total != 100:
            st.error("Сумма весов должна быть равна 100% перед переходом далее.")
        else:
            st.session_state.fin_step = 3
            st.rerun()

def _render_step3(lc: dict):
    lc_risk_classes = lc.get('risk_classes', {}) if lc else {}
    lc_pd = lc.get('pd_by_class', {}) if lc else {}

    st.subheader("3. Классы риска и вероятность дефолта")
    st.caption("Настройте границы скор-баллов, стратегию работы и вероятность дефолта для каждого класса.")

    if 'fin_risk_classes' not in st.session_state or st.session_state.get('fin_rc_just_loaded'):
        if lc_risk_classes:
            st.session_state.fin_risk_classes = {
                k: v.copy() for k, v in lc_risk_classes.items()
            }
            st.session_state.fin_pd_values = lc_pd.copy() if lc_pd else {}
        else:
            st.session_state.fin_risk_classes = {
                "A": {"min_score": 80, "max_score": 100, "strategy": "Отсрочка платежа", "max_days": 30},
                "B": {"min_score": 60, "max_score": 79,  "strategy": "Факторинг / сокращённая отсрочка", "max_days": 14},
                "C": {"min_score": 30, "max_score": 59,  "strategy": "Частичная предоплата (50/50)", "max_days": 0},
                "D": {"min_score": 0,  "max_score": 29,  "strategy": "100% предоплата / блокировка поставок", "max_days": 0},
            }
            st.session_state.fin_pd_values = {"A": 5, "B": 20, "C": 60, "D": 90}
        st.session_state.fin_rc_just_loaded = False

    risk_classes = st.session_state.fin_risk_classes
    pd_values = st.session_state.fin_pd_values

    class_order = ['A', 'B', 'C', 'D']
    class_emoji = {'A': '🟢', 'B': '🟡', 'C': '🟠', 'D': '🔴'}

    for cls in class_order:
        cls_def = risk_classes.get(cls)
        if cls_def is None:
            continue
        with st.container(border=True):
            st.write(f"### {class_emoji.get(cls, '')} Класс {cls}")

            col_range, col_pd = st.columns([2, 1])
            with col_range:
                score_range = st.slider(
                    "Диапазон скор-баллов",
                    0, 100, (cls_def['min_score'], cls_def['max_score']),
                    key=f"rc_range_{cls}"
                )
                cls_def['min_score'], cls_def['max_score'] = score_range
            with col_pd:
                pd_val = st.number_input(
                    "PD — вероятность дефолта (%)",
                    min_value=0, max_value=100,
                    value=int(pd_values.get(cls, 0)),
                    key=f"pd_{cls}"
                )
                pd_values[cls] = pd_val

            col_strategy, col_days = st.columns([2, 1])
            with col_strategy:
                cls_def['strategy'] = st.text_input(
                    "Стратегия работы с контрагентом",
                    value=cls_def['strategy'],
                    key=f"strategy_{cls}"
                )
            with col_days:
                cls_def['max_days'] = st.number_input(
                    "Макс. отсрочка (дней)",
                    min_value=0, max_value=180,
                    value=int(cls_def['max_days']),
                    key=f"max_days_{cls}"
                )

    st.session_state.fin_step3_config = {
        'risk_classes': risk_classes,
        'pd_by_class': {k: round(v / 100, 2) for k, v in pd_values.items()}
    }

    st.divider()
    col_back, col_next = st.columns(2)
    if col_back.button("← Назад", use_container_width=True, key='fin_step3_back'):
        st.session_state.fin_step = 2
        st.rerun()
    if col_next.button("Далее →", type="primary", use_container_width=True, key='fin_step3_next'):
        st.session_state.fin_step = 4
        st.rerun()

def _render_step4_params(lc: dict):
    lc_business = lc.get('business_params', {}) if lc else {}

    st.subheader("4. Бизнес-параметры")

    col1, col2 = st.columns(2)
    with col1:
        margin_pct = st.slider(
            "Маржинальность бизнеса (%)",
            min_value=1, max_value=100,
            value=int(lc_business.get('margin_pct', 20)),
            help="Используется для расчёта безопасного кредитного лимита",
            key='fin_margin_pct'
        )
    with col2:
        credit_horizon = st.number_input(
            "Горизонт кредитования (дней)",
            min_value=1, max_value=365,
            value=int(lc_business.get('credit_horizon_days', 30)),
            help="На какой срок рассматривается отгрузка в долг",
            key='fin_credit_horizon'
        )

    st.session_state.fin_step4_config = {
        'business_params': {
            'margin_pct': margin_pct,
            'credit_horizon_days': credit_horizon
        }
    }

    st.divider()
    col_back, col_next = st.columns(2)
    if col_back.button("← Назад", use_container_width=True, key='fin_step4_back'):
        st.session_state.fin_step = 3
        st.rerun()
    if col_next.button("▶️ Выполнить расчёт", type="primary", use_container_width=True, key='fin_step4_next'):
        st.session_state.fin_step = 5
        st.rerun()

def _render_step5(ds_service, an_service, user_id: int):
    st.subheader("5. Результаты анализа")

    config = {
        **st.session_state.get('fin_step1_config', {}),
        **st.session_state.get('fin_step2_config', {}),
        **st.session_state.get('fin_step3_config', {}),
        **st.session_state.get('fin_step4_config', {}),
    }

    if 'fin_last_results' not in st.session_state:
        try:
            with st.spinner("Выполняется расчёт..."):
                dataset_id = st.session_state.get('fin_dataset_id')
                df = ds_service.get_dataframe(dataset_id)
                strategy = FinancialScoringScenario(df, config)
                results = an_service.run_analysis(strategy)
                st.session_state.fin_last_results = results
                st.session_state.fin_active_config = config
                st.session_state.pop('loaded_config', None)
                st.session_state.pop('loaded_dataset_id', None)
                st.success("Расчёт завершён успешно!")
        except Exception as ex:
            st.error(f"Ошибка при расчёте: {ex}")
            if st.button("← Вернуться к настройкам"):
                st.session_state.fin_step = 4
                st.rerun()
            return
    
    res = st.session_state.fin_last_results
    render_financial_dashboard(res, use_tabs=True)

    st.divider()

    col_back, col_save = st.columns(2)

    if col_back.button("← Изменить параметры", use_container_width=True, key='fin_step5_back'):
        st.session_state.pop('fin_last_results', None)
        st.session_state.fin_step = 4
        st.rerun()

    if col_save.button(
        "💾 Сохранить в историю проекта",
        type="primary",
        use_container_width=True,
        key='fin_save'
    ):
        from bll.scenario_registry import registry
        active_project_id = st.session_state.get('current_project')
        if active_project_id is None:
            st.error("Не выбран активный проект! Выберите проект в боковой панели.")
        else:
            try:
                dataset_id = st.session_state.get('fin_dataset_id')
                scenario_id = registry.get_id_by_page('financial')
                us_id = an_service.save_scenario_settings(
                    user_id=user_id,
                    project_id=active_project_id,
                    dataset_id=dataset_id,
                    scenario_id=scenario_id,
                    config=st.session_state.get('fin_active_config', config)
                )
                an_service.save_analysis_result(us_id, res)
                st.success(f"Результат сохранён! ID сценария: {us_id}")
            except Exception as e:
                st.error(f"Ошибка при сохранении: {e}")

def render_financial_ui(ds_service, an_service, user_id: int):
    st.title("💰 Финансовый скоринг дебиторской задолженности")

    lc = st.session_state.get('loaded_config')

    if 'fin_step' not in st.session_state:
        st.session_state.fin_step = 1
    if lc and not st.session_state.get('fin_lc_applied'):
        st.session_state.fin_step = 1
        st.session_state.fin_rc_just_loaded = True
        st.session_state.pop('fin_last_results', None)
        st.session_state.fin_lc_applied = True
    if not lc:
        st.session_state.fin_lc_applied = False

    if lc:
        st.info("✅ Загружен сохранённый сценарий. Параметры предзаполнены — вы можете их изменить.")

    step = st.session_state.fin_step
    step_labels = ["Данные", "Веса модели", "Классы риска", "Бизнес-параметры", "Результаты"]
    st.progress(step / 5, text=f"Шаг {step} из 5: {step_labels[step - 1]}")
    st.divider()

    if step == 1:
        _render_step1(ds_service, user_id, lc)
    elif step == 2:
        _render_step2(lc)
    elif step == 3:
        _render_step3(lc)
    elif step == 4:
        _render_step4_params(lc)
    elif step == 5:
        _render_step5(ds_service, an_service, user_id)