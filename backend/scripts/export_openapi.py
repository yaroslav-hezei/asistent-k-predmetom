"""Write the OpenAPI schema of the backend to backend/openapi.json.

    python scripts/export_openapi.py          # regenerate
    python scripts/export_openapi.py --check  # exit 1 if openapi.json is out of date (CI)

Run from `backend/`. The frontend generates its TypeScript types from openapi.json.
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUTPUT = BACKEND_DIR / "openapi.json"

sys.path.insert(0, str(BACKEND_DIR))

from app.main import create_app  # noqa: E402


def render() -> str:
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only compare, do not write")
    args = parser.parse_args()

    schema = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != schema:
            print("openapi.json is out of date: run python scripts/export_openapi.py")
            return 1
        print("openapi.json is up to date")
        return 0
    OUTPUT.write_text(schema, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
