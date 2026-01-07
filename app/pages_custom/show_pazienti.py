import streamlit as st

from app.components.sidebar import sidebar
from app.models.user import User

def show_pazienti(db, user):
    sidebar(user)

    st.title("🧍‍♂️ Pazienti associati")
    st.markdown(f"### Lista dei pazienti associati a: **{user.username}**")

    pazienti = db.query(User).filter(
        User.medicoAssociato == user.email,
        User.role == "Paziente"
    ).all()

    if not pazienti:
        st.info("Non ci sono pazienti associati a questo medico.")
        return

    if "current_page" not in st.session_state:
        st.session_state.current_page = "show_pazienti"

    # --- LISTA PAZIENTI ---
    for i, p in enumerate(pazienti):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.button(f"👤 {p.nome} {p.cognome} — {p.email}", key=f"btn_{p.email}", use_container_width=True)
        with col2:
            if st.button("📤", key=f"upload_{p.email}", help="Vai ai documenti del paziente"):
                st.session_state.current_page = "upload_docs"
                st.session_state.selected_paziente = p
                st.rerun()

        if i < len(pazienti) - 1:
            st.markdown("<div style='margin:2px 0;border-bottom:1px solid #ddd;'></div>", unsafe_allow_html=True)
