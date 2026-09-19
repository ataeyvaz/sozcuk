# Sözcük — PyInstaller paketi (klasör biçiminde; kurulum paketi bu klasörü kurar)
# Derleme:  .venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm
#
# Not: dil paketleri (sozcuk/diller/*.argosmodel) ve yardım metni uygulamayla birlikte gelir.
# Konuşma tanıma modeli pakete konmaz: ilk dikte kullanımında bir kez indirilir.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project = Path(SPECPATH)

datas = [
    (str(project / "sozcuk" / "yardim.md"), "sozcuk"),
    (str(project / "sozcuk.ico"), "."),
]
for model in (project / "sozcuk" / "diller").glob("*.argosmodel"):
    datas.append((str(model), "sozcuk/diller"))
datas.append((str(project / "sozcuk" / "diller" / "BENIOKU.txt"), "sozcuk/diller"))

# çeviri ve dikte bileşenlerinin veri dosyaları
for package in ("argostranslate", "ctranslate2", "sentencepiece", "stanza", "sacremoses", "faster_whisper"):
    try:
        datas += collect_data_files(package)
    except Exception:
        pass

hiddenimports = ["comtypes", "comtypes.client", "olefile", "docx", "pdfminer", "argostranslate",
                 "argostranslate.package", "argostranslate.translate", "ctranslate2", "sentencepiece",
                 "faster_whisper", "sounddevice"]
for package in ("argostranslate", "ctranslate2"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

analysis = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "matplotlib", "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtWebEngineCore",
              "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtQml"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Sozcuk",
    icon=str(project / "sozcuk.ico"),
    console=False,
    disable_windowed_traceback=False,
    version=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Sozcuk",
)
