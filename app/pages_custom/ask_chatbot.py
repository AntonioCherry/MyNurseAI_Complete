import streamlit as st
import os, difflib
import ollama
from ollama import chat
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy.orm import Session
from app.components.sidebar import sidebar
from app.models.user import User
from app.security_components.check_therapy import is_therapy_related
from app.security_components.PII_obfuscation import obscure_pii
from app.security_components.prompt_sanitizer import sanitize_user_prompt
from app.config import OLLAMA_BASE_URL


ollama.base_url =  OLLAMA_BASE_URL
class OllamaWrapper:
    """
    Wrapper per l'uso di un modello Ollama tramite un'interfaccia callable.

    Questa classe incapsula una chiamata al modello Ollama e restituisce
    l'output in un formato compatibile con pipeline di generazione testo.
    """

    def __init__(self, model_name: str):
        """
        Inizializza il wrapper con il nome del modello.

        Args:
            model_name (str): nome del modello Ollama da utilizzare
        """
        self.model_name = model_name

    def __call__(self, prompt: str) -> list[dict]:
        """
        Esegue una richiesta al modello usando il prompt fornito.

        Args:
            prompt (str): testo di input da inviare al modello

        Returns:
            list[dict]: lista contenente un dizionario con la chiave
            'generated_text' e il testo generato dal modello
        """
        resp = chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return [{"generated_text": resp["message"]["content"]}]

    def reset(self) -> None:
        """
        Reset dello stato interno del wrapper.

        Attualmente non mantiene stato, quindi il metodo è un placeholder.
        """
        pass

@st.cache_resource
def load_model():
    """
    Carica il modello specifico da Ollama
    :return: istanza di OllamaWrapper configurata con il modello "mistral"
    """
    return OllamaWrapper(model_name="mistral")


def load_vectorstore(email_paziente):
    """
    Funzione che carica il vector store specifico di un paziente, così da poterne ricavare poi il contesto
    :param email_paziente: email del paziente di cui si vuole caricare il vectorstore
    :return: il vectorstore specifico per il paziente richiesto
    """
    persist_dir = os.path.join("chroma_db", email_paziente)
    if not os.path.exists(persist_dir):
        return None
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        encode_kwargs={"normalize_embeddings": True}
    )
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name="docs"
    )
    return vectorstore


def get_pazienti_del_medico(email_medico: str, db: Session):
    """
    Funzione che sulla base dell'email del medico ricerca e restituisce nel db relazionale tutti i pazienti a lui associato
    :param email_medico: emaail del medico di cui si vogliono ricercare i pazienti
    :param db: istanza del bd relazionale
    :return: lista dei pazienti
    """
    return db.query(User).filter(User.medicoAssociato == email_medico).all()


def build_rag_prompt(query, retrieved_docs, pazienti_coinvolti=None, contains_therapy: bool = False):
    """

    :param query: query utente
    :param retrieved_docs: documenti recuperati in fase di retrival
    :param pazienti_coinvolti: pazienti coinvolti nella query
    :param contains_therapy: presenza terapie nei documenti
    :return: prompt utilizzabile dal chatbot per generare una risposta
    """
    context = "\n\n".join(retrieved_docs) if retrieved_docs else "(Nessun documento rilevante trovato.)"
    patient_info = f"\nPazienti coinvolti: {pazienti_coinvolti}." if pazienti_coinvolti else ""

    if contains_therapy:
        therapy_instruction = (
            "Nei documenti forniti ci sono informazioni su terapie o trattamenti. "
            "Se rispondi citando una terapia, riporta esclusivamente quanto presente nei documenti "
            "e indica chiaramente la fonte o il referto da cui proviene l'informazione."
        )
    else:
        therapy_instruction = (
            "ATTENZIONE: nei documenti forniti non risultano informazioni su terapie o farmaci. "
            "Non proporre né inventare terapie, farmaci, dosaggi o prescrizioni. "
            "Limita la risposta a informazioni diagnostiche, descrittive o di follow-up presenti nel contesto."
        )

    prompt = f"""
            Sei un infermiere virtuale che assiste un medico. Rispondi in modo chiaro, professionale e conservativo.
            {patient_info}

            {therapy_instruction}

            Contesto (da usare esclusivamente per rispondere; non aggiungere informazioni esterne):
            {context}

            Domanda del medico/paziente:
            {query}

            Istruzioni di formato:
            - Rispondi solo con informazioni presenti nel contesto.
            - Se non trovi informazioni pertinenti, rispondi esplicitando che nei documenti non sono presenti dati utili.
            - Non includere consigli farmacologici o terapie se non esplicitamente presenti nei documenti.
            - Se citi parti dei documenti, indica brevemente la loro fonte (es. "Da referto del DD/MM/YYYY").

            Risposta:
"""
    return prompt


def identify_multiple_pazienti_in_query(query, pazienti):
    """
    Funzione che ha lo scopo di identificare quanti più pazienti in una query utente
    :param query: query utente
    :param pazienti: pazienti individuati nella query
    :return: lista pazienti individuati
    """
    query_lower = query.lower()
    found = []

    for p in pazienti:
        fullname = f"{p.nome.lower()} {p.cognome.lower()}"
        if fullname in query_lower:
            found.append(p)

    # Fuzzy search aggiuntiva
    if not found:
        names = [f"{p.nome.lower()} {p.cognome.lower()}" for p in pazienti]
        match = difflib.get_close_matches(query_lower, names, n=2, cutoff=0.6)
        for m in match:
            for p in pazienti:
                if f"{p.nome.lower()} {p.cognome.lower()}" == m:
                    found.append(p)

    return list(set(found))


def extract_clinical_event(query: str):
    """
    Estrae le keyword cliniche principali dalla query, invece di tutta la frase.
    :param query utente
    :return: lista di keywork o eventi clinici
    """
    q = query.lower()
    keywords = ["visita", "controllo", "referto", "esame", "ecografia", "analisi", "terapia", "farmacologica",
                "farmaco"]

    events = []
    for word in keywords:
        if word in q:
            events.append(word)
    return events if events else None


def ask_chatbot(db, user):
    """
    Funzione che gestisce la logica di interrogazione del chatbot della piattaforma.
    :param db: istanza del bd relazionale
    :param user: utente che ha effettuato l'accesso alla piattaforma
    """
    sidebar(user)

    st.title("💬 Chat con il tuo infermiere virtuale")

    chatbot = load_model()

    if user.role == "Medico":
        pazienti = get_pazienti_del_medico(user.email, db)
    else:
        pazienti = [user]

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for role, msg in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"🧑‍⚕️ **Tu:** {msg}")
        else:
            st.markdown(f"🤖 **MyNurseAI:** {msg}")

    user_input = st.text_input("Scrivi la tua domanda:", value="", key="chat_input")

    if st.button("💬 Invia"):
        if not user_input.strip():
            st.warning("Inserisci un messaggio prima di inviare.")
            return

        processed_input = obscure_pii(user_input)
        sanitized_input = sanitize_user_prompt(processed_input)

        if user.role == "Paziente":
            if sanitized_input == "error":
                st.session_state.chat_history.append(("user", user_input))
                response = "⚠️ Il messaggio contiene istruzioni non consentite o sospette. Riformula la domanda."
                st.session_state.chat_history.append(("bot", response))
                return

        if sanitized_input == "warning":
            st.warning("⚠️ Il messaggio potrebbe contenere contenuti sospetti. Procedi con cautela.")

        # continua con la generazione della risposta usando sanitized_input
        st.session_state.chat_history.append(("user", processed_input))

        with st.spinner("L'infermiere sta cercando nei documenti..."):
            response = None

            if user.role == "Medico":
                selected_pazienti = identify_multiple_pazienti_in_query(processed_input, pazienti)

                if not selected_pazienti:
                    response = (
                        "Non ho trovato riferimenti chiari a pazienti tra i tuoi assistiti. "
                        "Specificami il nome completo del paziente o dei pazienti a cui ti riferisci."
                    )
                    st.session_state.chat_history.append(("bot", response))
                    return

                all_docs = []
                pazienti_con_vectorstore = []

                for p in selected_pazienti:
                    vs = load_vectorstore(p.email)
                    if vs is None:
                        continue

                    pazienti_con_vectorstore.append(p)
                    retriever = vs.as_retriever(search_kwargs={"k": 3})
                    docs = retriever.invoke(sanitized_input)
                    all_docs.extend(docs)

                if not pazienti_con_vectorstore:
                    response = "Non ho trovato documenti clinici per nessuno dei pazienti menzionati."
                    st.session_state.chat_history.append(("bot", response))
                    return

                retrieved_texts = [d.page_content for d in all_docs]
                context = "\n\n".join(retrieved_texts)

                contains_therapy = is_therapy_related(context)

                event_requested = extract_clinical_event(processed_input)

                if event_requested:
                    found_in_context = any(any(ev in doc.lower() for ev in event_requested) for doc in retrieved_texts)

                    if not found_in_context:
                        response = (
                            f"📄 Nei documenti disponibili non risultano informazioni relative a '{event_requested}'. "
                            "Non posso fornirti dettagli su questo evento clinico."
                        )
                        st.session_state.chat_history.append(("bot", response))
                        st.rerun()
                        return

                pazienti_nomi = ", ".join([f"{p.nome} {p.cognome}" for p in pazienti_con_vectorstore])
                rag_prompt = build_rag_prompt(processed_input,
                                              retrieved_texts,
                                              pazienti_coinvolti=pazienti_nomi,
                                              contains_therapy=contains_therapy)

                raw_response = chatbot(rag_prompt)[0]["generated_text"]
                response = obscure_pii(raw_response)

                query_is_therapy = is_therapy_related(sanitized_input)

                if query_is_therapy and not contains_therapy:
                    response = (
                        "⚠️ Nei documenti recuperati non sono presenti indicazioni terapeutiche. "
                        "Posso fornirti solo informazioni cliniche generali, non terapie."
                    )

            else:  # Se paziente
                paziente_email = user.email
                vectorstore = load_vectorstore(paziente_email)

                if vectorstore is None:
                    response = "Non ho trovato informazioni nei tuoi documenti."
                else:
                    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                    docs = retriever.invoke(processed_input)
                    retrieved_texts = [d.page_content for d in docs]
                    context = "\n\n".join(retrieved_texts)
                    contains_therapy = is_therapy_related(context)

                    event_requested = extract_clinical_event(processed_input)
                    if event_requested:
                        found_in_context = any(
                            event in doc.lower() for event in event_requested for doc in retrieved_texts)
                        if not found_in_context:
                            response = (
                                f"📄 Nei documenti presenti non risultano informazioni relative a '{event_requested}'. "
                                "Non posso fornirti dettagli su questo evento clinico."
                            )
                            st.session_state.chat_history.append(("bot", response))
                            st.rerun()
                            return

                    if not retrieved_texts:
                        response = "Non ho trovato informazioni utili nei tuoi documenti per rispondere alla domanda."
                    else:
                        rag_prompt = build_rag_prompt(processed_input, retrieved_texts,
                                                      contains_therapy=contains_therapy)
                        raw_response = chatbot(rag_prompt)[0]["generated_text"]
                        response = obscure_pii(raw_response)
                        query_is_therapy = is_therapy_related(processed_input)
                        if query_is_therapy and not contains_therapy:
                            response = (
                                "⚠️ Nei documenti consultati non sono presenti indicazioni terapeutiche. "
                                "Posso riportare solo informazioni cliniche generali relative al caso, "
                                "ma non dettagli su trattamenti o farmaci."
                            )

        st.session_state.chat_history.append(("bot", response))
        st.rerun()
