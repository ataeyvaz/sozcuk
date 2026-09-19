import sys

from PySide6.QtWidgets import QApplication

from sozcuk import __version__, fonts, logbook, theme
from sozcuk.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sözcük")
    app.setApplicationVersion(__version__)
    # setOrganizationName kullanılmıyor: ayarlar ve kişisel sözlük %APPDATA%\Sözcük altında kalsın
    logbook.setup()  # yerel teşhis günlüğü; belge/dikte metni yazılmaz
    theme.apply(app)
    fonts.load_saved_fonts()

    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_document(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
