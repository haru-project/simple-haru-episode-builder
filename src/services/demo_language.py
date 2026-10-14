"""Language policy for exported conversation goals."""
import copy
import json
import os

LANGUAGES = {
    "en-US": ("English", "Speak to participants only in English."),
    "es-ES": ("Español", "Habla con los participantes exclusivamente en español."),
    "ja-JP": ("日本語", "参加者には日本語だけで自然に話してください。"),
    "uk-UA": ("Українська", "Говори з учасниками лише природною українською мовою."),
}


def normalize_language(value=None):
    value = (value or os.environ.get("HARU_DEMO_LANGUAGE") or "en-US").lower().replace("_", "-")
    for locale in LANGUAGES:
        if value in (locale.lower(), locale[:2]):
            return locale
    raise ValueError(f"Unsupported demo language: {value}")


def apply_language(episode, language=None):
    result = copy.deepcopy(episode)
    locale = normalize_language(language)
    result["demo_language"] = locale
    for action in result.get("actions", []):
        if action.get("action_type") != "HARU_CONVERSATE" or not action.get("action_goal"):
            continue
        goal = json.loads(action["action_goal"])
        instructions = goal.setdefault("additional_instructions", [])
        instructions[:] = [i for i in instructions if i not in {v[1] for v in LANGUAGES.values()}]
        instructions.append(LANGUAGES[locale][1])
        action["action_goal"] = json.dumps(goal, ensure_ascii=False)
    return result
