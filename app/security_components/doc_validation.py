import re
import math
import json
import io
import subprocess
from PyPDF2 import PdfReader
from typing import Tuple, List

def chunk_text(text: str, max_chunk_length: int = 1500) -> List[str]:
    """
    Divide il testo in chunk di lunghezza max_chunk_length (in parole)
    :param text: testo sui cui fare il chunking
    :param max_chunk_length: lunghezza massima di ogni chunk
    :return: chunk individuati
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_chunk_length):
        chunk = " ".join(words[i:i + max_chunk_length])
        chunks.append(chunk)

    return chunks


def classify_chunk_with_ollama(text_chunk: str) -> Tuple[bool, str, float, str]:
    """
    Classifica un singolo chunk usando Ollama / Mistral con output JSON
    :param text_chunk: chunk da classificare
    :return: True/false, classificazione("medico" o "non medico"), confidence score e reason (spiegazione breve)
    """
    prompt = f"""
Sei un classificatore di documenti clinici.
Determina se il testo è MEDICO o NON_MEDICO.

Classifica come MEDICO solo se il documento ha scopo clinico principale.
Non classificare come MEDICO documenti che usano scenari medici come esempio
o che contengono solo riferimenti parziali a termini medico-sanitari.

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

        # Parsing JSON
        parsed = None
        try:
            parsed = json.loads(raw_output)
            if isinstance(parsed, list) and parsed:
                parsed = parsed[0]
        except Exception:
            match = re.search(r"\{.*\}", raw_output, flags=re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))

        if parsed is None:
            return False, "non medico", 0.0, "Parsing JSON fallito"

        label = str(parsed.get("label", "")).upper()
        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "")

        print(
            f"Chunk classificato come {label} "
            f"con confidence {confidence:.2f}, reason: {reason}"
        )

        if label == "MEDICO":
            return True, "medico", confidence, reason

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
        results.append(classify_chunk_with_ollama(chunk))

    medico_count = sum(1 for r in results if r[0])
    non_medico_count = len(results) - medico_count

    if medico_count >= non_medico_count:
        conf = sum(r[2] for r in results if r[0]) / max(medico_count, 1)
        print(
            f"\n=== DOCUMENTO FINALE ===\n"
            f"Classificato come MEDICO, confidence media: {conf:.2f}"
        )
        return True, "medico", conf

    conf = sum(r[2] for r in results if not r[0]) / max(non_medico_count, 1)
    print(
        f"\n=== DOCUMENTO FINALE ===\n"
        f"Classificato come NON_MEDICO, confidence media: {conf:.2f}"
    )
    return False, "non medico", conf


def shannon_entropy(s: str) -> float:
    """
    Calcola entropia per identificare testo codificato o nascosto
    :param s: stringa su cui calcolare l'entropia
    """
    if not s:
        return 0.0

    prob = [float(s.count(c)) / len(s) for c in dict.fromkeys(s)]
    return -sum(p * math.log(p, 2) for p in prob)


def check_pdf_structure(pdf_bytes: bytes) -> tuple[bool, str]:
    """
    Controlla che il PDF non contenga oggetti sospetti
    :param pdf_bytes: pdf da verificare
    """
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
    Analizza il contenuto del PDF per individuare testo sospetto o codificato
    :param pdf_bytes: pdf da verificare
    :return True/False
    """

    def alpha_ratio(s: str) -> float:
        if not s:
            return 0.0
        letters = len(re.findall(r"[A-Za-z]", s))
        return letters / max(1, len(s))

    errors = []
    suspicion_score = 0.0
    SCORE_THRESHOLD = 2.2

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if len(text.strip()) < 300:
        errors.append("Documento troppo breve o privo di testo leggibile.")
        suspicion_score += 0.6

    struct_ok, struct_msg = check_pdf_structure(pdf_bytes)
    if not struct_ok:
        errors.append(struct_msg)
        suspicion_score += 0.9

    if suspicion_score < 1.6:
        valid, _, _ = classify_with_chunks(text)
        if not valid:
            errors.append("Il documento non appare medico.")
            suspicion_score += 0.6

    if suspicion_score >= SCORE_THRESHOLD or errors:
        return False, "; ".join(errors)

    return True, ""
