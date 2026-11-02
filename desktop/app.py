"""Desktop entry point. Run only when the user chooses to launch."""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtGui import QIcon
from .client import ensure_service
from .ui import Window

def main():
    app=QApplication(sys.argv);app.setApplicationName('deepseek-lab');app.setApplicationDisplayName('DeepSeek Lab');app.setDesktopFileName('deepseek-lab');app.setOrganizationName('DeepSeekLocal');app.setWindowIcon(QIcon(str(Path(__file__).parent/'deepseek-lab.svg')))
    app.setStyle('Fusion');app.setStyleSheet((Path(__file__).parent/'theme.qss').read_text())
    try:ensure_service()
    except Exception as exc:QMessageBox.critical(None,'Could not start workspace',str(exc));return 1
    window=Window();window.show();return app.exec()

if __name__=='__main__':sys.exit(main())
