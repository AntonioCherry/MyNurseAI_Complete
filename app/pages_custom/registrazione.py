import streamlit as st
import datetime
import re
from app.models.user import User
from app.services.auth_service import hash_password

def register_page(db):
    st.title("MyNurseAI - Registrazione")
    st.subheader("Crea un account")

    ruoli_disponibili = ["Medico", "Paziente"]

    # --- Gestione ruolo fuori dal form per aggiornamento dinamico ---
    if "ruolo_temp" not in st.session_state:
        st.session_state.ruolo_temp = "Medico"

    ruolo = st.selectbox(
        "Ruolo",
        ruoli_disponibili,
        index=ruoli_disponibili.index(st.session_state.ruolo_temp)
    )

    if ruolo != st.session_state.ruolo_temp:
        st.session_state.ruolo_temp = ruolo
        st.rerun()

    # --- Campo Medico associato se Paziente ---
    medico_associato = None
    if ruolo == "Paziente":
        medico_associato = st.text_input("Email del medico associato")

    # --- Form di registrazione ---
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        st.markdown("### Dati personali")
        via = st.text_input("Via")
        numero_civico = st.number_input("Numero civico", min_value=0, step=1, format="%d")
        citta = st.text_input("Città")
        cap_num = st.number_input("CAP (5 cifre)", min_value=0, max_value=99999, step=1, format="%d")

        st.markdown("### Altri dati")
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        oggi = datetime.date.today()
        min_nascita = datetime.date(1900, 1, 1)
        max_nascita = oggi
        data_nascita = st.date_input("Data di nascita", min_value=min_nascita, max_value=max_nascita)
        sesso = st.selectbox("Sesso", ["Maschio", "Femmina", "Altro"])

        # --- Pulsanti ---
        col1, col2 = st.columns([4, 1])
        with col1:
            submitted = st.form_submit_button("Registrati")
        with col2:
            torna_login = st.form_submit_button("Torna al login")

    # --- Torna al login ---
    if 'torna_login' in locals() and torna_login:
        st.session_state.show_register = False
        st.rerun()

    if not submitted:
        return

    # --- Validazioni ---
    cap = str(int(cap_num)).zfill(5)
    error_msg = ""
    if not username or not email or not password or not via or not citta:
        error_msg = "Tutti i campi obbligatori devono essere compilati!"
    elif numero_civico <= 0:
        error_msg = "Inserisci un numero civico valido (solo cifre, maggiore di 0)."
    elif not re.fullmatch(r"^\d{5}$", cap):
        error_msg = "Il CAP deve contenere esattamente 5 cifre numeriche."
    else:
        existing_user = db.query(User).filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            error_msg = "Email o username già registrati"
        elif ruolo == "Paziente":
            medico = db.query(User).filter(User.email == medico_associato, User.role == "Medico").first()
            if not medico:
                error_msg = "Il medico associato non esiste. Inserisci una email valida di un medico registrato."
        else:
            medico_associato = None

    if error_msg:
        st.error(error_msg)
        return

    # --- Salvataggio utente ---
    hashed_pw = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role=ruolo,
        via=via,
        numero_civico=str(int(numero_civico)),
        citta=citta,
        cap=cap,
        data_nascita=data_nascita,
        sesso=sesso,
        nome=nome,
        cognome=cognome,
        medicoAssociato=medico_associato
    )
    db.add(user)
    db.commit()
    st.success("✅ Registrazione completata con successo!")

    st.session_state.show_register = False
    st.rerun()
