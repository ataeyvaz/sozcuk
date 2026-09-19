"""Windows Yazım Denetimi API'si (ISpellCheckerFactory) üzerinden Türkçe yazım denetimi.

Windows 8 ve sonrasıyla gelen, her uygulamanın kullanması için sunulmuş resmî bir işletim sistemi
API'sidir; Word'ün sözlük dosyaları kopyalanmaz ya da Word çalıştırılmaz. Ölçüldü: Türkçe yazım hataları
ve öneriler Word'ünkiyle birebir aynı (aynı Microsoft Türkçe sözlüğü). Tamamen yerel ve çevrimdışıdır;
metin hiçbir yere gönderilmez.

COM nesneleri oluşturuldukları iş parçacığında (arayüz iş parçacığı) kullanılmalıdır.
Qt'ye bağımlı değildir.
"""

import sys
from ctypes import HRESULT, POINTER, c_int, c_wchar_p
from ctypes.wintypes import BOOL, LPWSTR, ULONG

LANGUAGE = "tr-TR"

# ISpellingError.CorrectiveAction
ACTION_NONE, ACTION_SUGGEST, ACTION_REPLACE, ACTION_DELETE = 0, 1, 2, 3


class SpellEngineUnavailable(Exception):
    def __init__(self, message, language_missing=False):
        super().__init__(message)
        self.language_missing = language_missing  # Windows var ama Türkçe bileşeni yüklü değil


def _interfaces():
    from comtypes import COMMETHOD, GUID, IUnknown

    class IEnumString(IUnknown):
        _iid_ = GUID("{00000101-0000-0000-C000-000000000046}")
        _methods_ = [
            COMMETHOD([], HRESULT, "Next", (["in"], ULONG, "celt"), (["out"], POINTER(LPWSTR), "rgelt"),
                      (["out"], POINTER(ULONG), "fetched")),
            COMMETHOD([], HRESULT, "Skip", (["in"], ULONG, "celt")),
            COMMETHOD([], HRESULT, "Reset"),
            COMMETHOD([], HRESULT, "Clone", (["out"], POINTER(POINTER(IUnknown)), "ppenum")),
        ]

    class ISpellingError(IUnknown):
        _iid_ = GUID("{B7C82D61-FBE8-4B47-9B27-6C0D2E0DE0A3}")
        _methods_ = [
            COMMETHOD(["propget"], HRESULT, "StartIndex", (["out", "retval"], POINTER(ULONG), "value")),
            COMMETHOD(["propget"], HRESULT, "Length", (["out", "retval"], POINTER(ULONG), "value")),
            COMMETHOD(["propget"], HRESULT, "CorrectiveAction", (["out", "retval"], POINTER(c_int), "value")),
            COMMETHOD(["propget"], HRESULT, "Replacement", (["out", "retval"], POINTER(LPWSTR), "value")),
        ]

    class IEnumSpellingError(IUnknown):
        _iid_ = GUID("{803E3BD4-2828-4410-8290-418D1D73C762}")
        _methods_ = [COMMETHOD([], HRESULT, "Next", (["out"], POINTER(POINTER(ISpellingError)), "value"))]

    class ISpellChecker(IUnknown):
        _iid_ = GUID("{B6FD0B71-E2BC-4653-8D05-F197E412770B}")
        _methods_ = [
            COMMETHOD(["propget"], HRESULT, "LanguageTag", (["out", "retval"], POINTER(LPWSTR), "value")),
            COMMETHOD([], HRESULT, "Check", (["in"], c_wchar_p, "text"),
                      (["out", "retval"], POINTER(POINTER(IEnumSpellingError)), "value")),
            COMMETHOD([], HRESULT, "Suggest", (["in"], c_wchar_p, "word"),
                      (["out", "retval"], POINTER(POINTER(IEnumString)), "value")),
        ]

    class ISpellCheckerFactory(IUnknown):
        _iid_ = GUID("{8E018A9D-2415-4677-BF08-794EA61F94BB}")
        _methods_ = [
            COMMETHOD(["propget"], HRESULT, "SupportedLanguages",
                      (["out", "retval"], POINTER(POINTER(IEnumString)), "value")),
            COMMETHOD([], HRESULT, "IsSupported", (["in"], c_wchar_p, "languageTag"),
                      (["out", "retval"], POINTER(BOOL), "value")),
            COMMETHOD([], HRESULT, "CreateSpellChecker", (["in"], c_wchar_p, "languageTag"),
                      (["out", "retval"], POINTER(POINTER(ISpellChecker)), "value")),
        ]

    return ISpellCheckerFactory


FACTORY_CLSID = "{7AB36653-1796-484B-BDFA-E74F1DB7C1DC}"


class SpellEngine:
    def __init__(self, language=LANGUAGE):
        if sys.platform != "win32":
            raise SpellEngineUnavailable("Yazım denetimi yalnızca Windows'ta kullanılabilir.")
        try:
            import comtypes
            from comtypes import GUID
            factory_interface = _interfaces()
            factory = comtypes.CoCreateInstance(GUID(FACTORY_CLSID), interface=factory_interface)
        except Exception as exc:
            raise SpellEngineUnavailable("Windows yazım denetimi hizmetine ulaşılamadı.") from exc
        if not factory.IsSupported(language):
            raise SpellEngineUnavailable(
                "Bu Windows'ta Türkçe yazım denetimi bileşeni yüklü değil. Durum çubuğundaki menüden "
                "Windows'a eklenebilir.", language_missing=True)
        self.checker = factory.CreateSpellChecker(language)
        self.language = language

    def errors(self, text):
        """[(başlangıç, uzunluk, düzeltme türü, yerine konacak metin), …] — metin içindeki karakter konumları."""
        if not text.strip():
            return []
        result = []
        enum = self.checker.Check(text)
        while True:
            try:
                error = enum.Next()
            except Exception:  # S_FALSE: liste bitti
                break
            if not error:
                break
            action = error.CorrectiveAction
            replacement = error.Replacement if action == ACTION_REPLACE else ""
            result.append((error.StartIndex, error.Length, action, replacement))
        return result

    def suggest(self, word, limit=6):
        enum = self.checker.Suggest(word)
        suggestions = []
        while len(suggestions) < limit:
            try:
                value, fetched = enum.Next(1)
            except Exception:
                break
            if not fetched:
                break
            suggestions.append(value)
        return suggestions
