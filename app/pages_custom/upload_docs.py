import streamlit as st
from app.components.sidebar import sidebar
import io
import os
from PyPDF2 import PdfReader
from app.models.doc import Doc

# Import corretto in base alla versione di LangChain
try:
    from langchain.text_splitters import CharacterTextSplitter
except ModuleNotFoundError:
    from langchain.text_splitter import CharacterTextSplitter

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.security_components.doc_validation import validate_pdf_content


def upload_docs(db, user):
    sidebar(user)

    # --- Controllo paziente selezionato ---
    if "selected_paziente" not in st.session_state or st.session_state.selected_paziente is None:
        st.warning("⚠️ Nessun paziente selezionato")
        return

    p = st.session_state.selected_paziente
    st.title(f"📄 Documenti di {p.nome} {p.cognome}")

    # --- Flag upload per paziente ---
    patient_flag_key = f"file_uploaded_{p.email}"
    if patient_flag_key not in st.session_state:
        st.session_state[patient_flag_key] = False

    # --- Cartella paziente per ChromaDB ---
    persist_dir = os.path.join("chroma_db", p.email)
    os.makedirs(persist_dir, exist_ok=True)

    # --- Carica o crea vectorstore ---
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        encode_kwargs={"normalize_embeddings": True}
    )

    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="docs"
    )

    # --- Upload PDF ---
    uploaded_file = st.file_uploader("Carica un nuovo documento", type=["pdf"])
    if uploaded_file is not None:
        processing_key = f"upload_processing_{p.email}"
        if processing_key not in st.session_state:
            st.session_state[processing_key] = False

        if st.session_state[processing_key]:
            st.info("Elaborazione in corso, attendere...")
            return

        st.session_state[processing_key] = True
        try:
            file_bytes = uploaded_file.read()

            # --- VALIDAZIONE PDF ---
            valid, message = validate_pdf_content(file_bytes)
            if not valid:
                st.error(f"Upload rifiutato: {message}")
                st.session_state[processing_key] = False
                return

            # Salva su PostgreSQL
            new_doc = Doc(
                filename=uploaded_file.name,
                paziente_email=p.email,
                file_data=file_bytes
            )
            db.add(new_doc)
            db.commit()
            st.success(f"Documento '{uploaded_file.name}' caricato con successo!")

            # Salva su ChromaDB
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                text = "".join([page.extract_text() or "" for page in reader.pages])

                text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                chunks = text_splitter.split_text(text)

                if chunks:
                    vectorstore.add_texts(texts=chunks)
                    vectorstore.persist()
                    st.success(f"Documento '{uploaded_file.name}' indicizzato su ChromaDB!")
                else:
                    st.warning("Il PDF non contiene testo estraibile per l'indicizzazione.")

            except Exception as e:
                st.error(f"Errore durante il salvataggio su ChromaDB: {e}")

        except Exception as e:
            st.error(f"Errore durante l'upload: {e}")

        finally:
            st.session_state[processing_key] = False

    # --- Lista documenti ---
    docs = db.query(Doc).filter(Doc.paziente_email == p.email).all()
    if not docs:
        st.info("Non ci sono documenti caricati per questo paziente.")
        return

    st.markdown("### Documenti caricati:")

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
