"""Türkçe telaffuz: metni okunacak biçime getirir ve ses birimlerine (IPA) çevirir — sesli okuma için.

Neden kendi kodumuz: Piper ses modelleri metni espeak-ng ile ses birimlerine çeviriyor. espeak-ng GPL lisanslı
(uygulamanın tamamını GPL yapardı) ve Türkçede yanlışları var: "Dr." → "dere", "hâlâ"yı kalın l ile, "konuşmaya"yı
olumsuzluk eki sanıp yanlış vurguyla okuyor. Türkçe yazım okunuşa çok yakın olduğu için kurallar burada.

İşaretler espeak'in Türkçe çıktısıyla aynı tutuldu (eğitimde temel alınan model bunlarla eğitildi); kurallar espeak'in
5.600 kelimelik çıktısından ölçüldü, espeak'in yanlış yaptığı yerde Türkçe dil bilgisi uygulanır:
- ünlüler: açık hecede a e ɯ i o œ u y; kapalı hecede ve sözcük sonunda e→ɛ (l m n'den önce æ), i→ɪ, o→ɔ, u→ʊ, ü→ø
- l: sonraki (yoksa önceki) ünlü kalınsa ɫ; "hal, rol, alkol…" gibi alıntılarda sondaki l incedir
- r: iki ünlü arasında ɾ (tek vuruş), başka yerde r; g: ince ünlü yanında ɟ
- ğ: e/i'den sonra ünlü gelirse j ("değil" dejil), ı'dan sonra ɯ, diğer ünlüleri uzatır ("dağ" daː, "ağaç" aːtʃ)
- çift ünsüz uzar ("anne" anːɛ); â önceki k/g/l'yi inceltir ("kâr", "lâle"), başka yerde uzatır
- vurgu (ˈ ünlünün önüne): kural olarak son hece; -ma/-me olumsuzluğu, -yor, -dır, -ken, -(y)la, -sa, -ca gibi
  vurgusuz ekler vurguyu önceki heceye alır; "şimdi, Ankara, İstanbul…" gibi sözcükler kendi vurgusunu taşır
"""

import re
import unicodedata

VOWELS = set("aeıioöuüâîû")
FRONT = set("eiöüîâ")        # â: önceki ünsüzü incelttiği için ince sayılır ("lâle", "kâr")
BACK = set("aıouû")

# vurgusuz görevli sözcükler (vurgu işareti almaz)
UNSTRESSED_WORDS = {"ve", "de", "da", "ki", "mi", "mı", "mu", "mü", "ile", "ise", "te", "ta"}

# kendi vurgusunu taşıyan sözcükler: sözcük → vurgulu hecenin sırası (0 = ilk hece)
LEXICAL_STRESS = {
    "şimdi": 0, "sonra": 0, "belki": 0, "yarın": 0, "bugün": 0, "nasıl": 0, "niçin": 0, "nerede": 0, "nereye": 0,
    "nereden": 0, "hangi": 0, "çünkü": 0, "ama": 0, "fakat": 0, "ancak": 0, "yalnız": 0, "sadece": 0, "şöyle": 0,
    "böyle": 0, "öyle": 0, "hemen": 0, "henüz": 0, "yine": 0, "bazen": 0, "galiba": 0, "tabii": 0, "lütfen": 0,
    "merhaba": 0, "anne": 0, "baba": 0, "abla": 0, "amca": 0, "teyze": 0, "dayı": 0, "değil": 0, "acaba": 0,
    "aslında": 0, "herhalde": 0, "gerçekten": 1, "evet": 0, "hayır": 0, "peki": 0, "haydi": 0, "hadi": 0, "eğer": 0,
    "sanki": 0, "önce": 0, "kimse": 0, "herkes": 0, "biraz": 0, "bazı": 0, "neden": 0, "niye": 0, "rağmen": 0,
    "göre": 0, "gibi": 0, "diye": 0, "hiçbir": 0, "vardır": 0, "yoktur": 0, "budur": 0, "şudur": 0, "odur": 0,
    "ankara": 0, "istanbul": 1, "izmir": 0, "bursa": 0, "antalya": 1, "türkiye": 0, "avrupa": 1, "almanya": 1,
    "fransa": 0, "italya": 1, "amerika": 1, "ispanya": 1, "rusya": 0, "londra": 0, "paris": 0, "efendim": 1,
    "asla": 0, "yukarı": 0, "aşağı": 0, "ileri": 0, "geri": 0, "dışarı": 0, "içeri": 0,
}

# kendi vurgusunu taşıyan sözcüklere gelip vurguyu değiştirmeyen ekler ("ÖNceden", "ANnesi", "BAbalar")
_STRESS_SUFFIX = re.compile(r"(?:l[ae]r)?(?:[ıiuü]m[ıiuü]z|[ıiuü]n[ıiuü]z|s[ıiuü]|[ıiuü]m|[ıiuü]n|m|n|[ıiuü])?"
                            r"(?:n?[dt][ae](?:n|ki)?|[ny]?[ae]|[ny]?[ıiuü]|n?[ıiuü]n|y?l[ae]|ki)?"
                            r"(?:s[ıiuü]n(?:[ıiuü]z)?|y?[ıiuü][mz]|[dt][ıiuü]r)?$")   # kişi ekleri de vurgusuz

# sondaki l'si ince okunan alıntı sözcükler (sonrasına ek gelirse ekin ünlüsü zaten inceliği gösterir)
THIN_L_WORDS = {"hal", "hâl", "rol", "gol", "alkol", "futbol", "voleybol", "basketbol", "kontrol", "protokol",
                "petrol", "usul", "kabul", "meşgul", "mahsul", "hayal", "ihtimal", "istiklal", "misal", "kemal",
                "cemal", "celal", "hilal", "sual", "idrak", "ilan", "lal", "kalp", "hayali", "hala", "hâlâ"}

# -ma/-me ile bitip ek alan adlar (olumsuzluk eki sanılmasın: "sinemadan")
MA_NOUNS = ("sinema", "tema", "drama", "firma", "forma", "pijama", "lama", "kama", "dama", "panorama", "karizma",
            "dogma", "prizma", "sigma", "magma", "astma", "gama", "zama", "kinema", "ödeme", "cümle")

# "-ca/-ce" ile biten ama eki olmayan sözcükler (vurgu sonda kalır)
CA_EXCEPTIONS = {"düşünce", "karınca", "gonca", "kanca", "hınca"}

_NEG = re.compile(r"m[ae](?:d[ıiuü]|m[ıiuü]ş|z|y[ae]c[ae]k|s[ae]|s[ıi]n|"
                  r"y[ıi]n|d[ae]n|y[ae]n|d[ıi]k|y[ıi][mz])(?:m|n|k|[ıi]n|[ıi]z|lar|ler|n[ıi]z|s[ıi]n|s[ıi]n[ıi]z|"
                  r"d[ıi]r|ken|s[ae]|m[ıi]ş|d[ıi]|[ıi]m|y[ıi]z|y[ıi]m)?$")


def lower_tr(text):
    """Türkçe küçük harf: I → ı, İ → i."""
    return text.replace("I", "ı").replace("İ", "i").lower()


# =============================================================================
# Sayılar
# =============================================================================

ONES = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
TENS = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
SCALES = ["", "bin", "milyon", "milyar", "trilyon", "katrilyon"]


def _below_thousand(n):
    words = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        words += ([ONES[hundreds]] if hundreds > 1 else []) + ["yüz"]
    tens, ones = divmod(rest, 10)
    if tens:
        words.append(TENS[tens])
    if ones:
        words.append(ONES[ones])
    return words


def number_words(n):
    """Tam sayıyı Türkçe okunuşuna çevirir: 1250 → "bin iki yüz elli"."""
    if n == 0:
        return "sıfır"
    if n < 0:
        return "eksi " + number_words(-n)
    groups = []
    while n:
        n, group = divmod(n, 1000)
        groups.append(group)
    if len(groups) > len(SCALES):
        return " ".join(ONES[int(d)] or "sıfır" for d in str(n))
    words = []
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if not group:
            continue
        if index == 1 and group == 1:
            words.append("bin")       # "bir bin" denmez
        else:
            words += _below_thousand(group) + ([SCALES[index]] if index else [])
    return " ".join(words)


def ordinal_words(n):
    """Sıra sayısı: 3 → "üçüncü", 40 → "kırkıncı"."""
    words = number_words(n).split()
    last = words[-1]
    if last == "dört":
        last = "dörd"
    if last[-1] in VOWELS:
        suffix = "nc" + _harmony_high(last)
    else:
        vowel = _harmony_high(last)
        suffix = vowel + "nc" + vowel
    words[-1] = last + suffix
    return " ".join(words)


def _harmony_high(word):
    """Dar ünlü uyumu (ı, i, u, ü) — sözcüğün son ünlüsüne göre."""
    for char in reversed(word):
        if char in "aı":
            return "ı"
        if char in "ei":
            return "i"
        if char in "ou":
            return "u"
        if char in "öü":
            return "ü"
    return "i"


def _digits(text):
    return " ".join(ONES[int(d)] or "sıfır" for d in text)


def _read_number(text):
    """"1.250" (binlik ayraç) ve "3,5" (ondalık) dahil sayıyı okur."""
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        return number_words(int(text.replace(".", "")))
    whole, _, fraction = text.partition(",")
    if len(whole) > 15:
        return _digits(whole)
    words = number_words(int(whole)) if not (len(whole) > 1 and whole.startswith("0")) else _digits(whole)
    if fraction:
        fraction_words = _digits(fraction) if fraction.startswith("0") else number_words(int(fraction))
        words += " virgül " + fraction_words
    return words


# =============================================================================
# Metni okunacak biçime getirme
# =============================================================================

MONTHS = ["", "ocak", "şubat", "mart", "nisan", "mayıs", "haziran", "temmuz", "ağustos", "eylül", "ekim", "kasım",
          "aralık"]

ABBREVIATIONS = {
    "dr.": "doktor", "prof.": "profesör", "doç.": "doçent", "av.": "avukat", "sn.": "sayın", "vb.": "ve benzeri",
    "vs.": "vesaire", "örn.": "örneğin", "bkz.": "bakınız", "no.": "numara", "mah.": "mahallesi",
    "cad.": "caddesi", "sok.": "sokağı", "blv.": "bulvarı", "apt.": "apartmanı", "tel.": "telefon",
    "a.ş.": "anonim şirketi", "ltd.": "limitet", "şti.": "şirketi", "t.c.": "te ce", "yy.": "yüzyıl",
    "m.ö.": "milattan önce", "m.s.": "milattan sonra", "s.": "sayfa", "yrd.": "yardımcı", "öğr.": "öğretmen",
}
# yalnızca sayıdan sonra okunan birimler
UNITS = {
    "km": "kilometre", "m": "metre", "cm": "santimetre", "mm": "milimetre", "kg": "kilogram", "g": "gram",
    "mg": "miligram", "lt": "litre", "l": "litre", "ml": "mililitre", "sn": "saniye", "dk": "dakika", "sa": "saat",
    "tl": "lira", "mb": "megabayt", "gb": "gigabayt", "kb": "kilobayt", "tb": "terabayt", "kw": "kilovat",
    "mhz": "megahertz", "ghz": "gigahertz", "km/sa": "kilometre", "°c": "derece",
}
SYMBOLS = {"&": " ve ", "+": " artı ", "=": " eşittir ", "@": " et ", "₺": " lira ", "$": " dolar ", "€": " avro ",
           "£": " sterlin ", "°": " derece ", "×": " çarpı ", "÷": " bölü ", "§": " madde ", "#": " numara "}
LETTER_NAMES = {"a": "a", "b": "be", "c": "ce", "ç": "çe", "d": "de", "e": "e", "f": "fe", "g": "ge",
                "ğ": "yumuşak ge", "h": "he", "ı": "ı", "i": "i", "j": "je", "k": "ke", "l": "le", "m": "me",
                "n": "ne", "o": "o", "ö": "ö", "p": "pe", "q": "kü", "r": "re", "s": "se", "ş": "şe", "t": "te",
                "u": "u", "ü": "ü", "v": "ve", "w": "dabılyu", "x": "iks", "y": "ye", "z": "ze"}
# sözcük gibi okunan kısaltmalar
ACRONYM_WORDS = {"nato", "odtü", "aselsan", "tübitak", "nasa", "unesco", "unicef", "yök", "tüsiad", "havelsan",
                 "roketsan", "tusaş", "aşti", "iski", "aski", "buski", "tomer", "ösym"}


def _spell(acronym):
    return " ".join(LETTER_NAMES.get(char, char) for char in lower_tr(acronym))


def _acronym(match):
    word, suffix = match.group(1), match.group(2) or ""
    low = lower_tr(word)
    consonant_runs = re.findall(r"[^aeıioöuü]+", low)
    pronounceable = (low in ACRONYM_WORDS or (
        len(low) >= 3 and any(c in VOWELS for c in low) and low[0:2] != "".join(c for c in low[0:2] if c not in VOWELS)
        and all(len(run) <= 2 for run in consonant_runs) and low[-1] in VOWELS | set("nmrlkz")
        and not re.search(r"[^aeıioöuü]{2}$", low)))
    spoken = low if pronounceable else _spell(word)
    return spoken + lower_tr(suffix.lstrip("'’"))


def normalize(text):
    """Metni sesli okunacak biçime getirir: sayılar, saat, tarih, yüzde, kısaltmalar, simgeler → sözcük."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("…", "...")
    text = text.replace("–", " - ").replace("—", " - ")
    # tarih: 21.09.2026 / 21/09/2026
    text = re.sub(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b",
                  lambda m: (f"{number_words(int(m.group(1)))} {MONTHS[int(m.group(2))]} {number_words(int(m.group(3)))}"
                             if 1 <= int(m.group(2)) <= 12 else m.group(0)), text)
    # saat: 10:30, 10:30'da (09.05 değil: nokta tarih ya da ondalık olabilir)
    def clock(match):
        hour, minute, suffix = match.group(1), match.group(2), match.group(3) or ""
        spoken = number_words(int(hour))
        if minute != "00":
            spoken += " " + (_digits(minute) if minute.startswith("0") else number_words(int(minute)))
        return spoken + suffix
    text = re.sub(r"\b(\d{1,2}):(\d{2})\b(?:'([a-zçğıöşü]+))?", clock, text)
    # yüzde: %50, % 50, %50'si
    text = re.sub(r"%\s?(\d+(?:,\d+)?)(?:'([a-zçğıöşü]+))?",
                  lambda m: "yüzde " + _read_number(m.group(1)) + (m.group(2) or ""), text)
    # sıra sayısı: "3. sayfa" (ardından küçük harfle devam eden)
    text = re.sub(r"\b(\d+)\.(?=\s+[a-zçğıöşü])", lambda m: ordinal_words(int(m.group(1))), text)
    # sayı + birim: "5 km", "12 TL"
    def unit(match):
        name = UNITS.get(lower_tr(match.group(2)))
        return f"{match.group(1)} {name}" if name else match.group(0)
    text = re.sub(r"(\d)\s?([A-Za-z°/]+)(?![A-Za-zçğıöşüÇĞİÖŞÜ])", unit, text)
    # sayılar (eklerle: 2026'da → iki bin yirmi altıda)
    text = re.sub(r"(\d+(?:\.\d{3})*(?:,\d+)?)(?:'([a-zçğıöşü]+))?",
                  lambda m: _read_number(m.group(1)) + (m.group(2) or ""), text)
    # kısaltmalar
    def abbreviation(match):
        spoken = ABBREVIATIONS.get(lower_tr(match.group(0)))
        return spoken if spoken else match.group(0)
    text = re.sub(r"(?<![\wçğıöşüÇĞİÖŞÜ])(?:[A-Za-zÇĞİÖŞÜçğıöşü]{1,4}\.){1,3}", abbreviation, text)
    # büyük harfli kısaltmalar: THY'nin → te ha yenin, NATO → nato
    text = re.sub(r"\b([A-ZÇĞİÖŞÜ]{2,})('[a-zçğıöşü]+)?\b", _acronym, text)
    for symbol, spoken in SYMBOLS.items():
        text = text.replace(symbol, spoken)
    text = re.sub(r"(?<=\w)/(?=\w)", " ", text)
    return re.sub(r"[ \t]+", " ", text).strip()


# =============================================================================
# Sözcük → ses birimleri
# =============================================================================

def _vowel_positions(word):
    return [index for index, char in enumerate(word) if char in VOWELS]


def _stress_syllable(word, root=None):
    """Vurgulu hecenin sırası (0 = ilk hece); vurgusuz sözcükte None."""
    vowels = _vowel_positions(word)
    count = len(vowels)
    if count == 0 or word in UNSTRESSED_WORDS:
        return None
    last = count - 1
    if root and root in LEXICAL_STRESS:              # "Ankara'da": kök vurgusu korunur
        return min(LEXICAL_STRESS[root], last)
    if word in LEXICAL_STRESS:
        return min(LEXICAL_STRESS[word], last)
    for size in range(len(word) - 1, 2, -1):
        stem = word[:size]
        if stem in LEXICAL_STRESS and _STRESS_SUFFIX.fullmatch(word[size:]):
            return min(LEXICAL_STRESS[stem], last)
    if count == 1:
        return 0

    def before(position):
        """position (harf sırası) içeren hecenin bir öncesi."""
        syllable = sum(1 for v in vowels if v < position)
        return max(0, syllable - 1)

    # -m(ı/i/u/ü)yor: olumsuz şimdiki zaman → olumsuzluktan önceki hece ("gelmiyor" GEL-mi-yor)
    match = re.search(r"m[ıiuü]yor", word)
    if match and any(char in VOWELS for char in word[:match.start()]):
        return before(match.start())
    # -yor: "yor"dan önceki hece ("geliyor" ge-Lİ-yor)
    match = re.search(r"(?<=[aeıioöuüâîû])yor", word)
    if match:
        return before(match.start())
    # -ma/-me olumsuzluğu ("gelmedi", "yapmadan", "gelmez")
    if not word.startswith(MA_NOUNS):
        match = _NEG.search(word)
        if match and any(char in VOWELS for char in word[:match.start()]):
            return before(match.start())
    # ortaç -dığ/-acağ: vurgu ortaç hecesinde ("okuDUğum", "anlataCAğım")
    match = re.search(r"(?:[dt][ıiuü]|[ae]c[ae])ğ", word)
    if match and match.end() < len(word):
        return sum(1 for v in vowels if v < match.end() - 1) - 1
    # kişi ekleri -sınız/-siniz vurgusuz ("alabiLİRsiniz")
    match = re.search(r"s[ıiuü]n[ıiuü]z$", word)
    if match and count >= 3:
        return before(match.start())
    # gereklilik -malı/-meli: vurgu "ma" hecesinde ("gelMEli")
    match = re.search(r"m[ae]l[ıi](?:[ıi]m|s[ıi]n|y[ıi]z|s[ıi]n[ıi]z|l[ae]r|d[ıi]r|y[ıi]m)?$", word)
    if match and count >= 3 and any(char in VOWELS for char in word[:match.start()]):
        return sum(1 for v in vowels if v < match.start())
    # -dır ve türevleri (en az üç hece: "kaldır, indir, getir" gibi fiil kökleri karışmasın)
    match = re.search(r"[dt][ıiuü]r(?:lar|ler)?$", word)
    if match and count >= 3:
        return before(match.start())
    # -ken ("gelirken"), -(y)la/-(y)le, -lerle, -mekle, -sa/-se (koşul)
    for pattern in (r"(?<=[rzyşın])ken$", r"yl[ae]$", r"(?<=l[ae]r)l[ae]$", r"(?<=m[ae]k)l[ae]$",
                    r"(?<=[rz])s[ae](?:m|n|k|n[ıi]z|lar|ler)?$", r"(?<=y)s[ae](?:m|n|k|n[ıi]z)?$"):
        match = re.search(pattern, word)
        if match and (count >= 3 or "s[ae]" in pattern):
            return before(match.start())
    # -ca/-ce eki ("Türkçe", "Almanca", "gelince", "bence")
    match = re.search(r"(?<=[^aeıioöuüâîû])[cç][ae]$", word)
    if match and word not in CA_EXCEPTIONS:
        return before(match.start())
    return last


def _closed(word, index, vowels):
    """index'teki ünlünün hecesi kapalı mı (Türkçe hece bölme: ünlüler arasında tek ünsüz sonraki heceye geçer)."""
    after = word[index + 1:]
    if after.startswith("ğ"):
        # ğ önceki ünlüyü uzatır (açık hece gibi); e/i'den sonra ünsüz önünde y gibi okunur ("çiğdem" çɪjdem)
        return word[index] in "ei" and (len(after) < 2 or after[1] not in VOWELS)
    following = [v for v in vowels if v > index]
    if not following:
        return any(char not in VOWELS for char in after)
    between = word[index + 1:following[0]]
    if len(between) == 2 and between[0] == between[1] and between[0] in "bcçdgkpt":
        return False                     # çift patlamalı tek ünsüz gibi sayılır ("seyretti" sɛjretːɪ)
    return len(between) >= 2


def _vowel_phone(word, index, vowels, char):
    is_last = index == vowels[-1]
    final = is_last and index == len(word) - 1
    closed = _closed(word, index, vowels)
    lax = closed or final
    if char == "e":
        if closed:
            nxt = word[index + 1]
            return "æ" if nxt in "lmn" else "ɛ"
        return "ɛ" if final else "e"
    if char in "iî":
        return "ɪ" if lax else "i"
    if char == "o":
        return "ɔ" if lax else "o"
    if char in "uû":
        return "ʊ" if lax or word[index + 1:index + 2] == "ğ" else "u"
    if char == "ü":
        return "ø" if lax else "y"
    if char == "ö":
        return "œ"
    if char == "ı":
        return "ɯ"
    return "a"


def _neighbour_vowel(word, index):
    """l ve g için belirleyici ünlü: hemen sonraki ünlü, yoksa önceki."""
    for char in word[index + 1:]:
        if char in VOWELS:
            return char
        if char not in "lrğy":           # arada başka ünsüz varsa sonraki hecenin ünlüsü belirlemez
            break
    for char in reversed(word[:index]):
        if char in VOWELS:
            return char
    return "a"


CONSONANTS = {"b": "b", "c": "dʒ", "ç": "tʃ", "d": "d", "f": "f", "h": "h", "j": "ʒ", "m": "m", "n": "n", "p": "p",
              "s": "s", "ş": "ʃ", "t": "t", "v": "v", "y": "j", "z": "z", "k": "k"}


def word_phonemes(word, stress=True):
    """Tek bir sözcüğü (küçük harf, yalnız harf; kesme işaretli özel ad olabilir) ses birimlerine çevirir."""
    root = None
    if "'" in word:
        root, _, suffix = word.partition("'")
        word = root + suffix
    word = word.replace("q", "k").replace("w", "v").replace("x", "ks")
    word = "".join(char for char in word if char in VOWELS or char in CONSONANTS or char in "glrğ")
    if not word:
        return []
    vowels = _vowel_positions(word)
    if not vowels:                        # ünlüsüz: harf harf oku
        return word_phonemes_list(_spell(word).split(), stress)
    stressed = _stress_syllable(word, root) if stress else None
    stressed_index = vowels[stressed] if stressed is not None else None
    thin_final_l = (root or word) in THIN_L_WORDS

    out = []
    index = 0
    while index < len(word):
        char = word[index]
        prev = word[index - 1] if index else ""
        nxt = word[index + 1] if index + 1 < len(word) else ""
        if char in VOWELS:
            if index == stressed_index:
                out.append("ˈ")
            phone = _vowel_phone(word, index, vowels, char)
            if char == "â" and prev not in "kgl":
                phone = "aː"
            out.append(phone)
        elif char == "ğ":
            after = word[index + 1] if index + 1 < len(word) else ""
            if prev in "ei":
                out.append("j")
            elif prev == "ı":
                out.append("ɯ")
            elif prev in VOWELS:
                if out and out[-1][-1] != "ː":
                    out[-1] += "ː"
                if after in VOWELS and after == prev:      # "ağa" → aː, "uğu" → uː
                    if index + 1 == stressed_index and "ˈ" not in out:
                        out.insert(len(out) - 1, "ˈ")
                    index += 2
                    continue
        else:
            if char == nxt and char != "ğ":
                # çift ünsüz: patlamalılar uzatılır ("attı" atːɯ), sürekliler iki kez yazılır ("belli" bællɪ)
                phone = _consonant(word, index, char, prev, word[index + 2] if index + 2 < len(word) else "",
                                   thin_final_l)
                out.append(phone + "ː" if char in "bcçdgkpt" else phone + phone)
                index += 2
                continue
            out.append(_consonant(word, index, char, prev, nxt, thin_final_l))
        index += 1
    return [piece for phone in out for piece in _split(phone)]


def _split(phone):
    """"dʒ", "tʃ" gibi çok karakterli ses birimleri Piper'da tek tek karakter olarak geçer."""
    return list(phone)


def _consonant(word, index, char, prev, nxt, thin_final_l):
    if char == "l":
        if thin_final_l and index >= len(word) - 2:
            return "l"
        return "l" if _neighbour_vowel(word, index) in FRONT else "ɫ"
    if char == "r":
        after_vowel = prev in VOWELS or (prev == "ğ" and index >= 2 and word[index - 2] in VOWELS)
        return "ɾ" if after_vowel and nxt in VOWELS else "r"
    if char == "g":
        return "ɟ" if _neighbour_vowel(word, index) in FRONT else "ɡ"
    if char == "k":
        if nxt == "â" or (word.endswith("ken") and index == len(word) - 3 and prev in "ry"):
            return "c"
        return "k"
    return CONSONANTS[char]


def word_phonemes_list(words, stress=True):
    out = []
    for position, word in enumerate(words):
        if position:
            out.append(" ")
        out += word_phonemes(word, stress)
    return out


# =============================================================================
# Cümle → ses birimleri
# =============================================================================

PUNCTUATION = set(",.!?;:-()\"'")
_TOKEN = re.compile(r"[a-zçğıöşüâîûqwx]+(?:'[a-zçğıöşüâîû]+)?|[,.!?;:()\"-]")


def phonemize(text):
    """Metni (okunacak biçime getirerek) Piper'ın beklediği ses birimi listesine çevirir."""
    tokens = _TOKEN.findall(lower_tr(normalize(text)))
    out = []
    for token in tokens:
        if token in PUNCTUATION:
            if token == "-" and (not out or out[-1] == " "):
                token = ","
            while out and out[-1] == " ":
                out.pop()
            out.append(token)
            out.append(" ")
            continue
        out += word_phonemes(token)
        out.append(" ")
    while out and out[-1] == " ":
        out.pop()
    return out


def phoneme_ids(phonemes, id_map):
    """Piper kodlaması: ^ _ (ses birimi _)* $"""
    ids = list(id_map["^"]) + list(id_map["_"])
    for phoneme in phonemes:
        if phoneme in id_map:
            ids += list(id_map[phoneme]) + list(id_map["_"])
    ids += list(id_map["$"])
    return ids


# Cümle bölme: . ! ? … ve satır sonları; çok uzun cümleler virgülden bölünür
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-ZÇĞİÖŞÜÂÎÛ0-9])")
_NO_BREAK = {"dr", "prof", "doç", "yrd", "av", "sn", "vb", "vs", "bkz", "örn", "no", "mah", "cad", "sok", "apt",
             "tel", "ltd", "şti", "s", "yy"}
MAX_CHARS = 220


def sentences(text):
    """Metni sesli okuma parçalarına böler: (başlangıç, bitiş) karakter aralıkları."""
    spans = []
    for block in re.finditer(r"[^\n  ]+", text):
        start = block.start()
        last = start
        for match in _SENTENCE_END.finditer(block.group(0)):
            cut = block.start() + match.start()
            word = text[last:cut].rstrip().rsplit(None, 1)[-1] if text[last:cut].split() else ""
            if word.rstrip(".").lower() in _NO_BREAK or re.fullmatch(r"[A-ZÇĞİÖŞÜ]\.", word):
                continue
            spans.append((last, cut))
            last = block.start() + match.end()
        spans.append((last, block.end()))
    result = []
    for start, end in spans:
        while end - start > MAX_CHARS:
            chunk = text[start:start + MAX_CHARS]
            cut = max(chunk.rfind(mark) for mark in (", ", "; ", ": "))
            if cut <= 0:
                cut = chunk.rfind(" ")
            if cut <= 0:
                break
            result.append((start, start + cut + 1))
            start += cut + 1
            while start < end and text[start] == " ":
                start += 1
        if text[start:end].strip():
            result.append((start, end))
    return result
