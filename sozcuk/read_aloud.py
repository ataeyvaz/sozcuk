"""Sesli okuma: belgeyi ya da seçili metni Türkçe okur (Word'ün "Sesli Oku"su gibi).

GİZLİLİK: Tamamen bilgisayarda çalışır. Metin, pronunciation.py ile ses birimlerine çevrilir ve bir Piper (VITS)
ses modeliyle onnxruntime üzerinde sese dönüştürülür; hiçbir sunucuya gönderilmez, internet gerekmez.

Ses modelleri: "<ad>.onnx" + "<ad>.onnx.json" çiftleri. Aranan yerler: uygulamayla gelen sozcuk/sesler/, Sozcuk.exe
yanındaki sesler/ ve %LOCALAPPDATA%\\Sözcük\\sesler. .json içindeki "sozcuk" bölümü arayüzdeki adı ve cinsiyeti verir:
    "sozcuk": {"name": "Ata", "gender": "erkek"}

Okuma sırasında bir sonraki cümle arka planda hazırlanır; böylece cümleler arasında bekleme olmaz.
"""

import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QStandardPaths, QThread, Signal
from PySide6.QtWidgets import QMenu, QMessageBox

from . import icons, logbook, pronunciation, resource_dir, theme

log = logbook.get("sesli-okuma")

VOICES_DIR_NAME = "sesler"
SPEEDS = [("Yavaş", 0.8), ("Normal", 1.0), ("Hızlı", 1.2), ("Çok hızlı", 1.45)]
SENTENCE_PAUSE = 0.18       # cümleler arası sessizlik (sn)
BLOCK_SECONDS = 0.1         # durdurma/duraklatma bu sıklıkla denetlenir


# =============================================================================
# Ses modelleri
# =============================================================================

def voice_dirs():
    folders = [resource_dir() / VOICES_DIR_NAME, Path(__file__).resolve().parent / VOICES_DIR_NAME,
               Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / VOICES_DIR_NAME]
    if getattr(sys, "frozen", False):
        folders.insert(1, Path(sys.executable).resolve().parent / VOICES_DIR_NAME)
    seen, result = set(), []
    for folder in folders:
        folder = folder.resolve()
        if folder.is_dir() and folder not in seen:
            seen.add(folder)
            result.append(folder)
    return result


class Voice:
    """Bir Piper ses modeli (onnx + json)."""

    def __init__(self, model_path, config):
        self.model_path = model_path
        self.config = config
        meta = config.get("sozcuk", {})
        self.id = model_path.stem.replace(".onnx", "")
        self.name = meta.get("name") or config.get("dataset") or self.id
        self.gender = meta.get("gender", "")
        self.sample_rate = config["audio"]["sample_rate"]
        self.id_map = config["phoneme_id_map"]
        inference = config.get("inference", {})
        self.noise_scale = inference.get("noise_scale", 0.667)
        self.length_scale = inference.get("length_scale", 1.0)
        self.noise_w = inference.get("noise_w", 0.8)
        self._session = None
        self._lock = threading.Lock()

    @property
    def label(self):
        return f"{self.name} ({self.gender})" if self.gender else self.name

    def session(self):
        with self._lock:
            if self._session is None:
                import onnxruntime  # ağır içe aktarma: yalnızca ilk okumada
                options = onnxruntime.SessionOptions()
                options.intra_op_num_threads = max(1, (os.cpu_count() or 2))
                started = time.monotonic()
                self._session = onnxruntime.InferenceSession(str(self.model_path), options,
                                                             providers=["CPUExecutionProvider"])
                log.info("ses modeli yüklendi: %s (%.1f sn)", self.id, time.monotonic() - started)
            return self._session

    def synthesize(self, text, speed=1.0):
        """Metni sese çevirir: int16 mono örnekler."""
        phonemes = pronunciation.phonemize(text)
        if not phonemes:
            return np.zeros(0, dtype=np.int16)
        ids = pronunciation.phoneme_ids(phonemes, self.id_map)
        session = self.session()
        inputs = {
            "input": np.array([ids], dtype=np.int64),
            "input_lengths": np.array([len(ids)], dtype=np.int64),
            "scales": np.array([self.noise_scale, self.length_scale / speed, self.noise_w], dtype=np.float32),
        }
        if len(session.get_inputs()) > 3:
            inputs["sid"] = np.array([0], dtype=np.int64)
        audio = session.run(None, inputs)[0].squeeze()
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 1.0:
            audio = audio / peak
        return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def find_voices():
    """Kurulu ses modelleri; aynı kimlikten birden fazla varsa ilk bulunan."""
    voices, seen = [], set()
    for folder in voice_dirs():
        for model in sorted(folder.glob("*.onnx")):
            config_path = model.with_name(model.name + ".json")
            if not config_path.exists():
                continue
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                voice = Voice(model, config)
            except (OSError, ValueError, KeyError) as exc:
                log.warning("ses modeli okunamadı: %s (%s)", model.name, exc)
                continue
            if voice.id not in seen:
                seen.add(voice.id)
                voices.append(voice)
    return voices


# =============================================================================
# Okuyucu (arka plan)
# =============================================================================

class Reader(QThread):
    """Parçaları sırayla sese çevirip çalar; bir sonraki parçayı çalınan parça sürerken hazırlar."""

    chunk_started = Signal(int, int)     # belge içindeki başlangıç, bitiş
    failed = Signal(str)

    def __init__(self, voice, chunks, speed, parent=None):
        super().__init__(parent)
        self.voice = voice
        self.chunks = chunks            # [(başlangıç, bitiş, metin)]
        self.speed = speed
        self._stop = threading.Event()
        self._pause = threading.Event()

    def stop(self):
        self._stop.set()
        self._pause.clear()

    def set_paused(self, paused):
        if paused:
            self._pause.set()
        else:
            self._pause.clear()

    @property
    def paused(self):
        return self._pause.is_set()

    def _produce(self, output):
        try:
            for start, end, text in self.chunks:
                if self._stop.is_set():
                    break
                started = time.monotonic()
                audio = self.voice.synthesize(text, self.speed)
                log.info("sentez: %d karakter, %.1f sn ses, %.2f sn", len(text), len(audio) / self.voice.sample_rate,
                         time.monotonic() - started)
                while not self._stop.is_set():
                    try:
                        output.put((start, end, audio), timeout=0.1)
                        break
                    except queue.Full:
                        continue
        except Exception as exc:  # model hatası: kullanıcıya bildir
            log.error("sentez hatası: %s", exc)
            self._put_final(output, exc)
        self._put_final(output, None)

    def _put_final(self, output, item):
        # okuma durdurulduysa kuyruğu okuyan kalmaz: beklemeden bırak
        while not self._stop.is_set():
            try:
                output.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def run(self):
        try:
            import sounddevice
        except (ImportError, OSError):
            self.failed.emit("Ses aygıtlarına erişilemiyor; hoparlör kullanılamıyor.")
            return
        output = queue.Queue(maxsize=2)
        producer = threading.Thread(target=self._produce, args=(output,), daemon=True)
        producer.start()
        rate = self.voice.sample_rate
        block = int(rate * BLOCK_SECONDS)
        pause = np.zeros(int(rate * SENTENCE_PAUSE), dtype=np.int16)
        try:
            with sounddevice.OutputStream(samplerate=rate, channels=1, dtype="int16") as stream:
                while not self._stop.is_set():
                    try:
                        item = output.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        self.failed.emit(f"Sesli okuma yapılamadı: {item}")
                        break
                    start, end, audio = item
                    self.chunk_started.emit(start, end)
                    audio = np.concatenate([audio, pause])
                    position = 0
                    while position < len(audio) and not self._stop.is_set():
                        if self._pause.is_set():
                            time.sleep(0.05)
                            continue
                        stream.write(audio[position:position + block])
                        position += block
        except Exception as exc:
            log.error("çalma hatası: %s", exc)
            self.failed.emit("Ses çalınamadı. Hoparlörün bağlı ve açık olduğundan emin olun.")
        finally:
            self._stop.set()
            producer.join(timeout=5)


# =============================================================================
# Denetleyici (arayüz)
# =============================================================================

class ReadAloudController(QObject):
    """"Sesli Oku" düğmesi ve menüsü: seçili metni ya da imleçten itibaren belgeyi okur, okunan cümleyi vurgular."""

    def __init__(self, editor, action, button, settings, notify=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.action = action
        self.settings = settings
        self.notify = notify
        self.reader = None
        self._voices = None
        self._document_revision = None

        self.pause_action = None
        self._build_menu(button)
        action.triggered.connect(self.toggle)
        editor.document().contentsChanged.connect(self._document_changed)
        self._set_idle_look()

    # --- ses ve hız ---------------------------------------------------------

    def voices(self, refresh=False):
        if self._voices is None or refresh:
            self._voices = find_voices()
        return self._voices

    def current_voice(self):
        voices = self.voices()
        if not voices:
            return None
        wanted = self.settings.value("read_aloud/voice", "")
        return next((voice for voice in voices if voice.id == wanted), voices[0])

    @property
    def speed(self):
        return float(self.settings.value("read_aloud/speed", 1.0))

    def _build_menu(self, button):
        menu = QMenu(button)
        self.pause_action = menu.addAction("Duraklat")
        self.pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(icons.icon("close"), "Okumayı Durdur", self.stop)
        menu.addSeparator()
        self.voice_menu = menu.addMenu("Ses")
        self.speed_menu = menu.addMenu("Hız")
        menu.aboutToShow.connect(self._refresh_menu)
        button.setMenu(menu)

    def _refresh_menu(self):
        reading = self.is_reading()
        self.pause_action.setEnabled(reading)
        self.pause_action.setText("Devam Et" if reading and self.reader.paused else "Duraklat")
        self.voice_menu.clear()
        voices = self.voices(refresh=not reading)
        current = self.current_voice()
        if not voices:
            self.voice_menu.addAction("Kurulu ses yok").setEnabled(False)
        for voice in voices:
            item = self.voice_menu.addAction(voice.label)
            item.setCheckable(True)
            item.setChecked(current is not None and voice.id == current.id)
            item.triggered.connect(lambda _=False, v=voice: self.settings.setValue("read_aloud/voice", v.id))
        self.speed_menu.clear()
        for label, value in SPEEDS:
            item = self.speed_menu.addAction(label)
            item.setCheckable(True)
            item.setChecked(abs(value - self.speed) < 0.01)
            item.triggered.connect(lambda _=False, v=value: self.settings.setValue("read_aloud/speed", v))

    # --- okuma ---------------------------------------------------------------

    def is_reading(self):
        return self.reader is not None and self.reader.isRunning()

    def toggle(self):
        if self.is_reading():
            self.stop()
        else:
            self.start()

    def toggle_pause(self):
        if self.is_reading():
            self.reader.set_paused(not self.reader.paused)

    def _chunks(self):
        """Okunacak parçalar: seçim varsa seçim, yoksa imlecin bulunduğu cümleden belge sonuna kadar."""
        text = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            low, high = cursor.selectionStart(), cursor.selectionEnd()
        else:
            low, high = cursor.position(), len(text)
        spans = pronunciation.sentences(text)
        chunks = []
        for start, end in spans:
            if end <= low or start >= high:
                continue
            if not cursor.hasSelection() and start < low and end > low:
                pass                              # imlecin içinde durduğu cümle baştan okunur
            elif cursor.hasSelection():
                start, end = max(start, low), min(end, high)
            piece = text[start:end].replace("￼", " ").strip()
            if any(char.isalnum() for char in piece):
                chunks.append((start, end, piece))
        return chunks

    def start(self):
        voice = self.current_voice()
        if voice is None:
            self.action.setChecked(False)
            QMessageBox.information(self.editor.window(), "Sesli Oku",
                                    "Kurulu bir ses modeli bulunamadı. Sesler Sözcük ile birlikte gelir; "
                                    "Sözcük'ü yeniden kurmayı deneyin.")
            return
        chunks = self._chunks()
        if not chunks:
            self.action.setChecked(False)
            self._message("Okunacak metin yok.")
            return
        self.reader = Reader(voice, chunks, self.speed, self)
        self.reader.chunk_started.connect(self._chunk_started)
        self.reader.failed.connect(self._failed)
        self.reader.finished.connect(self._finished)
        self._document_revision = self.editor.document().revision()
        self.reader.start()
        self._set_reading_look()
        if voice._session is None:
            self._message("Ses hazırlanıyor… (ilk okumada birkaç saniye sürer)")
        log.info("okuma başladı: %d parça, ses=%s, hız=%.2f", len(chunks), voice.id, self.speed)

    def stop(self):
        if self.reader is not None:
            self.reader.stop()      # iş parçacığı kendi kendine biter; sinyalleri artık dikkate alınmaz
            self.reader = None
        self.editor.set_reading_range(None)
        self._set_idle_look()

    def shutdown(self):
        for reader in self.findChildren(Reader):
            reader.stop()
            reader.wait(3000)

    def _chunk_started(self, start, end):
        if self.sender() is self.reader and self.editor.document().revision() == self._document_revision:
            self.editor.set_reading_range((start, end))
            self.editor.ensure_position_visible(start)

    def _failed(self, message):
        if self.sender() is self.reader:
            self._message(message)

    def _finished(self):
        reader = self.sender()
        if reader is self.reader:
            self.reader = None
            self.editor.set_reading_range(None)
            self._set_idle_look()
        reader.deleteLater()

    def _document_changed(self):
        # belge değişirse vurgulanan aralıklar kayar: okumayı durdur
        if self.is_reading() and self.editor.document().revision() != self._document_revision:
            self.stop()

    def _message(self, text):
        if self.notify:
            self.notify(text)

    # --- görünüm -------------------------------------------------------------

    def _set_idle_look(self):
        self.action.setChecked(False)
        self.action.setIcon(icons.icon("read_aloud"))
        self.action.setText("Sesli Oku")

    def _set_reading_look(self):
        self.action.setChecked(True)
        self.action.setIcon(icons.icon("read_aloud_active", theme.ACCENT))
        self.action.setText("Okumayı Durdur")
