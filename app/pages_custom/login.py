import time
import streamlit as st
from app.models.user import User
from app.services.auth_service import verify_password
from app.pages_custom.registrazione import register_page
from app.pages_custom.area_personale import area_personale

def login_page(db):
    # --- Inizializza lo stato ---
    if "show_register" not in st.session_state:
        st.session_state.show_register = False
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user" not in st.session_state:
        st.session_state.user = None

    # --- 🔹 Rileggi email dai parametri URL (nuova sintassi) ---
    query_params = st.query_params  # ✅ nuovo metodo
    if "email" in query_params and not st.session_state.logged_in:
        email_param = query_params["email"]
        if isinstance(email_param, list):
            email_param = email_param[0]
        user = db.query(User).filter(User.email == email_param).first()
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.rerun()

    # --- Se loggato, mostra area personale ---
    if st.session_state.logged_in and st.session_state.user:
        area_personale(st.session_state.user)
        return

    # --- Se si è cliccato “Registrati” ---
    if st.session_state.show_register:
        register_page(db)
        return


    st.title("MyNurseAI - Login")
    # --- Form di login ---
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Accedi")

    # --- Testo + link registrazione ---
    col1, col2 = st.columns([3, 1], gap="small")
    with col1:
        st.write("Non hai ancora un account?")
    with col2:
        if st.button("Registrati"):
            st.session_state.show_register = True
            st.rerun()

    # --- Logica login ---
    if submitted:
        if not email or not password:
            st.error("Email e password sono obbligatorie!")
            return

        user = db.query(User).filter(User.email == email).first()
        if not user:
            st.error("Utente non trovato.")
            return
        if not verify_password(password, user.hashed_password):
            st.error("Password errata.")
            return

        # ✅ Login riuscito
        st.session_state.logged_in = True
        st.session_state.user = user

        # ✅ Nuovo modo per impostare i query params
        st.query_params["email"] = user.email

        st.success("✅ Accesso effettuato con successo!")
        time.sleep(1)
        st.rerun()
