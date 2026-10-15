"""Şerit sekmeleri (Tabcel `serit_sekmeleri.py` düzeniyle): Giriş, Ekle, Sayfa Düzeni, Gözden Geçir, Görünüm, Yardım.

Yalnız yerleşimdir: düğmeler `MainWindow.eylemler` kataloğundaki eylemleri ve pencerenin kurduğu hazır
bileşenleri (yazı tipi kutusu, renk düğmeleri, tablo/resim/simge menüleri, mikrofon…) kullanır; komut mantığı
pencerede kalır. Hazır bileşenler yalnız bir kez eklenir (bir widget iki yerde bulunamaz)."""

from .serit import SeritGrubu, SeritSayfasi, ikon_dugmesi


class GirisSayfasi(SeritSayfasi):
    """Giriş: Pano, Yazı Tipi, Paragraf, Stiller, Düzenleme, Ses."""

    def __init__(self, w):
        super().__init__()
        e = w.eylemler
        pano = SeritGrubu("Pano", 5, "paste32")
        pano.buyuk(e["paste"], menu=w.paste_menu, ikon="paste32", metin="Yapıştır", ana_islem=True)
        pano.kucukler([e["cut"], e["copy"]])
        self.grup_ekle(pano)

        yazi = SeritGrubu("Yazı Tipi", 9, "font32")
        yazi.satirlar([
            [w.font_box, w.size_box, ikon_dugmesi(e["grow_font"]), ikon_dugmesi(e["shrink_font"])],
            [ikon_dugmesi(e["bold"]), ikon_dugmesi(e["italic"]), ikon_dugmesi(e["underline"]),
             ikon_dugmesi(e["strike"]), w.highlight_button, w.color_button, ikon_dugmesi(e["clear_format"]),
             ikon_dugmesi(e["add_font"])],
        ])
        self.grup_ekle(yazi)

        paragraf = SeritGrubu("Paragraf", 8, "paragraph32")
        paragraf.satirlar([
            [ikon_dugmesi(e["bullets"]), ikon_dugmesi(e["numbers"]), ikon_dugmesi(e["outdent"]),
             ikon_dugmesi(e["indent"]), w.spacing_button],
            [ikon_dugmesi(e[k]) for k in ("align_left", "align_center", "align_right", "align_justify")],
        ])
        self.grup_ekle(paragraf)

        stiller = SeritGrubu("Stiller", 3, "styles32")
        stiller.satirlar([[w.heading_box]])
        self.grup_ekle(stiller)

        duzenleme = SeritGrubu("Düzenleme", 4, "find32")
        duzenleme.kucukler([e["find"], e["replace"]])
        self.grup_ekle(duzenleme)

        ses = SeritGrubu("Ses", 6, "mic32")
        ses.kucukler([w.mic_button])
        self.grup_ekle(ses)


class EkleSayfasi(SeritSayfasi):
    """Ekle: Tablo, Resim, Simge, Bağlantı, Sayfa Numarası."""

    def __init__(self, w):
        super().__init__()
        e = w.eylemler
        tablo = SeritGrubu("Tablolar", 6, "table32")
        tablo.buyuk(menu=w.table_menu, ikon="table32", metin="Tablo")
        self.grup_ekle(tablo)
        resim = SeritGrubu("Resimler", 5, "picture32")
        resim.buyuk(menu=w.image_menu, ikon="picture32", metin="Resim")
        self.grup_ekle(resim)
        baglanti = SeritGrubu("Bağlantılar", 4, "link32")
        baglanti.buyuk(e["link"], ikon="link32", metin="Bağlantı")
        self.grup_ekle(baglanti)
        sayfa = SeritGrubu("Sayfa", 3, "pagenum32")
        sayfa.buyuk(menu=w.page_menu.number_menu, ikon="pagenum32", metin="Sayfa\nNumarası")
        self.grup_ekle(sayfa)
        simge = SeritGrubu("Simgeler", 2, "symbol32")
        simge.buyuk(menu=w.symbol_menu, ikon="symbol32", metin="Simge")
        self.grup_ekle(simge)


class SayfaDuzeniSayfasi(SeritSayfasi):
    """Sayfa Düzeni: kenar boşlukları, yönlendirme, kâğıt boyutu (+ Sayfa Yapısı penceresi)."""

    def __init__(self, w):
        super().__init__()
        grup = SeritGrubu("Sayfa Yapısı", 5, "margins32")
        grup.buyuk(menu=w.page_menu.margins_menu, ikon="margins32", metin="Kenar\nBoşlukları")
        grup.buyuk(menu=w.page_menu.orientation_menu, ikon="orientation32", metin="Yönlendirme")
        grup.buyuk(menu=w.page_menu.size_menu, ikon="paper32", metin="Boyut")
        grup.baslatici_ekle(w.page_menu.open_dialog, "Sayfa Yapısı")
        self.grup_ekle(grup)


class GozdenGecirSayfasi(SeritSayfasi):
    """Gözden Geçir: yazım denetimi, çeviri, sesli okuma."""

    def __init__(self, w):
        super().__init__()
        e = w.eylemler
        yazim = SeritGrubu("Yazım Denetimi", 6, "spell32")
        yazim.buyuk(e["spell_next"], ikon="spell32", metin="Sonraki\nHata")
        yazim.kucukler([e["spell_live"], e["dictation_vocabulary"]])
        self.grup_ekle(yazim)
        dil = SeritGrubu("Dil", 5, "translate32")
        dil.buyuk(e["translate"], ikon="translate32", metin="Çeviri")
        dil.kucukler([e["language_packs"]])
        self.grup_ekle(dil)
        okuma = SeritGrubu("Sesli Okuma", 4, "read32")
        okuma.kucukler([w.read_button])
        self.grup_ekle(okuma)


class GorunumSayfasi(SeritSayfasi):
    """Görünüm: cetvel ve yakınlaştırma."""

    def __init__(self, w):
        super().__init__()
        e = w.eylemler
        goster = SeritGrubu("Göster", 3, "ruler32")
        goster.kucukler([e["ruler"]])
        self.grup_ekle(goster)
        yakin = SeritGrubu("Yakınlaştır", 5, "zoom_in32")
        yakin.buyuk(e["zoom_in"], ikon="zoom_in32", metin="Yakınlaştır")
        yakin.buyuk(e["zoom_out"], ikon="zoom_out32", metin="Uzaklaştır")
        yakin.buyuk(e["zoom_100"], ikon="zoom100_32", metin="%100")
        yakin.buyuk(e["fit_width"], ikon="page_width32", metin="Sayfa\nGenişliği")
        yakin.buyuk(e["fit_page"], ikon="full_page32", metin="Tam\nSayfa")
        self.grup_ekle(yakin)


class YardimSayfasi(SeritSayfasi):
    """Yardım: kullanım yardımı, kısayollar, Hakkında, tanılama günlüğü."""

    def __init__(self, w):
        super().__init__()
        e = w.eylemler
        yardim = SeritGrubu("Yardım", 5, "help32")
        yardim.buyuk(e["help"], ikon="help32", metin="Yardım")
        yardim.buyuk(e["shortcuts"], ikon="keyboard32", metin="Klavye\nKısayolları")
        yardim.buyuk(e["about"], ikon="info32", metin="Sözcük\nHakkında")
        self.grup_ekle(yardim)
        arac = SeritGrubu("Tanılama", 3, "info32")
        arac.kucukler([e["open_log"]])
        self.grup_ekle(arac)
