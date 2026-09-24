# Sözcük — PyInstaller paketi (klasör biçiminde; kurulum paketi bu klasörü kurar)
# Derleme:  .venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm
#
# Not: pakete yalnızca Türkçe ⇄ İngilizce dil paketleri (sozcuk/diller/translate-*/, açılmış klasör) konur;
# diğer diller kurulumda seçilirse Inno Setup indirir, sonradan uygulama içinden de indirilebilir.
# Konuşma tanıma modeli pakete konmaz: ilk dikte kullanımında bir kez indirilir.
# Sesli okuma sesleri (sozcuk/sesler/*.onnx + .onnx.json, ~63 MB/ses) pakete konur.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project = Path(SPECPATH)

datas = [
    (str(project / "sozcuk" / "yardim.md"), "sozcuk"),
    (str(project / "sozcuk.ico"), "."),
]
# sesli okuma sesleri: model + ayar dosyası çiftleri
for model in sorted((project / "sozcuk" / "sesler").glob("*.onnx")):
    config = model.with_name(model.name + ".json")
    if config.is_file():
        datas += [(str(model), "sozcuk/sesler"), (str(config), "sozcuk/sesler")]
# gömülü dil paketleri: açılmış klasörler (stanza/ cümle bölücüsü kullanılmadığı için alınmaz)
for package in sorted((project / "sozcuk" / "diller").glob("translate-*")):
    if not (package / "metadata.json").is_file():
        continue
    for file in package.rglob("*"):
        if file.is_file() and "stanza" not in file.relative_to(package).parts:
            datas.append((str(file), str(Path("sozcuk/diller") / file.parent.relative_to(project / "sozcuk" / "diller"))))

# çeviri ve dikte bileşenlerinin veri dosyaları (sacremoses: kısaltma listeleri; faster_whisper: sessizlik modeli)
for package in ("ctranslate2", "sacremoses", "faster_whisper"):
    datas += collect_data_files(package)

hiddenimports = ["comtypes", "comtypes.client", "olefile", "docx", "pdfminer", "ctranslate2", "sentencepiece",
                 "sacremoses", "faster_whisper", "sounddevice", "tokenizers", "onnxruntime"]

# Kullanılmayan büyük bileşenler. torch/stanza/spacy eskiden Argos Translate ile geliyordu (çeviri artık onlarsız);
# av (PyAV) dikte için gerekmez (dictation._stub_av). Qt'nin QML/Quick, PDF ve ağ modülleri kullanılmıyor.
excludes = ["tkinter", "matplotlib", "torch", "torchaudio", "torchvision", "stanza", "spacy", "thinc", "blis",
            "argostranslate", "minisbd", "av", "sympy", "networkx", "emoji",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtWebEngineCore", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtNetwork", "PySide6.QtPdf",
            "PySide6.QtOpenGL"]

analysis = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=False,
)

# Qt eklentileri ve DLL'lerinden kullanılmayanlar (sanal klavye → QML/Quick'i sürüklüyor; yazılım OpenGL 20 MB;
# arayüz Qt çevirilerini yüklemiyor)
UNUSED_QT = ("opengl32sw.dll", "qtvirtualkeyboardplugin", "qt6virtualkeyboard", "qt6quick", "qt6qml",
             "qt6pdf", "qpdf.dll", "qt6network", "qtnetwork.pyd", "plugins/networkinformation", "plugins/tls",
             "qdirect2d.dll", "qt6opengl.dll")


def _keep(entry):
    name = entry[0].replace("\\", "/").lower()
    if "pyside6/" not in name:
        return True
    if "pyside6/translations/" in name:
        return name.endswith(("qtbase_tr.qm", "qt_tr.qm"))
    return not any(part in name for part in UNUSED_QT)


analysis.binaries = [entry for entry in analysis.binaries if _keep(entry)]
analysis.datas = [entry for entry in analysis.datas if _keep(entry)]

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
