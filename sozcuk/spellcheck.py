"""Yazarken canlı yazım denetimi (Windows Yazım Denetimi API'si ile, bkz. spellengine.py).

- Değişen paragraf, yazmaya kısa bir ara verilince yeniden denetlenir; yazılmakta olan kelime, kelime
  bitene kadar işaretlenmez (Word gibi).
- Belge açılınca tam tarama arayüzü dondurmamak için küçük zaman dilimlerine bölünür (ölçüldü: paragraf
  başına ~6 ms; 1400 paragraflık belgede toplam ~8 sn) ve önce ekranda görünen bölümden başlar.
- Dikte sözlüğü ortak kişisel sözlüktür: oradaki kelimeler hata sayılmaz; "Sözlüğe Ekle" oraya yazar.

Tamamen yerel ve çevrimdışıdır; metin hiçbir yere gönderilmez.
"""

import time
from collections import deque

from PySide6.QtCore import QObject, QPointF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeySequence, QTextCursor
from PySide6.QtWidgets import QMenu, QMessageBox, QToolButton

from . import icons, logbook, theme, winlang
from .spellengine import ACTION_DELETE, ACTION_REPLACE, SpellEngine, SpellEngineUnavailable
from .vocabulary import tr_lower

log = logbook.get("yazım")

# testlerde değiştirilebilsin diye modül düzeyinde
engine_factory = SpellEngine
installer = winlang.install_turkish_spelling


class InstallWorker(QThread):
    """Windows bileşen kurulumunu (UAC onayı + indirme) arayüzü dondurmadan bekler."""

    done = Signal(str, object)

    def run(self):
        result, code = installer()
        self.done.emit(result, code)

RECHECK_DELAY_MS = 350
SLICE_MS = 25  # tam taramada tek seferde en fazla bu kadar çalış, sonra arayüze sıra ver
MAX_SYNC_BLOCKS = 4  # bundan fazla paragraf değiştiyse denetim zaman dilimli taramaya aktarılır


class SpellCheckController(QObject):
    def __init__(self, editor, vocabulary, status_bar, settings, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.vocabulary = vocabulary
        self.settings = settings
        self.ignored = set()          # "Tümünü Yoksay" — bu oturum boyunca
        self._known = vocabulary.known_words()
        self._dirty = []              # yeniden denetlenecek paragrafları izleyen imleçler
        self._scan_queue = deque()    # tam tarama: sıradaki paragraf konumları (imleç olarak)
        self._scan_started = time.monotonic()
        self.engine = None
        self.unavailable_reason = ""
        self.language_missing = False
        self._installer = None
        self._init_engine()

        self._recheck_timer = QTimer(self, singleShot=True, interval=RECHECK_DELAY_MS)
        self._recheck_timer.timeout.connect(self._recheck_dirty)
        self._scan_timer = QTimer(self, singleShot=True, interval=0)
        self._scan_timer.timeout.connect(self._scan_slice)

        self.button = self._build_button()
        status_bar.insertPermanentWidget(0, self.button)

        editor.document().contentsChange.connect(self._on_change)
        editor.issuesChanged.connect(self._update_button)
        editor.cursorPositionChanged.connect(self._on_cursor_moved)
        editor.issue_menu_hooks.append(self._issue_menu)
        vocabulary.listeners.append(self._vocabulary_changed)
        self._last_cursor_block = -1
        self._update_button()

    # --- durum ---------------------------------------------------------------

    def _init_engine(self):
        """Windows yazım denetimi motorunu başlatmayı dener; başarılıysa True."""
        try:
            started = time.monotonic()
            self.engine = engine_factory()
            self.unavailable_reason, self.language_missing = "", False
            log.info("Windows yazım denetimi hazır (%s, %.2f sn)", self.engine.language, time.monotonic() - started)
            return True
        except SpellEngineUnavailable as exc:
            self.engine = None
            self.unavailable_reason, self.language_missing = str(exc), exc.language_missing
            log.warning("yazım denetimi kullanılamıyor: %s", exc)
            return False

    @property
    def enabled(self):
        return self.engine is not None and self.settings.value("spell/live", True, type=bool)

    def _build_button(self):
        button = QToolButton()
        button.setIcon(icons.icon("spell_check", theme.TEXT_MUTED))
        button.setIconSize(QSize(20, 20))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")
        menu = QMenu(button)
        self.live_action = menu.addAction("Yazarken Yazım Denetimi")
        self.live_action.setCheckable(True)
        self.live_action.setChecked(self.enabled)
        self.live_action.toggled.connect(self._set_enabled)
        self.next_action = menu.addAction("Sonraki Yazım Hatası", self.go_to_next)
        self.next_action.setShortcut(QKeySequence("F7"))  # pencereye attach_shortcuts ile bağlanır
        self.reset_action = menu.addAction("Yoksayılan Kelimeleri Sıfırla", self._reset_ignored)
        # yalnızca Windows'ta Türkçe bileşeni eksikse görünür
        self.install_separator = menu.addSeparator()
        self.install_action = menu.addAction(icons.icon("spell_check"), "Türkçe Yazım Denetimini Windows'a Ekle…",
                                             self.install_language)
        self.settings_action = menu.addAction("Windows Dil Ayarlarını Aç", winlang.open_language_settings)
        self.retry_action = menu.addAction("Yeniden Dene", self._retry)
        menu.aboutToShow.connect(self._update_menu)
        button.setMenu(menu)
        return button

    def _update_menu(self):
        available = self.engine is not None
        installing = self._installer is not None and self._installer.isRunning()
        self.live_action.setEnabled(available)
        self.live_action.blockSignals(True)
        self.live_action.setChecked(self.enabled)
        self.live_action.blockSignals(False)
        self.next_action.setEnabled(available)
        self.reset_action.setEnabled(available)
        missing = not available and self.language_missing
        for action in (self.install_separator, self.install_action, self.settings_action, self.retry_action):
            action.setVisible(missing)
        self.install_action.setEnabled(not installing)

    def attach_shortcuts(self, window):
        window.addAction(self.next_action)

    def _update_button(self):
        if self._installer is not None and self._installer.isRunning():
            self.button.setText("Türkçe yazım denetimi ekleniyor…")
            self.button.setToolTip("Windows bileşeni indiriliyor ve kuruluyor; birkaç dakika sürebilir.")
            return
        if self.engine is None:
            self.button.setText("Türkçe yazım denetimi yüklü değil" if self.language_missing else "Yazım denetimi yok")
            self.button.setToolTip(self.unavailable_reason)
            return
        if not self.enabled:
            self.button.setText("Yazım denetimi kapalı")
            self.button.setToolTip("Yazarken yazım denetimi kapalı — açmak için tıklayın")
            return
        count = len(self.editor.issues)
        scanning = " (denetleniyor…)" if self._scan_queue else ""
        self.button.setText((f"{count} yazım hatası" if count else "Yazım hatası yok") + scanning)
        self.button.setToolTip("Windows yazım denetimi (Türkçe) — çevrimdışı. F7: sonraki hata")

    def _set_enabled(self, on):
        self.settings.setValue("spell/live", on)
        log.info("yazarken yazım denetimi: %s", "açık" if on else "kapalı")
        if on:
            self.recheck_all()
        else:
            self._dirty.clear()
            self._scan_queue.clear()
            self.editor.clear_issues()
        self._update_button()

    # --- değişiklikler -------------------------------------------------------

    def _on_change(self, position, removed, added):
        if not self.enabled or self.editor.bulk_loading:
            return  # belge yüklenirken değil; yükleme bitince recheck_all tek taramayla denetler
        doc = self.editor.document()
        if added > 5000:  # yapıştırma ya da belge yükleme: tam tarama daha verimli
            self.recheck_all()
            return
        end = min(position + added, doc.characterCount() - 1)
        block = doc.findBlock(position)
        while block.isValid() and block.position() <= end:
            self._dirty.append(QTextCursor(block))
            block = block.next()
        self._recheck_timer.start()

    def _on_cursor_moved(self):
        # kullanıcı yazdığı kelimeden ayrılınca (başka paragrafa geçince) o paragrafı hemen denetle
        number = self.editor.textCursor().blockNumber()
        if number != self._last_cursor_block and self._last_cursor_block >= 0 and self.enabled:
            block = self.editor.document().findBlockByNumber(self._last_cursor_block)
            if block.isValid():
                self._dirty.append(QTextCursor(block))
                self._recheck_timer.start()
        self._last_cursor_block = number

    def _recheck_dirty(self):
        blocks, seen = [], set()
        for cursor in self._dirty:
            block = cursor.block()
            if block.isValid() and block.blockNumber() not in seen:
                seen.add(block.blockNumber())
                blocks.append(block)
        self._dirty.clear()
        if len(blocks) > MAX_SYNC_BLOCKS:
            # çok paragraf birden değişti (büyük yapıştırma, geri alma): donmadan zaman dilimli tara
            if not self._scan_queue:
                self._scan_started = time.monotonic()
            self._scan_queue.extend(QTextCursor(block) for block in blocks)
            self._scan_timer.start()
            self._update_button()
            return
        for block in blocks:
            self.check_block(block)

    def recheck_all(self):
        """Belgenin tamamını zaman dilimlerine bölerek denetler; önce ekranda görünen bölümden başlar."""
        if not self.enabled:
            return
        doc = self.editor.document()
        view = self.editor
        top = view.mapToScene(view.viewport().rect().topLeft())
        first_visible = doc.documentLayout().hitTest(QPointF(0, max(0.0, top.y())), Qt.FuzzyHit)
        start_block = doc.findBlock(max(0, first_visible)).blockNumber() if first_visible >= 0 else 0
        order = list(range(start_block, doc.blockCount())) + list(range(0, start_block))
        self._scan_queue = deque(QTextCursor(doc.findBlockByNumber(n)) for n in order)
        self._scan_started = time.monotonic()
        self._scan_timer.start()
        self._update_button()

    def _scan_slice(self):
        deadline = time.monotonic() + SLICE_MS / 1000
        while self._scan_queue and time.monotonic() < deadline:
            block = self._scan_queue.popleft().block()
            if block.isValid():
                self.check_block(block, typing_guard=False)
        if self._scan_queue:
            self._scan_timer.start()
        else:
            log.info("tam tarama bitti: %d paragraf, %d hata, %.1f sn", self.editor.document().blockCount(),
                     len(self.editor.issues), time.monotonic() - self._scan_started)
        self._update_button()

    # --- denetim -------------------------------------------------------------

    def check_block(self, block, typing_guard=True):
        text = block.text()
        base = block.position()
        found = []
        if text.strip():
            cursor = self.editor.textCursor()
            typing_at = cursor.position() - base if typing_guard and cursor.block() == block else -1
            for start, length, action, replacement in self.engine.errors(text):
                word = text[start:start + length]
                if action != ACTION_DELETE:
                    if start + length == typing_at:
                        continue  # kelime hâlâ yazılıyor
                    if self._is_known(word):
                        continue
                suggestions = self._suggestions_for(word, action, replacement)
                found.append((base + start, length, suggestions, "", "yazım"))
        self.editor.replace_issues(base, base + len(text), found)

    def _suggestions_for(self, word, action, replacement):
        if action == ACTION_DELETE:
            return [""]
        if action == ACTION_REPLACE:
            return [replacement]
        return lambda: self.engine.suggest(word)

    def _is_known(self, word):
        lowered = tr_lower(word)
        if lowered in self.ignored or lowered in self._known:
            return True
        # Türkçe ek: "Ataberk'e" → sözlükte "Ataberk" varsa hata değil
        for mark in ("'", "’"):
            if mark in lowered and lowered.split(mark, 1)[0] in (self._known | self.ignored):
                return True
        return False

    # --- kullanıcı eylemleri -------------------------------------------------

    def _issue_menu(self, menu, issue):
        if issue.kind != "yazım":
            return
        word = issue.original
        menu.addAction("Tümünü Yoksay", lambda: self.ignore_all(word))
        menu.addAction(icons.icon("spell_check"), "Sözlüğe Ekle", lambda: self.add_to_dictionary(word))

    def ignore_all(self, word):
        self.ignored.add(tr_lower(word))
        self._drop_known_issues()

    def add_to_dictionary(self, word):
        base = word.split("'")[0].split("’")[0]
        if self.vocabulary.add_word(base):  # dikte sözlüğüne de girer: dikteye ipucu olur
            log.info("yazım denetiminden sözlüğe kelime eklendi")
        self.editor.window().statusBar().showMessage(
            f"“{base}” kişisel sözlüğe eklendi (yazım denetimi ve dikte için).", 4000)

    def _vocabulary_changed(self):
        self._known = self.vocabulary.known_words()
        self._drop_known_issues()

    def _drop_known_issues(self):
        self.editor.remove_issues(lambda issue: issue.kind == "yazım" and self._is_known(issue.original))

    def _reset_ignored(self):
        self.ignored.clear()
        self.recheck_all()

    # --- Windows'a Türkçe bileşeni ekleme -----------------------------------

    def install_language(self):
        """Riskleri açıklar, onay alınırsa Windows'un Türkçe yazım bileşenini (UAC onayıyla) ekler."""
        if self._installer is not None and self._installer.isRunning():
            return
        box = QMessageBox(self.editor.window())
        box.setWindowTitle("Türkçe Yazım Denetimini Windows'a Ekle")
        box.setIcon(QMessageBox.NoIcon)
        box.setText("<b>Windows'un Türkçe yazım denetimi bileşeni eklensin mi?</b>")
        box.setInformativeText(
            "• Microsoft'un resmî “Türkçe temel yazma” bileşeni (yazım denetimi ve sözlük) eklenir.\n"
            "• Ekran diliniz ve klavye düzeniniz değişmez.\n"
            "• Sistem genelinde bir değişiklik olduğu için Windows yönetici onayı isteyecek.\n"
            "• Bileşen Windows Update'ten indirilir; internet gerekir ve birkaç dakika sürebilir.\n"
            "• İstediğiniz zaman Ayarlar → Uygulamalar → İsteğe bağlı özellikler bölümünden kaldırabilirsiniz."
        )
        install = box.addButton("Ekle", QMessageBox.AcceptRole)
        box.addButton("Vazgeç", QMessageBox.RejectRole)
        box.setDefaultButton(install)
        box.exec()
        if box.clickedButton() is not install:
            return
        log.info("Türkçe yazım bileşeni kurulumu başlatıldı")
        self._installer = InstallWorker(self)
        self._installer.done.connect(self._install_finished)
        self._installer.start()
        self._update_button()

    def _install_finished(self, result, code):
        log.info("Türkçe yazım bileşeni kurulumu bitti: %s (kod %s)", result, code)
        status = self.editor.window().statusBar()
        if result == winlang.InstallResult.CANCELLED:
            status.showMessage("Yönetici onayı verilmedi; Windows'ta hiçbir değişiklik yapılmadı.", 6000)
        elif result == winlang.InstallResult.OK and self._init_engine():
            self.settings.setValue("spell/live", True)
            status.showMessage("Türkçe yazım denetimi eklendi ve açıldı.", 6000)
            self.recheck_all()
        elif result == winlang.InstallResult.OK:
            QMessageBox.information(
                self.editor.window(), "Yeniden başlatma gerekiyor",
                "Bileşen Windows'a eklendi, ancak etkinleşmesi için Sözcük'ü kapatıp yeniden açmanız gerekiyor.")
        else:
            box = QMessageBox(QMessageBox.Warning, "Eklenemedi",
                              "Türkçe yazım denetimi bileşeni eklenemedi. İnternet bağlantısı olmayabilir ya da "
                              "kurumunuzun Windows politikası buna izin vermiyor olabilir.\n\n"
                              "Windows Ayarları → Saat ve dil → Dil bölümünden Türkçe'yi ekleyerek de deneyebilirsiniz.",
                              parent=self.editor.window())
            open_settings = box.addButton("Dil Ayarlarını Aç", QMessageBox.AcceptRole)
            box.addButton("Kapat", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is open_settings:
                winlang.open_language_settings()
        self._update_button()

    def _retry(self):
        if self._init_engine():
            self.editor.window().statusBar().showMessage("Türkçe yazım denetimi bulundu ve açıldı.", 5000)
            self.recheck_all()
        else:
            self.editor.window().statusBar().showMessage(self.unavailable_reason, 6000)
        self._update_button()

    def go_to_next(self):
        """F7: sonraki yazım hatasını seçer ve önerileri gösterir."""
        if not self.editor.issues:
            self.editor.window().statusBar().showMessage("Belgede yazım hatası yok.", 3000)
            return
        issue = self.editor.next_issue(self.editor.textCursor().position())
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(issue.start)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        rect = self.editor.mapFromScene(self.editor.cursor_rect().bottomLeft())
        QTimer.singleShot(0, lambda: self.editor.show_context_menu(self.editor.viewport().mapToGlobal(rect)))
