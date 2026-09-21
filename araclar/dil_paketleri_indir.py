"""Uygulamayla birlikte gelen (gömülü) çeviri dil paketlerini indirir.

Kullanım (proje klasöründe):
    .venv\\Scripts\\python.exe araclar\\dil_paketleri_indir.py

Pakete yalnızca Türkçe ⇄ İngilizce konur (≈260 MB). Paketler açılmış olarak sozcuk/diller/ klasörüne konur;
Sözcük onları oradan doğrudan okur. Diğer diller kurulumda seçilir (Inno Setup indirir) ya da uygulama içinden
(Gözden Geçir → Dil Paketleri…) indirilir; başka bir dili denemek için kodu (ör. "de") argüman olarak verin:
    .venv\\Scripts\\python.exe araclar\\dil_paketleri_indir.py de
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sozcuk import translate  # noqa: E402

TARGET = Path(__file__).resolve().parent.parent / "sozcuk" / translate.BUNDLE_DIR_NAME


def pairs_for(languages):
    pairs = [("tr", "en"), ("en", "tr")]
    for code in languages:
        if code not in ("tr", "en"):
            pairs += [("en", code), (code, "en")]
    return pairs


def main(argv):
    pairs = pairs_for(argv)
    installed = set()
    for folder in TARGET.glob("translate-*"):
        package = translate._read_package(folder)
        if package is not None:
            installed.add(package.pair)
    total = sum(translate.PACKAGE_SIZES.get(pair, 120) for pair in pairs if pair not in installed)
    print(f"{len(pairs)} paket, indirilecek ≈{total} MB -> {TARGET}")
    for pair in pairs:
        if pair in installed:
            print(f"  {pair[0]}->{pair[1]}: zaten var")
            continue
        print(f"  {pair[0]}->{pair[1]}: indiriliyor…", flush=True)
        folder = translate.download_package(pair, TARGET)
        print(f"    {folder.name}")
    print("bitti")


if __name__ == "__main__":
    main(sys.argv[1:])
