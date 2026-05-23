from storyforge.config import settings

def load_prompt(name: str) -> str:
    path = settings.prompts_path / name
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt template: {path}")
    return path.read_text(encoding="utf-8")
