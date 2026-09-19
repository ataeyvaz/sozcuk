"""Çeviri dil paketlerini uygulamanın içine indirir (gömülü diller).

Kullanım (proje klasöründe):
    .venv\\Scripts\\python.exe araclar\\dil_paketleri_indir.py en de fr
    .venv\\Scripts\\python.exe araclar\\dil_paketleri_indir.py --hepsi

İndirilen .argosmodel dosyaları sozcuk/diller klasörüne konur; Sözcük ilk açılışta bunları kendiliğinden
kurar, böylece kullanıcı hiçbir şey indirmez. Her dil için Türkçe ⇄ o dil çevirisi İngilizce üzerinden
yapıldığından tr↔en paketleri her zaman alınır.
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sozcuk import translate  # noqa: E402

TARGET = Path(__file__).resolve().parent.parent / "sozcuk" / translate.BUNDLE_DIR_NAME


def pairs_for(languages):
    pairs = [("tr", "en"), ("en", "tr")]
    for code in languages:
        if code in ("tr", "en"):
            continue
        pairs += [("en", code), (code, "en")]
    return pairs


def main(argv):
    languages = [a for a in argv if not a.startswith("--")]
    if "--hepsi" in argv or not languages:
        languages = translate.UI_LANGUAGES
    pairs = pairs_for(languages)
    index = translate.index_pairs(refresh=True)
    TARGET.mkdir(parents=True, exist_ok=True)
    total = sum(translate.PACKAGE_SIZES.get(pair, 120) for pair in pairs)
    print(f"{len(pairs)} paket, yaklaşık {total} MB -> {TARGET}")
    for source, target in pairs:
        entry = index.get((source, target))
        if entry is None:
            print(f"  {source}->{target}: dizinde yok, atlandı")
            continue
        name = f"translate-{source}_{target}.argosmodel"
        destination = TARGET / name
        if destination.exists():
            print(f"  {source}->{target}: zaten var")
            continue
        print(f"  {source}->{target}: indiriliyor…", flush=True)
        path = entry.download()
        shutil.copy(path, destination)
        print(f"    {destination.name} ({destination.stat().st_size / 1e6:.0f} MB)")
    print("bitti")


if __name__ == "__main__":
    main(sys.argv[1:])
