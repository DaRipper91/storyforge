import re
from pathlib import Path

content = Path('docs/New_SetUp.md').read_text()

def extract_block(header_pattern):
    # Find the header
    m = re.search(header_pattern, content)
    if not m: return None
    start = m.end()
    # Find the next code block
    m2 = re.search(r'```(?:python|json|html|css|javascript|fish)\n(.*?)```', content[start:], re.DOTALL)
    if not m2: return None
    return m2.group(1).strip() + "\n"

# New files
files = {
    'src/storyforge/core/character_factory.py': r'3\.2 `src/storyforge/core/character_factory\.py` — NEW File',
    'src/storyforge/api/routes_lobby.py': r'3\.5 `src/storyforge/api/routes_lobby\.py` — NEW File',
    'data/seeds/default_campaign.json': r'3\.8 `data/seeds/default_campaign\.json` — Replace',
    'frontend/css/lobby.css': r'4\.2 `frontend/css/lobby\.css` — NEW File',
    'frontend/js/lobby.js': r'4\.5 `frontend/js/lobby\.js` — NEW File',
    'scripts/migrate_lobby.fish': r'scripts/migrate_lobby\.fish'
}

for fname, pattern in files.items():
    code = extract_block(pattern)
    if code:
        Path(fname).parent.mkdir(parents=True, exist_ok=True)
        Path(fname).write_text(code)
        print(f"Extracted {fname}")
    else:
        print(f"Failed to extract {fname}")

