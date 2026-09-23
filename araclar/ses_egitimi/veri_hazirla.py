"""Sesli okuma modelinin eğitim verisini hazırlar (Kaggle'a yüklenecek klasör).

Kaynak: BabaKartalVoice projesindeki kayıtlar (dataset/wav + dataset/metadata.csv — "utt|metin").
Çıktı: <hedef>/  wav/*.wav, metadata.csv ("utt|ses birimleri"), metin.csv ("utt|metin"), pronunciation.py

Neden ses birimleri: Piper eğitimi metni espeak-ng ile çevirir; biz `--data.phoneme_type text` ile kendi
Türkçe dönüştürücümüzün (sozcuk/pronunciation.py) çıktısını veriyoruz. Böylece eğitimdeki ve Sözcük'teki
telaffuz birebir aynı olur (eski Piper denemesini bozan fonem uyuşmazlığı imkânsız).

Kullanım (proje klasöründe):
    .venv\\Scripts\\python.exe araclar\\ses_egitimi\\veri_hazirla.py
    .venv\\Scripts\\python.exe araclar\\ses_egitimi\\veri_hazirla.py --kaynak "C:\\...\\BabaKartalVoice" --hedef ...

Sonra Kaggle'a (ilk kez "create", sonrakilerde "version"):
    kaggle datasets create  -p <hedef> -r zip
    kaggle datasets version -p <hedef> -r zip -m "28 yeni kayıt"
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sozcuk.pronunciation import phonemize  # noqa: E402

KAYNAK = Path(r"C:\Users\Ata\Desktop\BabaKartalVoice")
HEDEF = Path(r"C:\Users\Ata\Desktop\BabaKartalVoice\kaggle-veri")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Kaggle eğitim veri klasörünü hazırlar.")
    parser.add_argument("--kaynak", type=Path, default=KAYNAK, help="BabaKartalVoice proje klasörü")
    parser.add_argument("--hedef", type=Path, default=HEDEF, help="oluşturulacak veri klasörü")
    args = parser.parse_args(argv)

    csv_path = args.kaynak / "dataset" / "metadata.csv"
    wav_dir = args.kaynak / "dataset" / "wav"
    if not csv_path.exists() or not wav_dir.is_dir():
        raise SystemExit(f"Kayıt bulunamadı: {csv_path} / {wav_dir}\n"
                         "Önce BabaKartalVoice'ta scripts\\prepare_dataset.py çalıştırın.")

    (args.hedef / "wav").mkdir(parents=True, exist_ok=True)
    rows = [line.rstrip("\n").split("|", 1) for line in csv_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    kopyalanan = 0
    with open(args.hedef / "metadata.csv", "w", encoding="utf-8", newline="\n") as phonemes_file, \
            open(args.hedef / "metin.csv", "w", encoding="utf-8", newline="\n") as text_file:
        for utt, text in rows:
            source = wav_dir / f"{utt}.wav"
            if not source.exists():
                print(f"  ses dosyası yok, atlandı: {utt}")
                continue
            target = args.hedef / "wav" / source.name
            if not target.exists() or target.stat().st_size != source.stat().st_size:
                shutil.copy2(source, target)
            kopyalanan += 1
            phonemes_file.write(f"{utt}|{''.join(phonemize(text))}\n")
            text_file.write(f"{utt}|{text}\n")

    shutil.copy2(Path(__file__).resolve().parent.parent.parent / "sozcuk" / "pronunciation.py",
                 args.hedef / "pronunciation.py")
    shutil.copy2(Path(__file__).resolve().parent / "dataset-metadata.json", args.hedef / "dataset-metadata.json")
    print(f"{kopyalanan} kayıt hazır -> {args.hedef}")


if __name__ == "__main__":
    main()
