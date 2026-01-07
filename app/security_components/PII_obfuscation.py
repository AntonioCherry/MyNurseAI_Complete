from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

# Inizializza i motori
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# --- Riconoscitori custom ---

# Codice Fiscale (Italia)
cf_pattern = Pattern(
    "CodiceFiscale",
    r"\b([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])\b",
    0.8)
cf_recognizer = PatternRecognizer(supported_entity="IT_TAX_CODE", patterns=[cf_pattern])

# Carta di credito
cc_pattern = Pattern("CreditCard", r"\b(?:\d[ -]*?){13,16}\b", 0.85)
cc_recognizer = PatternRecognizer(supported_entity="CREDIT_CARD", patterns=[cc_pattern])

# Numero di telefono (italiano o internazionale)
phone_pattern = Pattern(
    "PhoneNumber",
    r"(?:(?:\+?39)?\s?)?(?:3\d{2}|0\d{1,3})[\s./-]?\d{5,8}\b",
    0.85
)
phone_recognizer = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern])

# Indirizzi di casa (parole chiave tipiche italiane)
home_address_pattern = Pattern(
    "HomeAddress",
    r"\b(?:Via|Viale|Piazza|Corso|Largo|Strada|Contrada)\s+[A-Z][a-zàèéìòù’'\- ]+\s*(?:\d{1,3})?\b",
    0.75
)
home_address_recognizer = PatternRecognizer(supported_entity="HOME_ADDRESS", patterns=[home_address_pattern])

iban_pattern = Pattern(
    "IBAN_Tolerant",
    # country + check digits poi sequenza di gruppi che possono contenere lettere, cifre o placeholder
    r"\b[A-Z]{2}\d{2}(?:[A-Z0-9\[\]\(\)\s\-/]{4,}){3,}\b",
    0.75
)
iban_recognizer = PatternRecognizer(supported_entity="IBAN", patterns=[iban_pattern])

# Numero di passaporto (formato EU)
passport_pattern = Pattern(
    "Passport",
    r"\b[A-Z]{2}\d{6,9}\b",
    0.8
)
passport_recognizer = PatternRecognizer(supported_entity="PASSPORT", patterns=[passport_pattern])

# Numero di patente (formato italiano semplificato)
license_pattern = Pattern(
    "DrivingLicense",
    r"\b[A-Z]{1,2}\d{5,10}\b",
    0.7
)
license_recognizer = PatternRecognizer(supported_entity="DRIVING_LICENSE", patterns=[license_pattern])

# Email
email_pattern = Pattern(
    "EmailAddress",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    0.9
)
email_recognizer = PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[email_pattern])

# Password o segreti (keyword + simboli)
password_pattern = Pattern(
    "PasswordKeyword",
    r"(?i)\b(?:password|pwd|pass|pw|passphrase)\b[:=\s]*([^\s,;.:()]{6,})",
    0.95
)
password_recognizer = PatternRecognizer(supported_entity="AUTH_SECRET", patterns=[password_pattern])

# Pattern entropy-ish standalone (almeno 6 char, almeno una lettera, una cifra e un simbolo)
password_entropy_pattern = Pattern(
    "PasswordEntropyRobust",
    r'(?<!\w)(?=.{6,})(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9])[A-Za-z\d[^A-Za-z0-9]]{6,}\b',
    0.90
)
password_entropy_recognizer = PatternRecognizer(
    supported_entity="AUTH_SECRET",
    patterns=[password_entropy_pattern]
)

cvv_pattern = Pattern(
    "CardSecurityCode",
    r"(?i)\b(?:cvv|cvc|codice[ ]di[ ]sicurezza|codice[ ]a[ ]tre[ ]cifre|codice[ ]a[ ]3[ ]cifre|security[ ]code|codice)\b[^\d]{0,6}(\d{3,4})\b",
    0.97
)
cvv_recognizer = PatternRecognizer(
    supported_entity="CREDIT_CARD_SECURITY_CODE",
    patterns=[cvv_pattern]
)

# --- Expiry (scadenza carta) rilevata in contesto ---
expiry_pattern = Pattern(
    "CardExpiry",
    r"(?i)\b(?:scad(?:enza)?|exp|expiry|valid(?:\s*thru)?)\b.{0,20}?([0-3]?\d[/\-][0-9]{2,4})\b",
    0.95
)
expiry_recognizer = PatternRecognizer(
    supported_entity="CREDIT_CARD_EXPIRY",
    patterns=[expiry_pattern]
)


# --- Registra ---
custom_recognizers = [
    cf_recognizer,
    cc_recognizer,
    phone_recognizer,
    home_address_recognizer,
    iban_recognizer,
    passport_recognizer,
    license_recognizer,
    email_recognizer,
    password_recognizer,
    expiry_recognizer,
    cvv_recognizer
]
for rec in custom_recognizers:
    analyzer.registry.add_recognizer(rec)

# --- Funzione principale ---
def obscure_pii(text: str) -> str:
    # Analizza il testo (usa 'en' per compatibilità, regex sono linguisticamente indipendenti)
    results = analyzer.analyze(text=text, language="en")

    # Entità considerate sensibili
    sensitive_entities = {
        "CREDIT_CARD",
        "IT_TAX_CODE",
        "PHONE_NUMBER",
        "HOME_ADDRESS",
        "EMAIL_ADDRESS",
        "IBAN",
        "PASSPORT",
        "DRIVING_LICENSE",
        "AUTH_SECRET",
        "CREDIT_CARD_SECURITY_CODE",
        "CREDIT_CARD_EXPIRY"
    }

    # Filtra solo le entità da oscurare
    filtered = [r for r in results if r.entity_type in sensitive_entities]

    # Esegui l'anonimizzazione
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=filtered,
        operators={
            "DEFAULT": OperatorConfig("replace", {"new_value": "[DATI PERSONALI RIMOSSI]"})
        }
    )

    return anonymized.text
