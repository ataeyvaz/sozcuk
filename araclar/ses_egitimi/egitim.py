# Sözcük — Ata'nın sesiyle Piper ses modeli eğitimi (Kaggle GPU)
#
# Veri: /kaggle/input/<veri seti>/  wav/*.wav (22050 Hz mono) + metadata.csv (utt|ses birimleri)
#       Ses birimleri Sözcük'ün kendi Türkçe dönüştürücüsüyle (pronunciation.py) üretildi: eğitimde ve uygulamada
#       aynı dönüştürücü → uyuşmazlık olmaz. Bu yüzden espeak yerine --data.phoneme_type text.
# Temel: Piper tr_TR dfki medium checkpoint'inden ince ayar (Türkçe bilen model, yalnızca ses öğretilir).
# Çıktı (/kaggle/working): ata.onnx + ata.onnx.json, ornekler/*.wav, checkpoints/last.ckpt (devam için)
#
# Bilinen tuzaklar (BabaKartalVoice Colab denemelerinde bulundu): torch.load kati kipi, val_mos geri çağrımı,
# yeni ONNX dışa aktarıcısı, eski checkpoint'in geçersiz ayarları. Hepsi aşağıda kapatılıyor.

import glob
import inspect
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePath

STARTED = time.time()
TRAIN_HOURS = 3.0                   # eğitim süresi (oturum sınırı 12 sa; kurulum ve dışa aktarma payı kalsın)
BATCH_SIZE = 16
VOICE = "ata"
BASE_URL = ("https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/"
            "tr/tr_TR/dfki/medium/epoch%3D5679-step%3D1489110.ckpt")

IN = Path(glob.glob("/kaggle/input/**/metadata.csv", recursive=True)[0]).parent
AUDIO = Path(glob.glob("/kaggle/input/**/utt_*.wav", recursive=True)[0]).parent   # zip açılınca iç içe olabilir
WORK = Path("/kaggle/working")
TMP = Path("/tmp/egitim")
PIPER = Path("/tmp/piper")
CKPT_DIR = WORK / "checkpoints"
for folder in (TMP, CKPT_DIR, WORK / "ornekler"):
    folder.mkdir(parents=True, exist_ok=True)


def sh(command, cwd=None):
    print(f"\n$ {command}", flush=True)
    subprocess.run(command, shell=True, check=True, cwd=cwd)


def elapsed():
    return f"{(time.time() - STARTED) / 60:.0f} dk"


# --- 1. GPU ------------------------------------------------------------------
sh("nvidia-smi")

# --- 2. Piper eğitim ortamı (sürüm sabit: v1.8.0) -----------------------------
sh("apt-get -qq update && apt-get -qq install -y build-essential cmake ninja-build > /dev/null")
if not PIPER.exists():
    sh(f"git clone -q --depth 1 --branch v1.8.0 https://github.com/OHF-voice/piper1-gpl.git {PIPER}")
sh("pip install -q -e '.[train]' onnxscript scikit-build cython", cwd=PIPER)
sh("python setup.py build_ext --inplace", cwd=PIPER)
sh("bash ./build_monotonic_align.sh", cwd=PIPER)
sys.path.insert(0, str(PIPER / "src"))
sh(f"{sys.executable} -c 'from piper.train.vits.monotonic_align import maximum_path; print(\"monotonic_align OK\")'",
   cwd=PIPER)
print("kurulum bitti:", elapsed(), flush=True)

# --- 3. Veri -----------------------------------------------------------------
rows = (IN / "metadata.csv").read_text(encoding="utf-8").strip().splitlines()
wavs = list(AUDIO.glob("*.wav"))
print(f"veri: {len(rows)} satır, {len(wavs)} ses dosyası; örnek: {rows[0]}", flush=True)

# --- 4. Başlangıç: önceki eğitimin son checkpoint'i varsa ondan devam, yoksa temel modelden ---------------
previous = sorted(glob.glob("/kaggle/input/**/checkpoints/last.ckpt", recursive=True))
base = TMP / "tr_TR-dfki-medium.ckpt"
if not previous and not base.exists():
    sh(f"wget -q -O {base} '{BASE_URL}'")

import torch  # noqa: E402

if previous:
    # önceki eğitimin zaman sayacı (Timer) geri yüklenirse max_time'ın bir kısmı harcanmış sayılır: temizle
    raw = torch.load(previous[0], map_location="cpu", weights_only=False)
    raw["callbacks"] = {k: v for k, v in raw.get("callbacks", {}).items() if "Timer" not in str(k)}
    start_ckpt = TMP / "resume.ckpt"
    torch.save(raw, start_ckpt)
    print(f"önceki eğitimden devam: {previous[0]} (epoch {raw.get('epoch')}, adım {raw.get('global_step')})",
          flush=True)
    del raw
else:
    from piper.train.__main__ import VitsModel  # noqa: E402

    linked = {"batch_size", "num_symbols"}
    allowed = set(inspect.signature(VitsModel.__init__).parameters) - {"self", "kwargs"} - linked
    raw = torch.load(base, map_location="cpu", weights_only=False)
    hp = {k: (str(v) if isinstance(v, PurePath) else v)
          for k, v in raw.get("hyper_parameters", {}).items() if k in allowed}
    start_ckpt = TMP / "finetune_start.ckpt"
    torch.save({"state_dict": raw["state_dict"], "hyper_parameters": hp, "epoch": 0, "global_step": 0,
                "pytorch-lightning_version": raw.get("pytorch-lightning_version", "2.0.0"),
                "optimizer_states": [], "lr_schedulers": []}, start_ckpt)
    del raw
    print("temel modelden başlangıç; ayarlar:", sorted(hp), flush=True)

# --- 5. Eğitim ---------------------------------------------------------------
(TMP / "bkv_train.py").write_text('''
import sys, torch
_original_load = torch.load
torch.load = lambda *a, **k: _original_load(*a, **{**k, "weights_only": False})
from piper.train import __main__ as train_module
train_module._DEFAULT_CALLBACKS = [c for c in train_module._DEFAULT_CALLBACKS
                                   if getattr(c, "monitor", None) != "val_mos"]
for callback in train_module._DEFAULT_CALLBACKS:
    callback.dirpath = sys.argv.pop(1)
sys.argv = ["piper.train"] + sys.argv[1:]
train_module.main()
''', encoding="utf-8")

hours = int(TRAIN_HOURS)
minutes = int((TRAIN_HOURS - hours) * 60)
config_path = WORK / f"{VOICE}.onnx.json"
sh(" ".join([
    sys.executable, str(TMP / "bkv_train.py"), str(CKPT_DIR), "fit",
    f"--data.voice_name {VOICE}",
    f"--data.csv_path {IN / 'metadata.csv'}",
    f"--data.audio_dir {AUDIO}",
    "--model.sample_rate 22050",
    "--data.espeak_voice tr",
    "--data.phoneme_type text",
    f"--data.cache_dir {TMP / 'cache'}",
    f"--data.config_path {config_path}",
    f"--data.batch_size {BATCH_SIZE}",
    "--data.num_workers 2",
    "--trainer.accelerator gpu --trainer.devices 1",
    "--trainer.precision 32",
    f"--trainer.max_time 00:{hours:02d}:{minutes:02d}:00",
    "--trainer.log_every_n_steps 20",
    f"--ckpt_path {start_ckpt}",
]), cwd=PIPER)
print("eğitim bitti:", elapsed(), flush=True)

# --- 6. ONNX'e dışa aktarma ---------------------------------------------------
last = CKPT_DIR / "last.ckpt"
if not last.exists():
    last = sorted(CKPT_DIR.glob("*.ckpt"), key=os.path.getmtime)[-1]
(TMP / "bkv_export.py").write_text('''
import sys, torch
_original_load = torch.load
torch.load = lambda *a, **k: _original_load(*a, **{**k, "weights_only": False})
_export = torch.onnx.export
def _legacy(*args, **kwargs):
    kwargs.setdefault("dynamo", False)
    return _export(*args, **kwargs)
torch.onnx.export = _legacy
from piper.train.export_onnx import main
sys.argv = ["export_onnx"] + sys.argv[1:]
main()
''', encoding="utf-8")
onnx_path = WORK / f"{VOICE}.onnx"
sh(f"{sys.executable} {TMP / 'bkv_export.py'} --checkpoint {last} --output-file {onnx_path}", cwd=PIPER)

config = json.loads(config_path.read_text(encoding="utf-8"))
config["sozcuk"] = {"name": "Ata", "gender": "erkek"}
config.setdefault("inference", {})["length_scale"] = 1.25   # Ata'nın tercihi (pilotta dinlendi): %25 yavaş
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"model: {onnx_path.stat().st_size / 1e6:.0f} MB, checkpoint: {last.name}", flush=True)

# --- 7. Dinleme örnekleri (Sözcük'ün kendi dönüştürücüsüyle) -------------------
sys.path.insert(0, str(IN))
import wave  # noqa: E402

import numpy as np  # noqa: E402
import onnxruntime  # noqa: E402

import pronunciation  # noqa: E402

session = onnxruntime.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
inference = config.get("inference", {})
samples = {
    "1_tanisma": "Merhaba, ben Sözcük. Yazdığınız metni sizin için sesli okuyabilirim.",
    "2_masal": "Bir varmış, bir yokmuş. Evvel zaman içinde, kalbur saman içinde, küçük bir kartal yaşarmış.",
    "3_sayilar": "Toplantı 21.09.2026 günü saat 10:30'da başlayacak; Dr. Ahmet Bey %15 indirim yapıldığını söyledi.",
    "4_soru": "Bugün hava çok güzel, değil mi? Hadi birlikte parka gidelim!",
    "6_kartal": "Kartal, oğlum, bu sesi sana bırakıyorum. Seni çok seviyorum.",
    "5_uzun": ("Öğretmenimiz hâlâ gelmedi, ama gelirse kitabın üçüncü bölümünü okuyacağız. "
               "Sonra herkes kendi düşüncesini anlatacak ve birbirimizi dikkatle dinleyeceğiz."),
}
for name, text in samples.items():
    ids = pronunciation.phoneme_ids(pronunciation.phonemize(text), config["phoneme_id_map"])
    audio = session.run(None, {
        "input": np.array([ids], dtype=np.int64),
        "input_lengths": np.array([len(ids)], dtype=np.int64),
        "scales": np.array([inference.get("noise_scale", 0.667), inference.get("length_scale", 1.0),
                            inference.get("noise_w", 0.8)], dtype=np.float32),
    })[0].squeeze()
    audio = (np.clip(audio / max(1.0, float(np.abs(audio).max())), -1, 1) * 32767).astype(np.int16)
    with wave.open(str(WORK / "ornekler" / f"{name}.wav"), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(config["audio"]["sample_rate"])
        out.writeframes(audio.tobytes())
    print(f"örnek: {name} ({len(audio) / config['audio']['sample_rate']:.1f} sn)", flush=True)

# yalnızca son checkpoint kalsın (devam eğitimi için); diğerleri çıktıyı şişirmesin
for ckpt in CKPT_DIR.glob("*.ckpt"):
    if ckpt.resolve() != last.resolve():
        ckpt.unlink()
if last.name != "last.ckpt":
    shutil.move(str(last), str(CKPT_DIR / "last.ckpt"))
print("bitti:", elapsed(), flush=True)
