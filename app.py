import sys
from pathlib import Path

# Allow `import study_companion.*` without installing the package.
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from study_companion.ui import run_app


if __name__ == "__main__":
    run_app()

