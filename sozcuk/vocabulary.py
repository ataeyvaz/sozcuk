"""Dikte sözlüğü: konuşma tanımaya ipucu verilen kelimeler ve dikte metnine uygulanan düzeltmeler.

İki tür kayıt vardır:
- Kelime: özel adlar, terimler ("Gülbeyaz Yılmazer", "PySide"). Whisper'a ipucu olarak verilir.
- Düzeltme: yanlış → doğru ("Ara yüzünü" → "arayüzünü"). Dikte edilen metne sonradan uygulanır.

Her kayıt ya kullanıcı tarafından elle eklenir / doğrulanır (MANUAL, hemen etkin) ya da kullanıcının
dikte edilen metinde yaptığı düzeltmelerden öğrenilir (LEARNED). Öğrenilen bir düzeltme, yanlış öğrenmeye
karşı en az iki kez görülünce ya da kullanıcı doğrulayınca otomatik uygulanır.

Neden yazım denetimi yetmiyor: dikte bir kelimeyi başka bir GEÇERLİ kelimeye çevirebilir ("diktek" →
"tiktik"; ölçüldü: Word ve Windows yazım denetimi "tiktik"i doğru sayıyor). Bunu yalnızca doğrulanmış
yanlış → doğru kaydı yakalar.

Sözlük yalnızca bu bilgisayarda bir JSON dosyasında tutulur. Bu modül Qt'ye bağımlı değildir.
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

MANUAL = "elle"
LEARNED = "öğrenildi"
LEARN_THRESHOLD = 2          # öğrenilen düzeltme bu kadar görülünce otomatik uygulanır
HINT_TOKEN_BUDGET = 120      # ölçüldü: gerçekçi listelerde ~190 token'a kadar sorun yok; güvenli pay
MAX_PHRASE_WORDS = 3
MIN_SIMILARITY = 0.6

WORD_RE = re.compile(r"\w+(?:['’]\w+)*", re.UNICODE)


# --- Türkçe büyük/küçük harf -------------------------------------------------

def tr_lower(text):
    return text.replace("I", "ı").replace("İ", "i").lower()


def tr_capitalize(text):
    if not text:
        return text
    first = {"i": "İ", "ı": "I"}.get(text[0], text[0].upper())
    return first + text[1:]


def _now():
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Word:
    text: str
    source: str = MANUAL
    uses: int = 0
    added: str = field(default_factory=_now)


@dataclass
class Correction:
    wrong: str
    right: str
    source: str = MANUAL
    count: int = 1
    added: str = field(default_factory=_now)

    @property
    def active(self):
        return self.source == MANUAL or self.count >= LEARN_THRESHOLD


class Vocabulary:
    def __init__(self, path):
        self.path = Path(path)
        self.words = []
        self.corrections = []
        self.listeners = []  # sözlük değişince çağrılır (ör. yazım denetimi yeni kelimenin çizgisini kaldırsın)
        self.load()

    def known_words(self):
        """Yazım denetiminde hata sayılmayacak tek kelimeler (Türkçe küçük harfle): kelimeler ve
        doğrulanmış düzeltmelerin doğru halleri."""
        known = set()
        for text in [w.text for w in self.words] + [c.right for c in self.corrections if c.active]:
            known.update(tr_lower(token) for token in WORD_RE.findall(text))
        return known

    # --- dosya -----------------------------------------------------------------

    def load(self):
        self.words, self.corrections = [], []
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.words = [Word(**item) for item in data.get("words", [])]
            self.corrections = [Correction(**item) for item in data.get("corrections", [])]
        except (OSError, ValueError, TypeError):
            # bozuk dosyayı kaybetmeden kenara al, boş sözlükle devam et
            try:
                self.path.replace(self.path.with_suffix(f".bozuk-{datetime.now():%Y%m%d-%H%M%S}.json"))
            except OSError:
                pass
            self.words, self.corrections = [], []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"words": [asdict(w) for w in self.words], "corrections": [asdict(c) for c in self.corrections]}
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        for listener in list(self.listeners):
            listener()

    # --- kelimeler ---------------------------------------------------------------

    def find_word(self, text):
        key = tr_lower(text.strip())
        return next((w for w in self.words if tr_lower(w.text) == key), None)

    def add_word(self, text, source=MANUAL):
        """Kelimeyi ekler; yeni eklendiyse True. Öğrenilmiş bir kelime elle eklenirse onaylanmış sayılır."""
        text = " ".join(text.split())
        if not text or not WORD_RE.search(text):
            return False
        existing = self.find_word(text)
        if existing:
            if source == MANUAL and existing.source != MANUAL:
                existing.source = MANUAL
                self.save()
            return False
        self.words.append(Word(text, source))
        self.save()
        return True

    def remove_word(self, text):
        word = self.find_word(text)
        if word:
            self.words.remove(word)
            self.save()

    # --- düzeltmeler -------------------------------------------------------------

    def find_correction(self, wrong):
        key = tr_lower(" ".join(wrong.split()))
        return next((c for c in self.corrections if tr_lower(c.wrong) == key), None)

    def add_correction(self, wrong, right, source=MANUAL):
        wrong, right = " ".join(wrong.split()), " ".join(right.split())
        if not wrong or not right or tr_lower(wrong) == tr_lower(right):
            return None
        existing = self.find_correction(wrong)
        if existing:
            if tr_lower(existing.right) == tr_lower(right):
                existing.count += 1
            else:
                existing.right, existing.count = right, 1
            if source == MANUAL:
                existing.source = MANUAL
            self.save()
            return existing
        correction = Correction(wrong, right, source)
        self.corrections.append(correction)
        self.save()
        return correction

    def remove_correction(self, wrong):
        correction = self.find_correction(wrong)
        if correction:
            self.corrections.remove(correction)
            self.save()

    def confirm(self, entry):
        """Öğrenilmiş bir kaydı onaylar (elle eklenmiş gibi hemen etkin olur)."""
        entry.source = MANUAL
        self.save()

    # --- dikte sırasında ---------------------------------------------------------

    def hint_candidates(self):
        """İpucu olarak verilecek kelimeler, önem sırasıyla: elle eklenen kelimeler (yeniden eskiye),
        doğrulanmış düzeltmelerin doğru halleri (ör. "tiktik" → "diktek" için "diktek": model kelimeyi zamanla
        ilk seferde doğru duysun), sonra en çok kullanılan öğrenilmiş kelimeler.
        Liste bütçeyi aşarsa sondan kesilir (bkz. build_hint)."""
        manual = sorted((w for w in self.words if w.source == MANUAL), key=lambda w: w.added, reverse=True)
        learned = sorted((w for w in self.words if w.source != MANUAL), key=lambda w: (w.uses, w.added), reverse=True)
        verified = sorted((c for c in self.corrections if c.source == MANUAL), key=lambda c: c.added, reverse=True)
        result, seen = [], set()
        for text in [w.text for w in manual] + [c.right for c in verified] + [w.text for w in learned]:
            if tr_lower(text) not in seen:
                seen.add(tr_lower(text))
                result.append(text)
        return result

    def apply(self, text):
        """Etkin düzeltmeleri uygular; (yeni metin, uygulanan düzeltme sayısı) döndürür."""
        applied = 0
        for correction in sorted((c for c in self.corrections if c.active), key=lambda c: len(c.wrong), reverse=True):
            text, n = _replace_phrase(text, correction.wrong, correction.right)
            applied += n
        return text, applied

    def note_used(self, text):
        """Tanınan metinde geçen sözlük kelimelerinin kullanım sayısını artırır (sıralama için)."""
        lowered = tr_lower(text)
        changed = False
        for word in self.words:
            if _find_phrase(lowered, tr_lower(word.text)):
                word.uses += 1
                changed = True
        if changed:
            self.save()

    def learn(self, original, edited):
        """Kullanıcının dikte edilen metinde yaptığı düzeltmelerden öğrenir; öğrenilen düzeltmeleri döndürür."""
        learned = []
        for wrong, right in replaced_phrases(original, edited):
            if any(ch.isdigit() for ch in wrong + right):
                continue
            # yalnızca aynı kelimenin yazımı düzeltildiyse öğren; anlamı değiştiren düzenlemeleri atla
            similarity = SequenceMatcher(None, tr_lower(wrong).replace(" ", ""), tr_lower(right).replace(" ", "")).ratio()
            if similarity < MIN_SIMILARITY:
                continue
            correction = self.add_correction(wrong, right, LEARNED)
            if correction is None:
                continue
            if right[:1].isupper() and len(right) >= 3:
                self.add_word(right, LEARNED)  # özel ad gibi görünüyor: tanımaya da ipucu olsun
            learned.append(correction)
        return learned


def replaced_phrases(original, edited):
    """İki metin arasında kullanıcının değiştirdiği kısa ifadeler: [(orijinal, yeni), …]."""
    before, after = WORD_RE.findall(original), WORD_RE.findall(edited)
    matcher = SequenceMatcher(None, [tr_lower(w) for w in before], [tr_lower(w) for w in after], autojunk=False)
    return [
        (" ".join(before[i1:i2]), " ".join(after[j1:j2]))
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag == "replace" and i2 - i1 <= MAX_PHRASE_WORDS and j2 - j1 <= MAX_PHRASE_WORDS
    ]


def recognized_counterpart(original, edited, phrase):
    """Kullanıcının düzelttiği ifadenin (phrase), dikte edilen orijinal metindeki karşılığı; yoksa None."""
    key = tr_lower(" ".join(phrase.split()))
    for wrong, right in replaced_phrases(original, edited):
        if tr_lower(right) == key or key in tr_lower(right).split():
            return wrong
    return None


def build_hint(words, count_tokens=None):
    """Kelimeleri ipucu metnine çevirir; count_tokens verilirse token bütçesini aşanlar eklenmez.
    Ölçüldü: gerçekçi Türkçe listelerde ~190 token'a kadar tanıma bozulmadı; yapay/uzun listeler ise
    başa uydurma metin ekletti. Bu yüzden güvenli bir bütçe uygulanır."""
    chosen = []
    for text in words:
        if count_tokens is not None and count_tokens(", ".join(chosen + [text])) > HINT_TOKEN_BUDGET:
            break
        chosen.append(text)
    return ", ".join(chosen) or None


# ifadedeki kelimeler arasında yalnızca boşluk/sekme eşleşir: satır sonu (paragraf) üzerinden eşleşip
# iki paragrafı birleştirmesin
_GAP = r"[ \t ]+"


def _find_phrase(lowered_text, lowered_phrase):
    pattern = r"(?<!\w)" + _GAP.join(map(re.escape, lowered_phrase.split())) + r"(?!\w)"
    return re.search(pattern, lowered_text)


def _replace_phrase(text, wrong, right):
    """Türkçe harf duyarsız, kelime sınırına saygılı değiştirme; ilk harfin büyüklüğü korunur."""
    lowered = tr_lower(text)
    if len(lowered) != len(text):  # nadir: küçültme karakter sayısını değiştirdi, güvenli tarafta kal
        return text, 0
    pattern = re.compile(r"(?<!\w)" + _GAP.join(map(re.escape, tr_lower(wrong).split())) + r"(?!\w)")
    result, last, count = [], 0, 0
    for match in pattern.finditer(lowered):
        start, end = match.span()
        # büyük harfi yalnızca cümle başında koru: Whisper cümle ortasında da gereksiz büyük harf yazabiliyor
        sentence_start = not text[:start].strip() or text[:start].rstrip()[-1] in ".!?…:\n"
        replacement = tr_capitalize(right) if sentence_start and right[:1].islower() else right
        result.append(text[last:start])
        result.append(replacement)
        last, count = end, count + 1
    result.append(text[last:])
    return "".join(result), count
