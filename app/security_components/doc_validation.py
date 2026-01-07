import re
import math, json
import io
import subprocess
from PyPDF2 import PdfReader
from typing import Tuple, List
from statistics import mean

def chunk_text(text: str, max_chunk_length: int = 1500) -> List[str]:
    """Divide il testo in chunk di lunghezza max_chunk_length (in parole)"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_chunk_length):
        chunk = " ".join(words[i:i+max_chunk_length])
        chunks.append(chunk)
    return chunks

def classify_chunk_with_ollama(text_chunk: str) -> Tuple[bool, str, float, str]:
    """Classifica un singolo chunk usando Ollama/Mistral e JSON output"""
    prompt = f"""
        Sei un classificatore di documenti clinici. Determina se il testo è MEDICO o NON_MEDICO.
        Classifica come MEDICO solo se il documento ha scopo clinico principale.
         Non classificare come MEDICO documenti su altri argomenti che usano scenari medici come esempio oppure che fanno
         riferimento a termini medico-sanitari solo in alcune porzioni del documento.
        Rispondi SOLO in JSON valido:
        {{"label":"MEDICO" o "NON_MEDICO", "confidence":0-1, "reason":"spiegazione breve"}}
        
        Testo:
        {text_chunk}
        """
    try:
        result = subprocess.run(
            ["ollama", "run", "mistral"],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode())

        raw_output = result.stdout.decode().strip()

        # parsing JSON
        parsed = None
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = parsed[0]
        except Exception:
            m = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
            if m:
                parsed = json.loads(m.group(0))

        if parsed is None:
            return False, "non medico", 0.0, "Parsing JSON fallito"

        label = str(parsed.get("label", "")).upper()
        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "")

        print(f"Chunk classificato come {label} con confidence {confidence:.2f}, reason: {reason}")

        if label == "MEDICO":
            return True, "medico", confidence, reason
        else:
            return False, "non medico", confidence, reason

    except Exception as e:
        print("⚠️ Errore classificazione chunk:", e)
        return False, "errore Ollama", 0.0, str(e)

def classify_with_chunks(text: str, chunk_size: int = 1500) -> Tuple[bool, str, float]:
    """
    Classifica un documento lungo suddividendolo in chunk.
    Ritorna la classificazione finale basata su majority voting.
    """
    chunks = chunk_text(text, max_chunk_length=chunk_size)
    results = []

    print(f"\nDocumento diviso in {len(chunks)} chunk")

    for i, chunk in enumerate(chunks, start=1):
        print(f"\n=== Chunk {i} ===")
        is_medical, label, confidence, reason = classify_chunk_with_ollama(chunk)
        results.append((is_medical, label, confidence, reason))

    # majority voting sulle etichette
    medico_count = sum(1 for r in results if r[0])
    non_medico_count = len(results) - medico_count

    if medico_count >= non_medico_count:
        conf = sum(r[2] for r in results if r[0]) / max(medico_count, 1)
        print(f"\n=== DOCUMENTO FINALE ===\nClassificato come MEDICO, confidence media: {conf:.2f}")
        return True, "medico", conf
    else:
        conf = sum(r[2] for r in results if not r[0]) / max(non_medico_count, 1)
        print(f"\n=== DOCUMENTO FINALE ===\nClassificato come NON_MEDICO, confidence media: {conf:.2f}")
        return False, "non medico", conf

def shannon_entropy(s: str) -> float:
    """Calcola entropia per identificare testo codificato o nascosto."""
    if not s:
        return 0.0
    prob = [float(s.count(c)) / len(s) for c in dict.fromkeys(s)]
    return -sum(p * math.log(p, 2) for p in prob)


def check_pdf_structure(pdf_bytes: bytes) -> tuple[bool, str]:
    """Controlla che il PDF non contenga oggetti sospetti."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            raw = page.extract_text() or ""
            if re.search(r"(?i)(<script|javascript:|eval\(|base64,|import )", raw):
                return False, "Trovato contenuto sospetto o codice embedded nel PDF."
        return True, ""
    except Exception as e:
        return False, f"Errore nella lettura del PDF: {e}"


def validate_pdf_content(pdf_bytes: bytes) -> tuple[bool, str]:
    """
    Analizza il contenuto del PDF per individuare testo sospetto o codificato.
    """
    def alpha_ratio(s: str) -> float:
        """Percentuale di lettere in una stringa."""
        if not s:
            return 0.0
        letters = len(re.findall(r"[A-Za-z]", s))
        return letters / max(1, len(s))

    errors = []
    suspicion_score = 0.0
    SCORE_THRESHOLD = 2.2

    # --- estrazione testo grezzo ---
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_texts = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages_texts)



    # --- controllo base sulla lunghezza ---
    if len(text.strip()) < 300:
        errors.append("Documento troppo breve o privo di testo leggibile.\n")
        suspicion_score += 0.6

    # --- controllo struttura ---
    struct_ok, struct_msg = check_pdf_structure(pdf_bytes)
    if not struct_ok:
        errors.append(struct_msg)
        suspicion_score += 0.9

    # --- normalizzazione ---
    alnum = re.sub(r"[^A-Za-z0-9+/=]", "", text)

    # --- rilevamento Base64 ---
    base64_matches = list(re.finditer(r"(?:[A-Za-z0-9+/]{80,}={0,2})", alnum))
    base64_flag = False
    for m in base64_matches:
        chunk = m.group(0)
        if shannon_entropy(chunk) > 4.5:
            base64_flag = True
            break
    if base64_flag:
        errors.append("Pattern compatibile con Base64 o testo codificato rilevato.\n")
        suspicion_score += 1.0

    # --- entropia ---
    try:
        chunks = [text[i:i+200] for i in range(0, len(text), 200)]
        entropy_vals = [shannon_entropy(c) for c in chunks if len(c) > 50]
        avg_entropy = mean(entropy_vals) if entropy_vals else 0
        entropy_total = shannon_entropy(re.sub(r"\s+", "", text)) if text.strip() else 0
    except Exception:
        avg_entropy = entropy_total = 0

    if avg_entropy > 5.5 or entropy_total > 5.5:
        errors.append("Entropia elevata: possibile testo codificato o anomalo.\n")
        suspicion_score += 1.0

    # --- rilevamento linee di codice ---
    code_like_lines = 0
    for line in text.splitlines():
        line_stripped = line.strip()

        # ignora linee corte o quasi vuote
        if len(line_stripped) < 10:
            continue

        # ignora linee con densità alfabetica troppo bassa (probabile numero o tabella)
        if alpha_ratio(line_stripped) < 0.35:
            continue

        # ignora linee tipiche dei referti (es. valori, unità di misura)
        if re.search(
                r"\b(g\/dl|mmol\/l|mg\/dl|u\/l||valori|esame|referto|diagnosi|terapia|farmacologica|farmaco|controllo)\b",
                line_stripped, re.IGNORECASE):
            continue

        # considera "code-like" solo se contiene più pattern di codice insieme
        symbol_count = len(re.findall(r"[{}<>;=()/\\]", line_stripped))
        keyword_hits = len(re.findall(r"\b(import|def|class|printf|var|function)\b", line_stripped, re.IGNORECASE))

        if symbol_count >= 3 or keyword_hits >= 1:
            code_like_lines += 1

    # aumenta la soglia per ridurre falsi positivi
    if code_like_lines > 15:
        errors.append(f"Rilevate {code_like_lines} righe con pattern simili a codice.\n")
        suspicion_score += 0.5

    # --- controllo LLM ---
    if suspicion_score < 1.6:
        valid, label, conf = classify_with_chunks(text)
        if not valid:
            errors.append("Il documento non appare medico.")
            suspicion_score += 0.6
    else:
        try:
            valid, label, conf = classify_with_chunks(text)
            if not valid:
                errors.append("Il documento non appare medico.")
                suspicion_score += 0.4
        except Exception:
            errors.append("Errore durante la classification LLM.")

    # --- decisione finale ---
    if suspicion_score >= SCORE_THRESHOLD or errors:
        return False, "; ".join(errors) if errors else "Documento sospetto."
    return True, ""

