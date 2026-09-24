# Sözcük

Word'ün kalabalık arayüzü yerine, gerçekten kullanılan özellikleri sade bir yüzle sunan **Türkçe masaüstü kelime işlemci**. Windows için; Python 3.11 ve PySide6 ile yazıldı.

**Developed By Usta ve Ata**

Yazım denetimi, sesle yazma, sesli okuma ve çeviri dahil her şey **bilgisayarda** çalışır: belgeleriniz hiçbir sunucuya gönderilmez.

## Neler var

- **Belge:** başlık stilleri, yazı tipi/boyut/renk, hizalama, satır aralığı, listeler, girintiler, tablolar
- **Sayfa:** gerçek A4 görünümü, cetveller, kâğıt boyutu (A4, A5, A3, B5, Letter, Legal, Executive), dikey/yatay, kenar boşlukları, **sayfa numarası** (Word'ün PAGE alanı olarak kaydedilir)
- **Resimler:** dosyadan/panodan/sürükle-bırak, tutamaklarla boyutlandırma, kırpma, 90° ve fareyle döndürme
- **Simgeler:** kategorili, Türkçe aranabilir simge penceresi (₺, oklar, matematik, ASCII, emoji…)
- **Bul ve Değiştir:** Türkçe harf kurallarıyla (İ/ı), tam sözcük, tümünü değiştir
- **Bağlantılar:** web/e-posta ve belge içi hedef ("2. sayfanın 5. satırı"); Word köprüsü olarak kaydedilir
- **Dosya biçimleri:** .docx, .docm, .dotx/.dotm, .doc/.dot, .rtf, .odt, .txt, .htm/.html/.mht, Word 2003 XML, .wps, .wpd, PDF açma; .docx/.doc/.rtf/.odt/.txt/.html olarak kaydetme; PDF dışa aktarma
- **Yazım denetimi:** Windows'un Türkçe yazım denetimi (Word ile aynı sonuçlar, çevrimdışı)
- **Sesle yazma:** faster-whisper ile yerel dikte, susunca otomatik durma, öğrenen kişisel sözlük
- **Sesli okuma:** Türkçe metni doğal sesle okur (Piper/VITS sesi, ONNX Runtime; sayı, tarih, saat, kısaltma okuma); uygulamayla Ata'nın sesi gelir
- **Çeviri:** yerel çeviri modelleri (CTranslate2); Türkçe ⇄ İngilizce uygulamayla gelir, diğer 11 dil kurulumda seçilir ya da sonradan indirilir
- **Google Drive / OneDrive:** eşitleme klasöründeki belgelerde canlı kayıt, dışarıdan değişikliği fark etme
- **Yardım:** uygulama içi, aranabilir "Yardım ve Nasıl Kullanılır" (F1)

## Çalıştırma (kaynaktan)

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe main.py
```

Uygulamayla gelen Türkçe ⇄ İngilizce dil paketleri depoda yer almaz (≈260 MB). İndirmek için:

```bat
.venv\Scripts\python.exe araclar\dil_paketleri_indir.py
```

Paketler açılmış klasörler olarak `sozcuk/diller/` içine konur; uygulama onları oradan doğrudan okur. Diğer diller pakete konmaz: kurulumda **Özel kurulum** ile seçilir (Inno Setup indirir) ya da uygulama içinden indirilir (`%LOCALAPPDATA%\Sözcük\diller`).

## Paketleme

```bat
.venv\Scripts\python.exe araclar\ikon_uret.py
.venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\sozcuk.iss
```

Sonuç: `dist\Sozcuk\` (taşınabilir klasör, ≈560 MB) ve `dist\Sozcuk-1.2-kurulum.exe` (kurulum paketi, ≈370 MB). Kurulum için Inno Setup 6.5 ya da üstü gerekir (dil paketlerini indirip açar).

## Klasörler

| Yol | İçerik |
|---|---|
| `sozcuk/` | uygulama kaynağı (editör, biçimler, çeviri, yardım…) |
| `sozcuk/yardim.md` | uygulama içi yardım metni |
| `sozcuk/sesler/` | sesli okuma sesleri (`.onnx` + `.onnx.json`; pakete konur) |
| `araclar/` | yardımcı betikler (gömülü dil paketlerini indirme, ikon üretme) |
| `araclar/ses_egitimi/` | sesli okuma sesinin eğitimi (Kaggle); bkz. içindeki `BENIOKU.md` |
| `kurulum/` | Inno Setup kurulum betiği |
| `plan.md`, `surec.md` | proje planı ve değişiklik günlüğü |

## Kullanılan açık kaynak bileşenler

PySide6 (Qt, LGPL) · python-docx (MIT) · pdfminer.six (MIT) · olefile (BSD) · comtypes (MIT) ·
faster-whisper + Whisper modeli (MIT) · CTranslate2 (MIT) + SentencePiece (Apache 2.0) · Argos Translate dil paketleri (MIT) + OPUS-MT modelleri (CC-BY 4.0) ·
ONNX Runtime (MIT) · Piper tr_TR dfki temel modeli (CC BY-NC-SA 4.0)

Sesli okuma sesi (`sozcuk/sesler/ata.onnx`) Ata'nın kendi kayıtlarıyla, dfki temel modelinden eğitildi; bu yüzden **ticari kullanıma kapalıdır** (CC BY-NC-SA 4.0).

Sözcük'ün kendi lisansı henüz belirlenmedi.
