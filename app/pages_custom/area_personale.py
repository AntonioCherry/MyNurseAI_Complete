import streamlit as st
from app.components.sidebar import sidebar
from app.pages_custom.show_pazienti import show_pazienti


def area_personale(user, db):
    # --- Protezione accesso ---
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        st.warning("⚠️ Devi prima effettuare il login.")
        st.stop()

    sidebar(user)

    # --- CONTENUTO PRINCIPALE ---
    if st.session_state.current_page == "area_personale":
        st.title("🏠 Area Personale")
        st.markdown("""
        Benvenuto nella tua area personale.  
        Qui puoi visualizzare e gestire le informazioni legate al tuo profilo.
        """)
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**👤 Username:** {user.username}")
            st.write(f"**📧 Email:** {user.email}")
            st.write(f"**🎂 Data di nascita:** {user.data_nascita}")
            st.write(f"**🚻 Sesso:** {user.sesso}")
        with col2:
            st.write(f"**🏠 Indirizzo:** {user.via} {user.numero_civico}")
            st.write(f"**🏙️ Città:** {user.citta}")
            st.write(f"**📮 CAP:** {user.cap}")
            st.write(f"**💼 Ruolo:** {user.role}")

    elif st.session_state.current_page == "show_pazienti":
        # ✅ Mostra la pagina dei pazienti all’interno dell’area personale
        show_pazienti(db, user)
