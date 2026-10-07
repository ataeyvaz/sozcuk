"""Ses / video dosyasından yazıya dökme (mp3, wav, mp4, m4a, ogg/opus, flac, mkv…).

GİZLİLİK: Tüm işlem bu bilgisayarda yapılır; ses de çıkan metin de hiçbir sunucuya gönderilmez. İnternet
yalnızca ilk kullanımda Whisper modelini bir kez indirmek için gerekir (dikteyle aynı Hugging Face önbelleği).

Model: "Dengeli" (small) dikteyle ORTAKTIR (aynı yüklü model, ek indirme yok). "Hızlı" (base) ve "Hassas"
(medium) isteğe bağlıdır. Ses çözme için PyAV (av) gerekir — mikrofon diktesi buna ihtiyaç duymaz.
"""

import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QVBoxLayout,
)

from . import dictation, logbook, theme

log = logbook.get("dosyadan-yazi")

EXTENSIONS = ("mp3", "wav", "m4a", "aac", "ogg", "opus", "flac", "wma", "amr",
              "mp4", "m4v", "mov", "mkv", "webm", "avi", "mpeg", "mpg", "3gp")

# kalite → (model, açıklama)
QUALITY = {
    "Hızlı":   ("base", "~145 MB; en hızlı, daha çok hata yapabilir"),
    "Dengeli": ("small", "~480 MB; önerilen, dikteyle ortak model"),
    "Hassas":  ("medium", "~1,5 GB; en doğru ama yavaş"),
}
BEAM = {"base": 1, "small": 3, "medium": 3}
LANGUAGES = (("Türkçe", "tr"), ("English", "en"), ("Otomatik algıla", "auto"))
PARAGRAPH_GAP = 1.5          # sn — bundan uzun sessizlikte yeni paragraf
PARAGRAPH_SOFT_CHARS = 700   # kesintisiz konuşmada cümle sonunda böl


# --- saf yardımcılar (arayüzden bağımsız, test edilir) ------------------------------------------------

def fmt_hms(seconds):
    s = max(0, int(seconds))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def fmt_srt_time(seconds):
    ms = int(round(max(0.0, seconds) * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def build_paragraphs(segments, gap=PARAGRAPH_GAP):
    """segments: [(başlangıç, bitiş, metin)] → [(paragraf başlangıcı, metin)]"""
    paras = []
    prev_end = None
    for start, end, text in segments:
        text = text.strip()
        if not text:
            continue
        new_para = not paras
        if prev_end is not None and start - prev_end > gap:
            new_para = True
        if (not new_para and sum(len(t) for t in paras[-1][1]) > PARAGRAPH_SOFT_CHARS
                and paras[-1][1][-1].rstrip().endswith((".", "!", "?", "…"))):
            new_para = True
        if new_para:
            paras.append([start, []])
        paras[-1][1].append(text)
        prev_end = end
    return [(s, " ".join(parts)) for s, parts in paras]


def render_text(segments, timestamps=False, gap=PARAGRAPH_GAP):
    out = []
    for start, text in build_paragraphs(segments, gap):
        out.append(f"[{fmt_hms(start)}] {text}" if timestamps else text)
    return "\n\n".join(out)


def render_srt(segments):
    blocks, n = [], 0
    for start, end, text in segments:
        text = text.strip()
        if not text:
            continue
        n += 1
        blocks.append(f"{n}\n{fmt_srt_time(start)} --> {fmt_srt_time(end)}\n{text}\n")
    return "\n".join(blocks)


def fmt_duration(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


# --- model ---------------------------------------------------------------------------------------------

_models = {}
_models_lock = threading.Lock()


def decoder_available():
    """PyAV gerçekten var mı? (dikte, eksikse boş bir 'av' modülü koyar; onunla dosya çözülemez.)"""
    try:
        import av
        return hasattr(av, "open")
    except ImportError:
        return False


def _get_model(size, on_status):
    if size == dictation.MODEL_SIZE:
        return dictation._load_model(on_status)       # dikteyle aynı model
    with _models_lock:
        if size in _models:
            return _models[size]
        _models.clear()                                # aynı anda tek ek model: bellek şişmesin
        from faster_whisper import WhisperModel
        kwargs = {"device": "cpu", "compute_type": "int8"}
        try:
            model = WhisperModel(size, local_files_only=True, **kwargs)
        except Exception:
            info = next(v[1] for v in QUALITY.values() if v[0] == size)
            on_status(f"Model indiriliyor, bu işlem bir kez yapılır ({info.split(';')[0]})…")
            try:
                model = WhisperModel(size, **kwargs)
            except Exception as exc:
                log.error("model indirilemedi: %s", exc)
                raise dictation.DictationError(
                    "Model indirilemedi. İnternet bağlantınızı kontrol edip yeniden deneyin "
                    "(model yalnızca ilk kullanımda bir kez indirilir).") from exc
        _models[size] = model
        return model


class FileTranscribeWorker(QThread):
    """Dosyayı arka planda yazıya döker; segmentleri tembel tüketir (bellekte biriktirmez)."""

    status = Signal(str)
    info = Signal(float, str)               # süre (sn), algılanan dil
    segment = Signal(float, float, str)
    finished_state = Signal(str, str)       # done | cancelled | net | error, mesaj

    def __init__(self, path, language, quality, parent=None):
        super().__init__(parent)
        self.path, self.language, self.quality = path, language, quality
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            if not decoder_available():
                raise dictation.DictationError(
                    "Bu sürümde ses çözücü (PyAV) bulunamıyor; dosyadan yazıya dökme kullanılamaz.")
            size = QUALITY[self.quality][0]
            model = _get_model(size, self.status.emit)
            if self._cancel.is_set():
                self.finished_state.emit("cancelled", "")
                return
            self.status.emit("Yazıya dökülüyor…")
            started = time.monotonic()
            segments, info = model.transcribe(
                self.path,
                language=None if self.language == "auto" else self.language,
                beam_size=BEAM[size],
                vad_filter=True,                       # sessizlikleri atla
                vad_parameters={"min_silence_duration_ms": 500},
                condition_on_previous_text=False,      # uzun seslerde tekrar döngüsüne girmesin
            )
            self.info.emit(float(info.duration), info.language)
            count = 0
            for seg in segments:
                if self._cancel.is_set():
                    self.finished_state.emit("cancelled", "")
                    return
                self.segment.emit(float(seg.start), float(seg.end), seg.text.strip())
                count += 1
            log.info("dosya yazıya döküldü: ses=%.1f sn süre=%.1f sn segment=%d model=%s",
                     info.duration, time.monotonic() - started, count, size)
            self.finished_state.emit("done", "")
        except dictation.DictationError as exc:
            log.warning("dosyadan yazı sonuçsuz: %s", exc)
            self.finished_state.emit("net" if "indirilemedi" in str(exc) else "error", str(exc))
        except Exception as exc:
            log.exception("dosyadan yazıya dökme hatası")
            self.finished_state.emit(
                "error", f"Dosya yazıya dökülemedi: {exc}\n\nDosya bozuk ya da desteklenmeyen biçimde olabilir.")


# --- pencere -------------------------------------------------------------------------------------------

class FileTranscribeDialog(QDialog):
    """Ses/video dosyası seç → yazıya dök → belgeye ekle / kopyala / .txt / .srt kaydet. Modsuzdur:
    işlem sürerken belgede çalışmaya devam edilebilir."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self.setWindowTitle("Ses / Video Dosyasından Yazıya Dök")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(720, 580)
        self.setAcceptDrops(True)
        self.path = ""
        self.segments = []
        self.worker = None
        self.duration = 0.0
        self._started_at = 0.0
        self._programmatic = False
        self._dirty = False
        self._build()

    # -- arayüz --
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        note = QLabel("🔒 Her şey bu bilgisayarda çalışır: ses ve metin hiçbir sunucuya gönderilmez.")
        note.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        layout.addWidget(note)

        row = QHBoxLayout()
        self.file_label = QLabel("Dosya seçilmedi — buraya sürükleyip bırakabilirsiniz")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        pick = QPushButton("Dosya Seç…")
        pick.clicked.connect(self.pick_file)
        row.addWidget(self.file_label, 1)
        row.addWidget(pick)
        layout.addLayout(row)

        options = QHBoxLayout()
        options.addWidget(QLabel("Dil:"))
        self.language = QComboBox()
        for text, code in LANGUAGES:
            self.language.addItem(text, code)
        options.addWidget(self.language)
        options.addSpacing(12)
        options.addWidget(QLabel("Kalite:"))
        self.quality = QComboBox()
        for name in QUALITY:
            self.quality.addItem(name)
        self.quality.setCurrentText("Dengeli")
        self.quality.currentTextChanged.connect(self._quality_note)
        options.addWidget(self.quality)
        options.addSpacing(12)
        self.timestamps = QCheckBox("Zaman damgası ekle")
        self.timestamps.toggled.connect(self._timestamps_toggled)
        options.addWidget(self.timestamps)
        options.addStretch()
        layout.addLayout(options)
        self.quality_note = QLabel()
        self.quality_note.setStyleSheet(f"color:{theme.TEXT_MUTED};")
        layout.addWidget(self.quality_note)
        self._quality_note()

        run = QHBoxLayout()
        self.start_button = QPushButton("Yazıya Dök")
        self.start_button.setDefault(True)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        run.addWidget(self.start_button)
        run.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        run.addWidget(self.progress, 1)
        self.progress_label = QLabel()
        self.progress_label.setMinimumWidth(200)
        run.addWidget(self.progress_label)
        layout.addLayout(run)

        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Yazıya dökülen metin burada görünür; eklemeden önce düzenleyebilirsiniz.")
        self.text.textChanged.connect(self._text_changed)
        layout.addWidget(self.text, 1)

        buttons = QHBoxLayout()
        self.insert_button = QPushButton("Belgeye Ekle")
        self.insert_button.clicked.connect(self.insert_into_document)
        copy = QPushButton("Panoya Kopyala")
        copy.clicked.connect(self.copy_text)
        save_txt = QPushButton(".txt Kaydet…")
        save_txt.clicked.connect(lambda: self.save_as(".txt"))
        save_srt = QPushButton(".srt Kaydet…")
        save_srt.clicked.connect(lambda: self.save_as(".srt"))
        close = QPushButton("Kapat")
        close.clicked.connect(self.close)
        for b in (self.insert_button, copy, save_txt, save_srt):
            buttons.addWidget(b)
        buttons.addStretch()
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def _quality_note(self, *_):
        name = self.quality.currentText()
        self.quality_note.setText(f"{name}: {QUALITY[name][1]}. Model ilk kullanımda bir kez indirilir.")

    # -- dosya seçimi --
    def pick_file(self):
        patterns = " ".join(f"*.{e}" for e in EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Ses ya da video dosyası seç", "", f"Ses ve video ({patterns});;Tüm dosyalar (*.*)")
        if path:
            self.set_file(path)

    def set_file(self, path):
        if self.worker is not None:
            return
        self.path = path
        self.file_label.setText(f"🎵  {os.path.basename(path)}")
        self.file_label.setStyleSheet("")
        self.start_button.setEnabled(True)
        self.progress.setValue(0)
        self.progress_label.setText("")

    @staticmethod
    def _dropped(event):
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and Path(local).suffix.lower().lstrip(".") in EXTENSIONS:
                return local
        return ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and self._dropped(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        path = self._dropped(event)
        if path:
            self.set_file(path)

    # -- çalıştırma --
    def start(self):
        if not self.path or self.worker is not None:
            return
        if not os.path.exists(self.path):
            QMessageBox.warning(self, "Yazıya Dök", "Dosya bulunamadı.")
            return
        self.segments = []
        self._dirty = False
        self._set_text("")
        self.text.setReadOnly(True)
        self.duration = 0.0
        self._started_at = time.monotonic()
        self.progress.setValue(0)
        self.progress_label.setText("Hazırlanıyor…")
        for w in (self.start_button, self.language, self.quality):
            w.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = FileTranscribeWorker(self.path, self.language.currentData(), self.quality.currentText(), self)
        self.worker.status.connect(lambda m: self.progress_label.setText(m[:60]))
        self.worker.info.connect(self._on_info)
        self.worker.segment.connect(self._on_segment)
        self.worker.finished_state.connect(self._on_finished)
        self.worker.start(QThread.Priority.LowPriority)        # arayüz ve diğer programlar yavaşlamasın

    def cancel(self):
        if self.worker is not None:
            self.cancel_button.setEnabled(False)
            self.progress_label.setText("İptal ediliyor…")
            self.worker.cancel()

    def shutdown(self):
        """Ana pencere kapanırken çağrılır."""
        if self.worker is not None:
            self.worker.cancel()
            self.worker.wait(8000)

    def closeEvent(self, event):
        if self.worker is not None:
            answer = QMessageBox.question(
                self, "Yazıya Dök", "İşlem sürüyor. İptal edilip pencere kapatılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.shutdown()
        event.accept()

    def _on_info(self, duration, language):
        self.duration = duration
        self._started_at = time.monotonic()
        self.main.statusBar().showMessage(f"Yazıya dökülüyor (algılanan dil: {language})", 5000)

    def _on_segment(self, start, end, text):
        self.segments.append((start, end, text))
        if self.duration > 0:
            fraction = min(1.0, end / self.duration)
            self.progress.setValue(int(fraction * 100))
            elapsed = time.monotonic() - self._started_at
            if fraction > 0.03:
                remaining = elapsed * (1 - fraction) / fraction
                self.progress_label.setText(f"%{int(fraction * 100)} · kalan ~{fmt_duration(remaining)}")
            else:
                self.progress_label.setText(f"%{int(fraction * 100)}")
        self._render()

    def _on_finished(self, state, message):
        worker, self.worker = self.worker, None
        worker.wait()
        worker.deleteLater()
        self._render()
        self.text.setReadOnly(False)
        for w in (self.start_button, self.language, self.quality):
            w.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if state == "done":
            self.progress.setValue(100)
            self.progress_label.setText("✅ Tamamlandı" if self.segments else "Konuşma bulunamadı")
        elif state == "cancelled":
            self.progress_label.setText("İptal edildi — metin korundu")
        elif state == "net":
            self.progress_label.setText("Model indirilemedi")
            QMessageBox.warning(self, "Model indirilemedi", message)
        else:
            self.progress_label.setText("Hata")
            QMessageBox.critical(self, "Yazıya Dök", message or "Bilinmeyen hata")

    # -- metin alanı --
    def _set_text(self, value):
        self._programmatic = True
        self.text.setPlainText(value)
        self._programmatic = False

    def _render(self):
        if self._dirty and self.worker is None:
            return                                       # kullanıcı düzenlediyse üzerine yazma
        self._set_text(render_text(self.segments, self.timestamps.isChecked()))
        if self.worker is not None:
            bar = self.text.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _text_changed(self):
        if not self._programmatic:
            self._dirty = True

    def _timestamps_toggled(self, _):
        if self.worker is None and self._dirty and self.segments:
            self.progress_label.setText("Metin düzenlendiği için bu seçenek yalnızca yeni yazıya dökmede geçerli")
            return
        self._render()

    # -- çıktı --
    def _has_text(self):
        if not self.text.toPlainText().strip():
            QMessageBox.information(self, "Yazıya Dök", "Henüz metin yok.")
            return False
        return True

    def copy_text(self):
        if self._has_text():
            QGuiApplication.clipboard().setText(self.text.toPlainText())
            self.main.statusBar().showMessage("Metin panoya kopyalandı.", 4000)

    def insert_into_document(self):
        if not self._has_text():
            return
        text = self.text.toPlainText().strip()
        corrected = 0
        vocabulary = getattr(self.main, "vocabulary", None)
        if vocabulary is not None:                       # dikte sözlüğü düzeltmeleri aynen uygulanır
            text, corrected = vocabulary.apply(text)
        editor = self.main.editor
        cursor = editor.textCursor()
        cursor.beginEditBlock()                          # tek adım: Ctrl+Z hepsini geri alır
        cursor.insertText(text.replace("\n\n", "\n"))    # her paragraf ayrı Word paragrafı olur
        cursor.endEditBlock()
        editor.setTextCursor(cursor)
        editor.setFocus()
        suffix = f" ({corrected} sözlük düzeltmesi uygulandı)" if corrected else ""
        self.main.statusBar().showMessage(f"Yazıya dökülen metin belgeye eklendi.{suffix}", 5000)
        log.info("belgeye eklendi: karakter=%d düzeltme=%d", len(text), corrected)

    def save_as(self, extension):
        if extension == ".srt":
            if not self.segments:
                QMessageBox.information(self, "Yazıya Dök", "Henüz altyazı yok.")
                return
        elif not self._has_text():
            return
        base = Path(self.path).stem if self.path else "metin"
        filters = {".txt": "Metin (*.txt)", ".srt": "Altyazı (*.srt)"}
        start_dir = str(Path(self.path).parent / (base + extension)) if self.path else base + extension
        target, _ = QFileDialog.getSaveFileName(self, "Kaydet", start_dir, filters[extension])
        if not target:
            return
        try:
            content = render_srt(self.segments) if extension == ".srt" else self.text.toPlainText()
            Path(target).write_text(content, encoding="utf-8")
            self.main.statusBar().showMessage(f"Kaydedildi: {Path(target).name}", 5000)
        except OSError as exc:
            QMessageBox.critical(self, "Kaydedilemedi", str(exc))
