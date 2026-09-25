# Sesli okuma sesini eğitmek (Kaggle)

Sözcük'ün sesli okuma sesi burada eğitilir. Eğitim GPU ister; bu bilgisayarda GPU yok, bu yüzden **Kaggle**
kullanılıyor (ücretsiz, haftada 30 saat, tarayıcı kapalıyken de çalışır — ücretsiz Colab eğitimi öldürüyordu).
Kaggle yalnızca "fırın"dır: çıkan model bilgisayarda, internetsiz çalışır.

## Dosyalar

| Dosya | Ne yapar |
|---|---|
| `veri_hazirla.py` | BabaKartalVoice kayıtlarından Kaggle veri klasörünü üretir (ses birimleri dahil) |
| `egitim.py` | Kaggle'da çalışan eğitim betiği (kurulum → eğitim → ONNX → dinleme örnekleri) |
| `kernel-metadata.json` | Kaggle kernel tanımı (GPU, internet, girdi veri seti ve önceki eğitim) |
| `dataset-metadata.json` | Kaggle veri seti tanımı (özel) |

## Sıra

```bat
rem 0) Kaggle girişi (bir kez; tarayıcıda onay ister, anahtar dosyası gerekmez)
kaggle auth login

rem 1) Yeni kayıtlar varsa önce BabaKartalVoice'ta veri setini tazele
cd C:\Users\Ata\Desktop\BabaKartalVoice
.venv\Scripts\python.exe scripts\prepare_dataset.py

rem 2) Kaggle veri klasörünü üret (ses birimleri Sözcük'ün telaffuzuyla)
cd C:\Users\Ata\Desktop\sozcuk
.venv\Scripts\python.exe araclar\ses_egitimi\veri_hazirla.py

rem 3) Kaggle'a yükle (ilk kez create, sonra version)
kaggle datasets version -p C:\Users\Ata\Desktop\BabaKartalVoice\kaggle-veri -r zip -m "yeni kayitlar"

rem 4) Eğitimi gönder: egitim.py + kernel-metadata.json'u bir klasöre koy ve
kaggle kernels push -p <klasor>
kaggle kernels status ataeyvaz/<kernel-adi>
kaggle kernels output ataeyvaz/<kernel-adi> -p <indirme-klasoru>
```

Çıktı: `ata.onnx`, `ata.onnx.json`, `ornekler/*.wav`, `checkpoints/last.ckpt`.

## Devam eğitimi

`kernel-metadata.json` içindeki `id` yeni bir ad olmalı (ör. `…-3`) ve `kernel_sources` bir önceki kernel'i
göstermeli. `egitim.py` girdide `checkpoints/last.ckpt` bulursa temel modelden değil **oradan devam eder**
(zaman sayacını temizleyerek; yoksa `max_time`ın bir kısmı harcanmış sayılır).

`TRAIN_HOURS` eğitim süresidir. Kaggle oturumu en fazla 12 saattir, kurulum ve dışa aktarma payı bırakın.
Ayar değiştirdiğinizde önce `TRAIN_HOURS = 0.05` ile kısa bir deneme koşusu yapın: kurulum hataları 3 saatlik
kotayı yakmadan görünür.

## Sesi Sözcük'e koymak

- Denemek için: `ata.onnx` + `ata.onnx.json` → `%LOCALAPPDATA%\Sözcük\sesler\`
- Pakete koymak için: `sozcuk\sesler\` (PyInstaller bu klasörü alır; `sozcuk.spec` güncellenmeli, +63 MB)
- `ata.onnx.json` içine Sözcük'ün okuduğu iki alan yazılır:
  `"sozcuk": {"name": "Ata", "gender": "erkek"}` ve `"inference": {"length_scale": 1.1, "noise_scale": 0.5,
  "noise_w": 0.6}` (kullanıcı tercihi, 2026-09-25: %10 yavaş, sakin; `noise_w` bu modelde süreyi etkilemiyor)

## Lisans notu

Temel model `tr_TR dfki medium` (CC BY-NC-SA). Ondan türetilen ses **ticari kullanıma kapalıdır**. Ticari bir
sürüm gerekirse CC0 veriyle eğitilmiş bir temelden (fettah/fahrettin) ya da sıfırdan eğitmek gerekir.
