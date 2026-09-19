"""Windows'a Türkçe yazım denetimi bileşeni ekleme.

Türkçe yazım denetimi Windows'un "Türkçe temel yazma" isteğe bağlı özelliğiyle (Language.Basic~~~tr-TR)
gelir. Türkçe olmayan Windows kurulumlarında bu bileşen yoksa Sözcük'ün yazım denetimi çalışmaz.

Risk değerlendirmesi (kullanıcıya da gösterilir):
- Eklenen yalnızca Microsoft'un resmî yazım denetimi/sözlük bileşenidir; ekran dilini ve klavye
  düzenini DEĞİŞTİRMEZ. Ayarlar → Uygulamalar → İsteğe bağlı özellikler'den kaldırılabilir.
- Sistem genelinde bir değişiklik olduğu için yönetici izni gerekir: Windows'un kendi UAC onay penceresi
  çıkar; kullanıcı onaylamazsa hiçbir şey yapılmaz. Sözcük yönetici olarak çalışmaz, yalnızca bu tek
  komut yükseltilmiş çalışır.
- Bileşen Windows Update üzerinden indirilir; internet gerekir. Kurumsal politikalar engelleyebilir.

Bu modül Qt'ye bağımlı değildir; kurulum beklemesi arka plan iş parçacığında yapılmalıdır.
"""

import ctypes
import os
import sys
from ctypes import wintypes

CAPABILITY = "Language.Basic~~~tr-TR~0.0.1.0"
SETTINGS_URI = "ms-settings:regionlanguage"

ERROR_CANCELLED = 1223  # kullanıcı UAC penceresinde "Hayır" dedi
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_HIDE = 0
INFINITE = 0xFFFFFFFF

# PowerShell'e verilen komut sabittir; kullanıcı girdisi içermez
INSTALL_SCRIPT = (
    "try { Add-WindowsCapability -Online -Name '" + CAPABILITY + "' -ErrorAction Stop | Out-Null; exit 0 } "
    "catch { exit 1 }"
)


class InstallResult:
    OK = "ok"
    CANCELLED = "cancelled"   # UAC reddedildi
    FAILED = "failed"         # komut çalıştı ama bileşen eklenemedi (internet, politika…)
    UNSUPPORTED = "unsupported"


class _ShellExecuteInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def run_powershell(script, elevated=True):
    """PowerShell komutunu gizli pencerede çalıştırır ve bitmesini bekler.
    (sonuç, çıkış kodu) döndürür; elevated=True ise Windows UAC onayı ister."""
    if sys.platform != "win32":
        return InstallResult.UNSUPPORTED, None
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    powershell = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                              r"System32\WindowsPowerShell\v1.0\powershell.exe")
    info = _ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas" if elevated else "open"
    info.lpFile = powershell
    info.lpParameters = f'-NoProfile -NonInteractive -WindowStyle Hidden -Command "{script}"'
    info.nShow = SW_HIDE
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        error = ctypes.get_last_error()
        return (InstallResult.CANCELLED if error == ERROR_CANCELLED else InstallResult.FAILED), error
    try:
        kernel32.WaitForSingleObject(info.hProcess, INFINITE)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    finally:
        kernel32.CloseHandle(info.hProcess)
    return (InstallResult.OK if code.value == 0 else InstallResult.FAILED), code.value


def install_turkish_spelling():
    return run_powershell(INSTALL_SCRIPT, elevated=True)


def open_language_settings():
    if sys.platform == "win32":
        os.startfile(SETTINGS_URI)
