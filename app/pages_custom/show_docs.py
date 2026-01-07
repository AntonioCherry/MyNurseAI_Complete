import streamlit as st
from app.components.sidebar import sidebar
from app.models.doc import Doc

def show_docs(db, user):
    sidebar(user)

    st.title(f"📄 Documenti di {user.nome} {user.cognome}")

    # --- Lista documenti ---
    docs = db.query(Doc).filter(Doc.paziente_email == user.email).all()
    if not docs:
        st.info("Non ci sono documenti caricati per questo paziente.")
        return

    st.markdown("### 📂 Documenti caricati:")

    for d in docs:
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{d.filename}**")
        with cols[1]:
            st.download_button(
                label="📥 Scarica",
                data=d.file_data,
                file_name=d.filename,
                mime="application/pdf",
                key=f"download_{d.id}"
            )
        st.markdown("<div style='margin:2px 0;border-bottom:1px solid #ddd;'></div>", unsafe_allow_html=True)
