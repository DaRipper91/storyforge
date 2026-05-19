
import sys
from pathlib import Path
import json

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / 'src'))

from storyforge.core.models import AINarrationResponse

schema_path = project_root / 'src' / 'storyforge' / 'ai' / 'prompts' / 'schemas' / 'state_diff.schema.json'
schema_path.parent.mkdir(parents=True, exist_ok=True)
schema_path.write_text(json.dumps(AINarrationResponse.model_json_schema(), indent=2))
print(f'Wrote schema to {schema_path}')

