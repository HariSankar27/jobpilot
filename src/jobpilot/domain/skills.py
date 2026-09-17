ALIASES = {
    "gcp": "google-cloud",
    "google cloud": "google-cloud",
    "k8s": "kubernetes",
    "azure openai": "azure-openai",
    "llms": "llm",
}
CANONICAL = {"python", "fastapi", "langgraph", "google-cloud", "kubernetes", "azure-openai", "llm"}
SKILL_VOCAB = CANONICAL | set(ALIASES)


def normalize_skill(s: str) -> str:
    key = s.strip().lower()
    return ALIASES.get(key, key.replace(" ", "-"))
