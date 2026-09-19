"""Yerel teşhis günlüğü.

Günlük yalnızca bu bilgisayarda, uygulama veri klasöründe tutulur (…\\Sözcük\\Logs\\sozcuk.log); hiçbir
yere gönderilmez. GİZLİLİK: belge içeriği, dikte edilen metin ya da yapay zekâya gönderilen metin
günlüğe YAZILMAZ — yalnızca süreler, ses seviyeleri, karakter sayıları ve hatalar.
Kapatmak için: SOZCUK_LOG=0 ortam değişkeni.
"""

import logging
import os
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QStandardPaths, qInstallMessageHandler, QtMsgType

ROOT = "sozcuk"
MAX_BYTES = 1_000_000
BACKUPS = 3

_directory = None


def log_directory():
    global _directory
    if _directory is None:
        _directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "Logs"
    return _directory


def get(name):
    return logging.getLogger(f"{ROOT}.{name}")


def setup():
    logger = logging.getLogger(ROOT)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if os.environ.get("SOZCUK_LOG") == "0":
        logger.addHandler(logging.NullHandler())
        return logger
    try:
        log_directory().mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_directory() / "sozcuk.log", maxBytes=MAX_BYTES,
                                      backupCount=BACKUPS, encoding="utf-8")
    except OSError:
        logger.addHandler(logging.NullHandler())  # günlük yazılamıyorsa uygulama yine çalışsın
        return logger
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s"))
    logger.addHandler(handler)

    _install_exception_hooks(logger)
    qInstallMessageHandler(_qt_message_handler)

    from PySide6 import __version__ as pyside_version
    logger.info("=== Sözcük başlıyor · Python %s · PySide6 %s · %s ===",
                platform.python_version(), pyside_version, platform.platform())
    return logger


def _install_exception_hooks(logger):
    previous_hook = sys.excepthook

    def excepthook(kind, value, traceback):
        logger.critical("yakalanmamış hata", exc_info=(kind, value, traceback))
        previous_hook(kind, value, traceback)

    def thread_excepthook(args):
        logger.critical("iş parçacığında yakalanmamış hata (%s)", args.thread.name if args.thread else "?",
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = excepthook
    threading.excepthook = thread_excepthook


def _qt_message_handler(mode, context, message):
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        get("qt").warning(message)
