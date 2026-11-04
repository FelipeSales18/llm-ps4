"""Correção igual à do notebook: strict = último '#### <número>' bate com o gold;
flex = o strict se existir, senão o último número da saída. Ignora vírgulas e '$'."""
import re

NUM = r"-?\d+(?:\.\d+)?"


def _norm(s: str) -> str:
    return s.replace(",", "").replace("$", "")


def _eq(a: str, gold: str) -> bool:
    try:
        return float(a) == float(_norm(gold))
    except ValueError:
        return False


def extract_strict(text: str):
    m = re.findall(r"####\s*(" + NUM + ")", _norm(text))
    return m[-1] if m else None


def extract_flex(text: str):
    s = extract_strict(text)
    if s is not None:
        return s
    m = re.findall(NUM, _norm(text))
    return m[-1] if m else None


def grade(text: str, gold: str):
    s, f = extract_strict(text), extract_flex(text)
    return (s is not None and _eq(s, gold)), (f is not None and _eq(f, gold))
