"""Sesle yazma (dikte): mikrofondan kayıt, sessizlikte otomatik durdurma, canlı seviye ve
faster-whisper ile Türkçe konuşma tanıma (dikte sözlüğü ipuçları ve öğrenilen düzeltmelerle).

GİZLİLİK: Tüm ses işleme bu bilgisayarda yapılır. Ses kaydı da, ondan çıkan metin de, dikte sözlüğü de
hiçbir sunucuya gönderilmez. İnternet yalnızca ilk kullanımda Whisper modelini bir kez indirmek için
gerekir; model sonra yerel önbellekten (Hugging Face önbelleği) yüklenir.
"""

import os
import threading
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QStandardPaths, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QTextCursor
from PySide6.QtWidgets import QMenu

from . import icons, logbook
from .vocabulary import MANUAL, build_hint
from .widgets import LevelMeter

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # Windows'ta gereksiz uyarıyı sustur

log = logbook.get("dikte")

MODEL_SIZE = "small"          # Türkçe doğruluğu ile indirme boyutu (~480 MB) / hız dengesi
SAMPLE_RATE = 16_000          # Whisper'ın beklediği örnekleme hızı
LANGUAGE = "tr"               # otomatik algılama yerine açıkça Türkçe: kısa kayıtlarda daha güvenilir
MAX_SECONDS = 10 * 60         # bellek taşmasın diye tek kayıt üst sınırı
MIN_SECONDS = 0.4
BLOCK_SECONDS = 0.1           # seviye ve sessizlik ölçümü 100 ms'lik bloklarla


class DictationError(Exception):
    """Kullanıcıya durum çubuğunda gösterilebilecek Türkçe hata."""


def _sounddevice():
    # ses kütüphanesi (PortAudio) yüklenemezse uygulama açılışta çökmesin; yalnızca dikte kullanılamaz
    try:
        import sounddevice
    except (ImportError, OSError) as exc:
        raise DictationError("Ses aygıtlarına erişilemiyor; mikrofon kullanılamıyor.") from exc
    return sounddevice


# =============================================================================
# Sessizlik algılama
# =============================================================================

class SilenceDetector:
    """Konuşma başladıktan sonra THRESHOLD_SECONDS kadar kesintisiz sessizlik görünce bir kez bildirir.

    Eşik üç ölçünün en büyüğüdür (Diktek projesinde sahada doğrulanan yaklaşımın genişletilmiş hali):
    - mutlak taban: sessiz bir odada fısıltının konuşma sayılmaması için
    - kaydın en yüksek bloğunun oranı: kısık ve gür mikrofonlara kendiliğinden uyum
    - kaydın gürültü tabanı (düşük yüzdelik): gürültülü ortamda ortam sesinin konuşma sayılmaması için
    Eşik hiçbir zaman en yüksek bloğun yarısını geçmez; yoksa konuşmanın kendisi "sessiz" sayılırdı.
    Konuşma görülmeden sayaç işlemez: kullanıcı düğmeye basıp henüz konuşmadan kayıt kapanmasın.
    Tetiklenmezse güvenli taraftadır: kayıt düğme ya da kısayolla her zaman durdurulabilir.
    """

    THRESHOLD_SECONDS = 2.5   # daha kısası cümle ortasındaki düşünme molasında keserdi
    ABSOLUTE_RMS = 0.004
    RELATIVE_FACTOR = 0.10
    NOISE_FACTOR = 2.5
    SPEECH_ONSET_RMS = 0.008
    NOISE_PERCENTILE = 20
    MIN_BLOCKS_FOR_NOISE = 5

    def __init__(self):
        self.reset()

    def reset(self):
        self.history = []
        self.peak_rms = 0.0
        self.speech_seen = False
        self.silent_seconds = 0.0
        self.reported = False

    def noise_floor(self):
        if len(self.history) < self.MIN_BLOCKS_FOR_NOISE:
            return 0.0
        return float(np.percentile(self.history, self.NOISE_PERCENTILE))

    def threshold(self):
        value = max(self.ABSOLUTE_RMS, self.peak_rms * self.RELATIVE_FACTOR, self.noise_floor() * self.NOISE_FACTOR)
        return min(value, self.peak_rms * 0.5) if self.peak_rms else value

    def push(self, rms, seconds=BLOCK_SECONDS):
        """Bir bloğun RMS'ini işler; eşik bu blokla İLK kez dolduysa True döner."""
        if self.reported:
            return False
        self.history.append(rms)
        self.peak_rms = max(self.peak_rms, rms)
        if not self.speech_seen:
            self.speech_seen = rms >= max(self.SPEECH_ONSET_RMS, self.noise_floor() * 3)
            return False
        if rms >= self.threshold():
            self.silent_seconds = 0.0
            return False
        self.silent_seconds += seconds
        if self.silent_seconds >= self.THRESHOLD_SECONDS:
            self.reported = True
            return True
        return False


# =============================================================================
# Kayıt
# =============================================================================

class Recorder:
    """Varsayılan mikrofondan mono kayıt. Ses verisi yalnızca bellekte tutulur, diske yazılmaz."""

    def __init__(self):
        self._stream = None
        self._sd = None
        self._chunks = []
        self._rate = SAMPLE_RATE
        self._lock = threading.Lock()
        self.detector = SilenceDetector()
        self.started_at = None
        # ses geri çağırma iş parçacığında yazılır, arayüz zamanlayıcısında okunur (tek değer atamaları)
        self.current_rms = 0.0
        self.current_peak = 0.0
        self.max_peak = 0.0
        self.silence_detected = False

    @property
    def recording(self):
        return self._stream is not None

    def elapsed(self):
        return time.monotonic() - self.started_at if self.started_at else 0.0

    def start(self):
        sd = self._sd = _sounddevice()
        try:
            device = sd.query_devices(kind="input")
        except (ValueError, sd.PortAudioError) as exc:
            raise DictationError("Mikrofon bulunamadı.") from exc
        if not device or device.get("max_input_channels", 0) < 1:
            raise DictationError("Mikrofon bulunamadı.")

        self._chunks = []
        self.detector.reset()
        self.current_rms = self.current_peak = self.max_peak = 0.0
        self.silence_detected = False
        # önce Whisper'ın hızıyla dene; sürücü desteklemezse mikrofonun kendi hızında kaydet, sonra dönüştür
        for rate in (SAMPLE_RATE, int(device.get("default_samplerate") or 44_100)):
            try:
                stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32",
                                        blocksize=int(rate * BLOCK_SECONDS), callback=self._callback)
                stream.start()
            except sd.PortAudioError:
                continue
            self._stream, self._rate = stream, rate
            self.started_at = time.monotonic()
            log.info("kayıt başladı: aygıt=%r hız=%d Hz", device.get("name"), rate)
            return
        raise DictationError("Mikrofon açılamadı. Başka bir uygulama kullanıyor ya da mikrofon izni kapalı olabilir.")

    def _callback(self, data, frames, time_info, status):
        chunk = data[:, 0].copy()
        with self._lock:
            self._chunks.append(chunk)
        if not len(chunk):
            return
        self.current_rms = float(np.sqrt(np.mean(chunk ** 2)))
        self.current_peak = float(np.abs(chunk).max())
        self.max_peak = max(self.max_peak, self.current_peak)
        if self.detector.push(self.current_rms, len(chunk) / self._rate):
            self.silence_detected = True  # durdurmayı burada yapmıyoruz: arayüz iş parçacığı yoklar

    def stop(self):
        """Kaydı durdurur ve 16 kHz mono float32 ses döndürür."""
        stream, self._stream = self._stream, None
        self.started_at = None
        self.current_rms = self.current_peak = 0.0
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except self._sd.PortAudioError:
                pass
        with self._lock:
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(chunks)
        if self._rate != SAMPLE_RATE:
            audio = _resample(audio, self._rate, SAMPLE_RATE)
        return audio.astype(np.float32)


def _resample(audio, source_rate, target_rate):
    if len(audio) == 0:
        return audio
    duration = len(audio) / source_rate
    target_len = int(round(duration * target_rate))
    source_times = np.linspace(0.0, duration, num=len(audio), endpoint=False)
    target_times = np.linspace(0.0, duration, num=target_len, endpoint=False)
    return np.interp(target_times, source_times, audio)


# =============================================================================
# Tanıma
# =============================================================================

_model = None
_model_lock = threading.Lock()


def _load_model(on_status):
    """Modeli bir kez yükler; önbellekte yoksa önce indirir (yalnızca ilk kullanımda)."""
    global _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel  # ağır içe aktarma: uygulama açılışını yavaşlatmasın

        # CPU + int8: her bilgisayarda çalışır, ek GPU sürücüsü gerektirmez, small model için yeterince hızlı
        kwargs = {"device": "cpu", "compute_type": "int8"}
        started = time.monotonic()
        try:
            _model = WhisperModel(MODEL_SIZE, local_files_only=True, **kwargs)
        except Exception:
            log.info("model önbellekte yok, indiriliyor")
            on_status("Konuşma tanıma modeli indiriliyor (yalnızca ilk kullanımda, ~480 MB)…")
            try:
                _model = WhisperModel(MODEL_SIZE, **kwargs)
            except Exception as exc:
                log.error("model indirilemedi: %s", exc)
                raise DictationError(
                    "Konuşma tanıma modeli indirilemedi. İlk kullanım için internet bağlantısı gerekir."
                ) from exc
        log.info("model yüklendi: %s (%.1f sn)", MODEL_SIZE, time.monotonic() - started)
        return _model


def transcribe(audio, hint_words=(), on_status=lambda message: None):
    if len(audio) < SAMPLE_RATE * MIN_SECONDS:
        raise DictationError("Kayıt çok kısa; konuşma algılanmadı.")
    model = _load_model(on_status)
    on_status("Ses metne dönüştürülüyor…")
    hint = build_hint(list(hint_words), lambda text: len(model.hf_tokenizer.encode(" " + text).ids))
    started = time.monotonic()
    segments, _ = model.transcribe(
        audio,
        language=LANGUAGE,
        beam_size=5,
        vad_filter=True,                   # sessizlikleri at: Whisper'ın sessizlikte uydurma metin üretmesini önler
        condition_on_previous_text=False,  # uzun kayıtlarda tekrar döngüsüne girmesin
        hotwords=hint,                     # dikte sözlüğü: özel adlar ve terimler için ipucu
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    log.info("tanıma: ses=%.1f sn süre=%.1f sn karakter=%d ipucu=%d kelime",
             len(audio) / SAMPLE_RATE, time.monotonic() - started, len(text),
             len(hint.split(", ")) if hint else 0)
    if not text:
        raise DictationError("Konuşma algılanmadı.")
    return text


class ModelLoader(QThread):
    """Kayıt başlarken modeli arka planda hazırlar; kullanıcı konuşurken yükleme süresi harcanmış olur."""

    status = Signal(str)

    def run(self):
        try:
            _load_model(self.status.emit)
        except DictationError:
            pass  # hata, dönüştürme adımında kullanıcıya gösterilir


class TranscribeWorker(QThread):
    """Tanımayı arka planda çalıştırır (arayüz donmaz) — PDF içe aktarma ile aynı düzen."""

    status = Signal(str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, audio, hint_words, parent=None):
        super().__init__(parent)
        self.audio = audio
        self.hint_words = list(hint_words)  # arayüz iş parçacığında alınmış kopya

    def run(self):
        try:
            self.done.emit(transcribe(self.audio, self.hint_words, self.status.emit))
        except DictationError as exc:
            log.warning("tanıma sonuçsuz: %s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:
            log.exception("tanıma hatası")
            self.failed.emit(f"Ses metne dönüştürülemedi: {exc}")


def join_with_context(text_before, dictated):
    """Dikte edilen metni, imlecin önündeki metne yazılmış gibi bağlar (gerekirse boşluk ekler)."""
    if text_before and not text_before[-1].isspace() and dictated[:1] not in ".,;:!?)":
        return " " + dictated
    return dictated


class TrackedRange:
    """Dikte edilen metnin belgedeki yerini düzenlemeler boyunca izler.

    Tek bir seçimli QTextCursor yetmez: metin imlecin tam konumuna eklenince imleç ileri kayar, yani
    kullanıcı dikteden hemen sonra yazmaya devam ettiğinde aralık büyür ve elle yazılan metin de
    "dikte edilmiş" sayılırdı. Bu yüzden:
    - başlangıç imleci kendi konumuna yapılan eklemede yerinde kalır: ilk kelime değiştirilince yeni hali
      aralıkta kalır;
    - bitiş, aralığın SON KARAKTERİNİN konumuyla izlenir: arkaya yazılan metin o konumdan sonra eklendiği
      için aralığa girmez, son kelime değiştirilince ise imleç yeni kelimenin sonuna taşınır.
    Test edildi: arkaya yazma, içte/ilk/son kelimeyi düzeltme.
    """

    def __init__(self, document, start, end):
        self.start = QTextCursor(document)
        self.start.setPosition(start)
        self.start.setKeepPositionOnInsert(True)
        self.last = QTextCursor(document)
        self.last.setPosition(max(start, end - 1))
        self._empty = end <= start

    def span(self):
        start = self.start.position()
        if self._empty:
            return start, start
        # son karakter silinip yerine yazıldıysa imleç yeni metnin sonuna geçer; kelime içi ise son karakterde durur
        cursor = QTextCursor(self.last)
        end = self.last.position()
        if end < cursor.document().characterCount() - 1 and not cursor.atBlockEnd():
            probe = QTextCursor(cursor)
            probe.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            if probe.selectedText() and not probe.selectedText().isspace():
                end += 1
        return start, max(start, end)

    def contains(self, start, end):
        a, b = self.span()
        return a <= start and end <= b

    def text(self):
        a, b = self.span()
        cursor = QTextCursor(self.start)
        cursor.setPosition(a)
        cursor.setPosition(b, QTextCursor.KeepAnchor)
        return cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")


def vocabulary_path():
    return Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "dikte-sozlugu.json"


# =============================================================================
# Arayüz denetleyicisi (araç çubuğu düğmesi + durum çubuğu)
# =============================================================================

RECORDING_COLORS = ("#c42b1c", "#f08a93")  # kayıt sırasında ikon bu iki ton arasında yanıp söner
TICK_MS = 100
PULSE_TICKS = 5


class DictationController(QObject):
    """Mikrofon düğmesini yönetir: bas → dinle, tekrar bas ya da sus → yerel olarak metne çevir ve imlece ekle."""

    def __init__(self, editor, action, button, status_bar, settings, vocabulary, notify=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.action = action
        self.status_bar = status_bar
        self.settings = settings
        self.notify = notify  # notify(metin, [(düğme, işlev), …]): pencerenin bilgi çubuğu
        self.recorder = Recorder()
        self.vocabulary = vocabulary  # kişisel sözlük; yazım denetimiyle ortak
        self.worker = None
        self.loader = None
        self._loader_note = ""
        self._ticks = 0
        self._auto_stopped = False
        self._last_dictation = None  # (dikte edilen aralığı izleyen imleç, eklenen metin) — öğrenme için
        self._history = []           # bu oturumdaki dikte bölümleri: sağ tıkta "orijinalde ne tanınmıştı?" için

        self._timer = QTimer(self, interval=TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._busy_text = ""
        self._busy_since = 0.0
        self._busy_timer = QTimer(self, interval=1000)
        self._busy_timer.timeout.connect(self._show_busy)

        self.meter = LevelMeter()
        self.meter.hide()
        status_bar.insertPermanentWidget(0, self.meter)

        self._build_menu(button)
        self._set_idle_look()
        action.triggered.connect(self.toggle)
        editor.cursorPositionChanged.connect(self._maybe_learn)
        editor.context_menu_hooks.append(self._context_menu_hook)

    # --- ayarlar ve menü -----------------------------------------------------

    @property
    def auto_stop(self):
        return self.settings.value("dictation/auto_stop", True, type=bool)

    @property
    def show_meter(self):
        return self.settings.value("dictation/level_meter", True, type=bool)

    def _build_menu(self, button):
        menu = QMenu(button)
        auto = menu.addAction(f"Susunca Otomatik Durdur ({SilenceDetector.THRESHOLD_SECONDS:g} sn)".replace(".", ","))
        auto.setCheckable(True)
        auto.setChecked(self.auto_stop)
        auto.toggled.connect(lambda on: self.settings.setValue("dictation/auto_stop", on))
        meter = menu.addAction("Ses Seviyesi Göstergesi")
        meter.setCheckable(True)
        meter.setChecked(self.show_meter)
        meter.toggled.connect(self._meter_toggled)
        menu.addSeparator()
        menu.addAction(icons.icon("spell_check"), "Dikte Sözlüğü…", lambda: self.open_vocabulary())
        button.setMenu(menu)

    def _meter_toggled(self, on):
        self.settings.setValue("dictation/level_meter", on)
        self.meter.setVisible(on and self.recorder.recording)

    def open_vocabulary(self, initial_word=""):
        from .vocabulary_dialog import VocabularyDialog  # yalnızca açılınca yükle
        self._maybe_learn(force=True)
        VocabularyDialog(self.vocabulary, self.editor.window(), initial_word).exec()

    def _context_menu_hook(self, menu, cursor):
        target = QTextCursor(cursor)
        if not target.hasSelection():
            target.select(QTextCursor.WordUnderCursor)  # seçim yoksa tıklanan kelime
        selected = target.selectedText().strip()
        if not selected or len(selected.split()) > 3 or "\u2029" in selected or len(selected) > 60:
            return
        menu.addSeparator()
        dictation = menu.addMenu(icons.icon("mic"), "Dikte Sözlüğü")
        dictation.addAction(f"Dikte Düzeltmesi Olarak Kaydet: “{selected}”…",
                            lambda: self.save_verified_correction(target))
        if self.vocabulary.find_word(selected):
            dictation.addAction(f"“{selected}” sözlükte kayıtlı").setEnabled(False)
        elif cursor.hasSelection():
            dictation.addAction(f"Kelime Olarak Ekle: “{selected}”", lambda: self._add_word(selected))
        dictation.addSeparator()
        dictation.addAction("Dikte Sözlüğünü Aç…", lambda: self.open_vocabulary())

    def _recognized_as(self, target):
        """(Whisper'ın orijinalde tanıdığı hal ya da None, seçim dikte edilmiş bir bölümde mi)."""
        from .vocabulary import recognized_counterpart
        start, end = target.selectionStart(), target.selectionEnd()
        for tracked, original in reversed(self._history):
            if tracked.contains(start, end):
                return recognized_counterpart(original, tracked.text(), target.selectedText()), True
        return None, False

    def save_verified_correction(self, target):
        """Kullanıcının doğruladığı yanlış → doğru kaydı: hemen etkin olur, doğru hali tanımaya ipucu olur."""
        from .vocabulary import tr_lower
        from .vocabulary_dialog import CorrectionDialog
        selected = target.selectedText().strip()
        counterpart, in_dictation = self._recognized_as(target)
        if counterpart:
            wrong, right = counterpart, selected   # kullanıcı metni zaten düzeltmiş: "tiktik" → "diktek"
        elif in_dictation:
            wrong, right = selected, ""            # dikte edildiği gibi duruyor: seçili kelime yanlış olan
        else:
            wrong, right = "", selected            # elle yazılmış metin: seçili kelimenin doğru hal olduğu varsayılır
        dialog = CorrectionDialog(self.editor.window(), wrong=wrong, right=right)
        if not dialog.exec():
            return
        wrong, right = dialog.values()
        correction = self.vocabulary.add_correction(wrong, right)  # elle = doğrulanmış
        if correction is None:
            self.status_bar.showMessage("Tanınan ve doğru hali aynı; kayıt eklenmedi.", 5000)
            return
        if tr_lower(target.selectedText().strip()) == tr_lower(correction.wrong):
            target.insertText(correction.right)  # belgedeki yanlış kelimeyi de düzelt (tek geri alma adımı)
        # bekleyen öğrenme aynı düzeltmeyi ikinci kez sormasın
        if self._last_dictation is not None:
            tracked, _ = self._last_dictation
            self._last_dictation = (tracked, tracked.text())
        log.info("doğrulanmış düzeltme eklendi (sağ tık), toplam düzeltme=%d", len(self.vocabulary.corrections))
        self.status_bar.showMessage(
            f"Doğrulanmış kayıt eklendi: “{correction.wrong}” → “{correction.right}”. Sonraki diktelerde otomatik düzeltilecek.",
            6000)

    def _add_word(self, word):
        if self.vocabulary.add_word(word):
            log.info("sözlüğe kelime eklendi (elle), toplam kelime=%d", len(self.vocabulary.words))
            self.status_bar.showMessage(f"“{word}” dikte sözlüğüne eklendi.", 4000)

    # --- kayıt ---------------------------------------------------------------

    @property
    def shortcut_text(self):
        return self.action.shortcut().toString(QKeySequence.NativeText)

    def toggle(self):
        if self.worker is not None and self.worker.isRunning():
            self.action.setChecked(False)
            return
        if self.recorder.recording:
            self.stop()
        else:
            self.start()

    def start(self):
        self._maybe_learn(force=True)
        try:
            self.recorder.start()
        except DictationError as exc:
            log.warning("kayıt başlatılamadı: %s", exc)
            self._set_idle_look()
            self.status_bar.showMessage(str(exc), 6000)
            return
        self._ticks = 0
        self._auto_stopped = False
        self.action.setChecked(True)
        self.action.setToolTip(f"Kaydı Durdur ve Metne Dönüştür ({self.shortcut_text})")
        self.meter.reset()
        self.meter.setVisible(self.show_meter)
        self._tick()
        self._timer.start()
        if _model is None and (self.loader is None or not self.loader.isRunning()):
            self._loader_note = ""
            self.loader = ModelLoader(self)
            self.loader.status.connect(lambda text: setattr(self, "_loader_note", text))
            self.loader.finished.connect(lambda: setattr(self, "_loader_note", ""))
            self.loader.start()

    def stop(self, automatic=False):
        self._timer.stop()
        detector = self.recorder.detector
        max_peak, elapsed = self.recorder.max_peak, self.recorder.elapsed()
        audio = self.recorder.stop()
        log.info("kayıt durdu: %.1f sn, otomatik=%s, tepe=%.3f, konuşma tepe RMS=%.4f, gürültü tabanı=%.4f",
                 elapsed, automatic, max_peak, detector.peak_rms, detector.noise_floor())
        self.meter.hide()
        self._set_idle_look()
        self.action.setEnabled(False)
        self._set_busy("Ses metne dönüştürülüyor…")
        worker = TranscribeWorker(audio, self.vocabulary.hint_candidates(), self)
        worker.status.connect(self._set_busy)
        worker.done.connect(self._insert)
        worker.failed.connect(self._failed)
        worker.finished.connect(self._transcription_finished)
        self.worker = worker
        worker.start()

    def _tick(self):
        recorder = self.recorder
        seconds = recorder.elapsed()
        if seconds >= MAX_SECONDS:
            self.stop()
            return
        if recorder.silence_detected and self.auto_stop:
            self._auto_stopped = True
            self.stop(automatic=True)
            return

        if self._ticks % PULSE_TICKS == 0:
            color = RECORDING_COLORS[(self._ticks // PULSE_TICKS) % 2]
            self.action.setIcon(icons.icon("mic_recording", color))
        self._ticks += 1

        detector = recorder.detector
        self.meter.set_level(recorder.current_rms, recorder.current_peak, detector.speech_seen)

        clock = f"{int(seconds) // 60}:{int(seconds) % 60:02d}"
        if not detector.speech_seen:
            state = "konuşmaya başlayın"
        elif self.auto_stop and detector.silent_seconds > 0:
            remaining = max(0.0, SilenceDetector.THRESHOLD_SECONDS - detector.silent_seconds)
            state = f"susarsanız {remaining:.1f} sn sonra biter".replace(".", ",")
        elif self.auto_stop:
            state = "susunca kendiliğinden durur"
        else:
            state = f"durdurmak için mikrofona tıklayın ya da {self.shortcut_text}"
        note = f" · {self._loader_note}" if self._loader_note else ""
        self.status_bar.showMessage(f"Dinleniyor… {clock} — {state}{note}")

    def _set_idle_look(self):
        self.action.setChecked(False)
        self.action.setIcon(icons.icon("mic"))
        self.action.setToolTip(f"Sesle Yaz ({self.shortcut_text}) — ses bu bilgisayarda işlenir, hiçbir yere gönderilmez")

    # --- dönüştürme ----------------------------------------------------------

    def _set_busy(self, text):
        self._busy_text = text
        self._busy_since = time.monotonic()
        self._show_busy()
        self._busy_timer.start()

    def _show_busy(self):
        seconds = int(time.monotonic() - self._busy_since)
        self.status_bar.showMessage(f"{self._busy_text} ({seconds} sn)" if seconds else self._busy_text)

    def _failed(self, message):
        self._busy_timer.stop()
        self.status_bar.showMessage(message, 6000)

    def _transcription_finished(self):
        self._busy_timer.stop()
        self.action.setEnabled(True)

    def _insert(self, text):
        self._busy_timer.stop()
        text, corrected = self.vocabulary.apply(text)
        self.vocabulary.note_used(text)

        cursor = self.editor.textCursor()
        before = cursor.block().text()[: cursor.selectionStart() - cursor.block().position()]
        inserted = join_with_context(before, text)
        # ayrı düzenleme bloğu: Ctrl+Z yalnızca dikte edilen metni geri alsın, önceden yazılanı değil
        cursor.beginEditBlock()
        start = cursor.selectionStart()
        cursor.insertText(inserted)  # seçim varsa, yazıyormuş gibi yerine geçer
        cursor.endEditBlock()

        # öğrenme için dikte edilen aralığı izle: kullanıcı burada bir kelimeyi düzeltirse sözlük öğrenir
        tracked = TrackedRange(self.editor.document(), start, cursor.position())
        self._last_dictation = (tracked, inserted)
        self._history = (self._history + [(tracked, inserted)])[-50:]

        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        suffix = f" ({corrected} sözlük düzeltmesi uygulandı)" if corrected else ""
        log.info("metin eklendi: karakter=%d, sözlük düzeltmesi=%d", len(inserted), corrected)
        self.status_bar.showMessage(f"Dikte edilen metin eklendi.{suffix}", 4000)

    # --- öğrenme -------------------------------------------------------------

    def _maybe_learn(self, force=False):
        """İmleç dikte edilen bölümden çıkınca (ya da yeni dikte başlarken) kullanıcının düzeltmelerini öğrenir."""
        if self._last_dictation is None:
            return
        tracked, original = self._last_dictation
        if not force:
            position = self.editor.textCursor().position()
            if tracked.contains(position, position):
                return  # kullanıcı hâlâ bu bölümde çalışıyor
        self._last_dictation = None
        current = tracked.text()
        if not current.strip() or current == original:
            return
        learned = [c for c in self.vocabulary.learn(original, current) if c.source != MANUAL]
        if not learned:
            return
        log.info("sözlük düzeltme öğrendi: %d kayıt", len(learned))
        pairs = ", ".join(f"“{c.wrong}” → “{c.right}”" for c in learned[:3])
        more = f" ve {len(learned) - 3} düzeltme daha" if len(learned) > 3 else ""
        if self.notify is None:
            self.status_bar.showMessage(f"Dikte sözlüğü öğrendi: {pairs}{more}.", 7000)
            return
        pending = [c for c in learned if not c.active]
        if pending:
            question = "Sonraki diktelerde hemen otomatik düzeltilsin mi? (Onaylamazsanız bir kez daha görülünce etkinleşir.)"
        else:
            question = "Bu düzeltme ikinci kez görüldüğü için artık otomatik uygulanıyor."
        self.notify(
            f"Sözcük dikte düzeltmenizi öğrendi: {pairs}{more}. {question}",
            [("Evet, Doğrula", lambda: self._confirm_learned(learned)),
             ("Hayır, Öğrenme", lambda: self._reject_learned(learned))],
        )

    def _confirm_learned(self, corrections):
        for correction in corrections:
            if correction in self.vocabulary.corrections:
                self.vocabulary.confirm(correction)
        log.info("öğrenilen düzeltme doğrulandı: %d kayıt", len(corrections))
        self.status_bar.showMessage("Doğrulandı — sonraki diktelerde otomatik düzeltilecek.", 5000)

    def _reject_learned(self, corrections):
        for correction in corrections:
            self.vocabulary.remove_correction(correction.wrong)
            word = self.vocabulary.find_word(correction.right)
            if word is not None and word.source != MANUAL:
                self.vocabulary.remove_word(word.text)
        log.info("öğrenilen düzeltme reddedildi: %d kayıt", len(corrections))
        self.status_bar.showMessage("Tamam, bu düzeltme öğrenilmedi.", 4000)

    def shutdown(self):
        self._timer.stop()
        self._maybe_learn(force=True)
        if self.recorder.recording:
            self.recorder.stop()
        for thread in (self.worker, self.loader):
            if thread is not None and thread.isRunning():
                thread.wait(15000)
