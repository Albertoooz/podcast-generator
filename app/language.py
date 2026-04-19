import pycountry


def resolve_language_name(language_code: str) -> str:
    if not language_code or not language_code.strip():
        raise ValueError("Language code cannot be empty")
    code = language_code.strip().split("-")[0].lower()
    lang = pycountry.languages.get(alpha_2=code)
    if lang is None:
        lang = pycountry.languages.get(alpha_3=code)
    if lang is None:
        raise ValueError(
            f"Invalid language code: '{language_code}'. "
            "Use ISO 639-1 (e.g., 'en') or BCP 47 (e.g., 'pt-BR').",
        )
    name: str = str(lang.name)
    if ";" in name:
        name = name.split(";")[0].strip()
    return name
