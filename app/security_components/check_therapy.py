from ollama import chat


def is_therapy_related(text: str) -> bool:
    few_shot_prompt = f"""
    Sei un assistente clinico. Devi stabilire se il testo fornito
    contiene riferimenti a TERAPIE, TRATTAMENTI o FARMACI.

    Classifica ogni testo come:
    - "TERAPIA" se contiene riferimenti a cure, farmaci, dosaggi, prescrizioni o trattamenti.
    - "NON_TERAPIA" se parla solo di diagnosi, sintomi, controlli o referti generici.

    Ora classifica il seguente testo:
    "{text}"

    Rispondi SOLO con "TERAPIA" o "NON_TERAPIA".
    """

    resp = chat(
        model="medllama2",
        messages=[{"role": "user", "content": few_shot_prompt}],
        stream=False
    )

    output = resp["message"]["content"].strip().lower()
    return "terapia" in output and "non" not in output

