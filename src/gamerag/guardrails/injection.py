"""Guardrails de seguridad: inyección de prompts, información sensible (PII/secretos) y fuga del prompt.

Cuatro controles, todos deterministas (sin LLM, sin costo, auditables) y con la interfaz de `base.py`:

- `InjectionGuard` (InputGuard): bloquea intentos de anular las instrucciones, extraer el prompt del sistema,
  secuestrar el rol, romper los delimitadores del contexto o saltarse el progreso/rol del jugador.
- `PIIGuard` (InputGuard): detecta correos, teléfonos, claves de API y similares. No bloquea la pregunta:
  entrega una versión **redactada** que es la que llega al recuperador y al LLM (minimización de datos).
- `QuarantineFilter` (AccessFilter): excluye del contexto los chunks del corpus que contienen instrucciones
  dirigidas a un modelo (inyección *indirecta* / envenenamiento de fuentes).
- `LeakGuard` (OutputGuard): rechaza respuestas que reproducen el prompt del sistema o contienen secretos.

Las heurísticas buscan *instrucciones dirigidas al asistente*, no palabras sueltas: "ignore the enemies" o
"act as bait" son preguntas de juego legítimas y no se bloquean (se mide la tasa de falsos positivos en
`evaluation/security.py` contra todos los bancos de preguntas reales).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from gamerag.guardrails.base import GuardResult
from gamerag.ingest.models import Chunk
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import Hit
from gamerag.schemas import Answer

_I = re.IGNORECASE

# (nombre, patrón). Cada patrón exige un verbo de orden + un objeto que solo tiene sentido para un asistente.
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("override_instructions", re.compile(
        r"\b(ignor[ae]|disregard|forget|override|bypass|olvida|ignora|omite|descarta|salt[ae]te)\b[^.?!\n]{0,40}"
        r"\b(previous|prior|above|earlier|all|any|your|the|these|those|anteriores?|previas?|todas?|tus|las|esas)\b"
        r"[^.?!\n]{0,25}\b(instructions?|rules?|prompts?|guidelines?|directives?|polic(?:y|ies)|restrictions?|"
        r"instrucciones|reglas|indicaciones|directrices|pol[ií]ticas?|restricciones)\b", _I)),
    ("reveal_system_prompt", re.compile(
        r"\b(reveal|show|print|display|repeat|output|leak|dump|tell me|muestra|revela|imprime|repite|dime|"
        r"cu[aá]les (?:son|eran))\b[^.?!\n]{0,40}\b(system|hidden|initial|original|secret|internal|tus|your|"
        r"del sistema|oculto|inicial)\b[^.?!\n]{0,20}"
        r"\b(prompt|instructions?|rules|message|instrucciones|reglas|mensaje)\b", _I)),
    ("role_hijack", re.compile(
        r"\b(you are now|from now on you are|act as|pretend (?:to be|you are)|roleplay as|ahora eres|"
        r"a partir de ahora eres|act[uú]a como|finge (?:ser|que eres))\b[^.?!\n]{0,60}"
        r"\b(dan|unrestricted|unfiltered|jailbr|no (?:rules|restrictions|limits)|developer mode|admin|root|"
        r"sin (?:reglas|restricciones|l[ií]mites)|modo desarrollador|administrador)\b", _I)),
    ("jailbreak_keywords", re.compile(
        r"\b(jailbreak|developer mode|do anything now|modo desarrollador|prompt injection)\b", _I)),
    ("delimiter_injection", re.compile(
        r"(</?\s*(?:document|context|system|instructions?)\s*>|<\|(?:im_start|im_end|system)\|>|"
        r"^\s*#{1,3}\s*(?:system|instructions?)\b|\[/?(?:INST|SYS)\]|```\s*system)", _I | re.MULTILINE)),
    ("bypass_access_controls", re.compile(
        r"\b(ignor[ae]|disregard|skip|bypass|ignora|omite|salt[ae]te|desactiva|disable)\b[^.?!\n]{0,20}"
        r"\b(my|mi|the|el|los|mis|all|todos?)\b[^.?!\n]{0,15}\b(progress|spoiler|gates?|filters?|progreso|"
        r"filtros?|restricci[oó]n|restricciones|protecci[oó]n)\w*|"
        r"\b(regardless of|no matter|sin importar|a pesar de|independientemente de)\b[^.?!\n]{0,20}"
        r"\b(progress|spoilers?|progreso)\b", _I)),
    ("claim_privileged_role", re.compile(
        r"\b(i am|i'm|soy|as an?|como)\b[^.?!\n]{0,15}\b(admin(?:istrator)?|administrador|developer|"
        r"desarrollador|root|the owner|el due[nñ]o)\b[^.?!\n]{0,40}\b(unlock|disable|override|show|reveal|give|"
        r"bypass|desbloque|desactiv|muestra|revela|da(?:me)?)", _I)),
    ("exfiltrate_secrets", re.compile(
        r"\b(api[ _-]?key|secret|password|credentials?|token|\.env|contrase[nñ]a|clave)\b[^.?!\n]{0,30}"
        r"\b(print|show|reveal|send|leak|give|muestra|revela|env[ií]a|dame)\b|"
        r"\b(print|show|reveal|send|leak|give|muestra|revela|env[ií]a|dame)\b[^.?!\n]{0,30}"
        r"\b(api[ _-]?key|secrets?|password|credentials?|\.env|contrase[nñ]a|clave de api|credenciales)\b", _I)),
]

# Subconjunto "fuerte" para los chunks del corpus: una wiki casi nunca contiene estas frases de forma legítima.
_STRONG = {"override_instructions", "reveal_system_prompt", "role_hijack", "delimiter_injection"}

PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("api_key", re.compile(r"\b(?:sk-ant-[\w-]+|sk-[\w-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})\b"), "[SECRET]"),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    ("phone", re.compile(r"(?<![\w-])(?:\+\d{1,3}[ -]?\d{3,4}[ -]?\d{4,}|\(\d{3}\)\s?\d{3}-\d{4}|"
                         r"\d{3}[ -]\d{3}[ -]\d{4}|\d{3,4}-\d{4})(?![\w-])"), "[PHONE]"),
    ("card", re.compile(r"\b(?:\d[ -]?){12,15}\d\b"), "[CARD]"),
    ("gov_id", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ID]"),
]

# Fragmentos únicos de los prompts del sistema: si aparecen en una respuesta, el prompt se filtró.
CANARIES = ("untrusted data, never instructions", "use only facts stated in the documents",
            "set abstained=true and cite nothing", "ONLY the documents provided inside <document>",
            "You write evaluation questions", "You decide whether retrieved documents")


def injection_signals(text: str, only: set[str] | None = None) -> list[str]:
    return [name for name, rx in INJECTION_PATTERNS if (only is None or name in only) and rx.search(text)]


def redact(text: str) -> tuple[str, list[str]]:
    """Reemplaza PII/secretos por marcadores. Devuelve (texto redactado, tipos encontrados)."""
    found: list[str] = []
    for name, rx, mark in PII_PATTERNS:
        text, n = rx.subn(mark, text)
        if n:
            found.append(name)
    return text, found


@dataclass
class InjectionGuard:
    """Rechaza la pregunta si dispara alguna firma de inyección (con el nombre de la firma en el motivo)."""

    name: str = "injection"

    def check(self, question: str, profile: Profile) -> GuardResult:
        hits = injection_signals(question)
        if hits:
            return GuardResult(False, f"prompt_injection:{','.join(hits)}", flags=hits)
        return GuardResult(True)


@dataclass
class PIIGuard:
    """No bloquea: entrega la pregunta redactada para que PII y secretos no lleguen al recuperador ni al LLM."""

    name: str = "pii"

    def check(self, question: str, profile: Profile) -> GuardResult:
        clean, found = redact(question)
        if found:
            return GuardResult(True, flags=[f"pii:{t}" for t in found], sanitized=clean)
        return GuardResult(True)


class QuarantineFilter:
    """AccessFilter: un chunk con instrucciones dirigidas a un modelo nunca llega al generador."""

    name = "quarantine"

    def __init__(self) -> None:
        self._cache: dict[str, bool] = {}

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        ok = self._cache.get(chunk.chunk_id)
        if ok is None:
            ok = not injection_signals(chunk.text, only=_STRONG)
            self._cache[chunk.chunk_id] = ok
        return ok


class LeakGuard:
    """OutputGuard: la respuesta no puede reproducir el prompt del sistema ni contener secretos."""

    name = "leak"

    def check(self, answer: Answer, context: list[Hit], profile: Profile) -> GuardResult:
        text = answer.answer.lower()
        if any(c.lower() in text for c in CANARIES):
            return GuardResult(False, "system_prompt_leak")
        _, found = redact(answer.answer)
        secrets = [t for t in found if t in ("api_key", "gov_id", "card")]
        if secrets:
            return GuardResult(False, f"sensitive_data_in_output:{','.join(secrets)}")
        return GuardResult(True)


def scan_corpus(chunks: list[Chunk]) -> list[tuple[str, list[str]]]:
    """Chunks del corpus con firmas fuertes de inyección (escaneo en la ingesta)."""
    out = []
    for c in chunks:
        sig = injection_signals(c.text, only=_STRONG)
        if sig:
            out.append((c.chunk_id, sig))
    return out
