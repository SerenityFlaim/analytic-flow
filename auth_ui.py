import streamlit as st
from bll.services.auth_service import AuthService

def render_auth_ui(auth_service: AuthService):
    st.title("AnalyticFlow")
    st.caption("Интерактивный инструмент бизнес-анализа")
    st.divider()

    tab_login, tab_register = st.tabs(["Войти", "Зарегистрироваться"])

    with tab_login:
        st.subheader("Вход в систему")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Пароль", type="password", key="login_password")

        if st.button("Войти", use_container_width=True, type="primary"):
            if not login_email or not login_password:
                st.error("Заполните все поля!")
            else:
                try:
                    user = auth_service.login(login_email, login_password)
                    st.session_state.user = {
                        "id": user.user_id,
                        "name": user.name,
                        "email": user.email
                    }
                    st.success(f"Добро пожаловать, {user.name}!")
                    st.rerun()
                except ValueError as ex:
                    st.error(str(ex))

    with tab_register:
        st.subheader("Регистрация")
        reg_name = st.text_input("Имя", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Пароль", type="password", key="reg_password")
        reg_password2 = st.text_input("Повторите пароль", type="password", key="reg_password2")

        if st.button("Зарегистрироваться", use_container_width=True, type="primary"):
            if not all([reg_name, reg_email, reg_password, reg_password2]):
                st.error("Заполните все поля!")
            elif reg_password != reg_password2:
                st.error("Пароли не совпадают.")
            else:
                try:
                    user = auth_service.register(
                        email=reg_email,
                        password=reg_password,
                        name=reg_name
                    )
                    st.success("Аккаунт создан! Теперь войдите в систему.")
                except ValueError as ex:
                    st.error(str(ex))
