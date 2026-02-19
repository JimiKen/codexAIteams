from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from codex_ai_teams.ui.app_icon import ensure_app_icon  # noqa: E402


def main() -> None:
    app = QApplication.instance()
    created = False
    if app is None:
        app = QApplication([])
        created = True
    path = ensure_app_icon(PROJECT_ROOT)
    print(f"Icon generated: {path}")
    if created:
        app.quit()


if __name__ == "__main__":
    main()
