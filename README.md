# Sözcük

Word'ün kalabalık arayüzü yerine, gerçekten kullanılan özellikleri sade bir yüzle sunan **Türkçe masaüstü kelime işlemci**. Windows için; Python 3.11 ve PySide6 ile yazıldı.

**Developed By Usta ve Ata**

Yazım denetimi, sesle yazma ve çeviri dahil her şey **bilgisayarda** çalışır: belgeleriniz hiçbir sunucuya gönderilmez.

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
- **Çeviri:** yerel çeviri modelleri; Türkçe ⇄ İngilizce, Almanca, İtalyanca, İspanyolca uygulamayla gelir, diğer diller istenirse indirilir
- **Google Drive / OneDrive:** eşitleme klasöründeki belgelerde canlı kayıt, dışarıdan değişikliği fark etme
- **Yardım:** uygulama içi, aranabilir "Yardım ve Nasıl Kullanılır" (F1)

## Çalıştırma (kaynaktan)

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\pythonw.exe main.py
```

Çeviri dil paketleri depoda yer almaz (dosya başına 87–285 MB). İndirmek için:

```bat
.venv\Scripts\python.exe araclar\dil_paketleri_indir.py de it es
```

`--hepsi` bütün dilleri indirir (≈2,2 GB). Paketler `sozcuk/diller/` klasörüne konur ve uygulama ilk açılışta bunları kendiliğinden kurar.

## Paketleme

```bat
.venv\Scripts\python.exe araclar\ikon_uret.py
.venv\Scripts\python.exe -m PyInstaller sozcuk.spec --noconfirm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\sozcuk.iss
```

Sonuç: `dist\Sozcuk\` (taşınabilir klasör) ve `dist\Sozcuk-1.0-kurulum.exe` (kurulum paketi).

## Klasörler

| Yol | İçerik |
|---|---|
| `sozcuk/` | uygulama kaynağı (editör, biçimler, çeviri, yardım…) |
| `sozcuk/yardim.md` | uygulama içi yardım metni |
| `araclar/` | yardımcı betikler (dil paketi indirme, ikon üretme) |
| `kurulum/` | Inno Setup kurulum betiği |
| `plan.md`, `surec.md` | proje planı ve değişiklik günlüğü |

## Kullanılan açık kaynak bileşenler

PySide6 (Qt, LGPL) · python-docx (MIT) · pdfminer.six (MIT) · olefile (BSD) · comtypes (MIT) ·
faster-whisper + Whisper modeli (MIT) · Argos Translate (MIT) + OPUS-MT modelleri (CC-BY 4.0)

Sözcük'ün kendi lisansı henüz belirlenmedi.
