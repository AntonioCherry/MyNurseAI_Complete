# MyNurseAI
**MyNurseAI** è una piattaforma web progettata per favorire il collegamento e l’interazione
tra pazienti e medici.
Attraverso una gestione centralizzata dei propri assistiti, ogni medico ha la possibilità di
caricare sulla piattaforma qualsiasi documento o referto medico utile per ciascun paziente.
A sua volta, il paziente può consultare e scaricare in autonomia i propri documenti,
mantenendoli sempre a disposizione in formato digitale.
L’elemento distintivo della piattaforma è la presenza di un infermiere digitale, disponibile
24 ore su 24 e 7 giorni su 7. Grazie all’integrazione di un’architettura RAG
(**Retrieval-Augmented Generation**) e alla gestione personalizzata dei documenti medici, il
chatbot è in grado di rispondere a domande di carattere medico-sanitario basandosi sulle
informazioni specifiche del singolo paziente, come malattie, terapie e referti caricati dal
proprio medico.

## Features Generiche
- <img width="15" height="15" alt="immagine" src="https://github.com/user-attachments/assets/4f86ac52-77ba-492d-81a7-be2b8edf2a4d" /> Upload di referti medici e terapie. 
- <img width="15" height="15" alt="immagine" src="https://github.com/user-attachments/assets/827279fd-4db0-4413-9643-522a97917107" /> Chatbot che sfrutta la knowledge base.

## Features di sicurezza per Upload
- 🧠 Classificatore LLM dei documenti per verificarne la pertinenza
- 🔐 Rilevamento presenz adi artefatti sospetti nel documento, nonchè riferimenti prompt injection indirette e jailbreak
## Features di sicurezza per Chatbot
- <img width="15" height="15" alt="immagine" src="https://github.com/user-attachments/assets/b669d234-2c7b-44be-a9ab-a2aa505804d5" /> Individuazione dei pazienti nell'input utente.
- 🔐 Sanificazione dell'input e controllo presenza artefatti sospetti al suo interno.
- 🧠 Classificatore LLM che giudica l'input in base alla possibile presenza di riferimenti ad possibili attacchi.
- 🧠 Classificatore LLM che giudica l'input in base alla possibile presenza di riferimenti a terapie o dosaggi di farmaci.
- <img width="15" height="15" alt="immagine" src="https://github.com/user-attachments/assets/362ba0b6-6842-43a2-bd7a-7c0cee57c481" /> Oscuramento di ogni possibile dato sensibile protetto da privacy presente nell'input e nell'output generato.

## Requisiti
- Python 3.12+
- Ollama installato e in esecuzione
- Modello della suite Ollama:`llama-guard3:1b` installato
- Modello della suite Ollama:`Mistral:7b` installato
- Modello della suite Ollama:`medllama2` installato

## Installazione
```bash
git clone (https://github.com/AntonioCherry/MyNurseAI_Complete.git)
cd MyNurseAI_Complete
python -m venv .venv
venv\Scripts\activate
pip install -r requirements.txt

Nota bene: nel requirements.txt sono presenti dei pacchetti molto pesanti che potrebbero richiedere molto tempo.
