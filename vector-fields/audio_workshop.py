"""Small, resumable ElevenLabs listening workshop. No game runtime dependency."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets/audio/elevenlabs"
LOCAL = ROOT / ".local"
KEY_PATH = LOCAL / "elevenlabs-key.dpapi"
BASE_URL = "https://api.elevenlabs.io"
RECIPES = ASSETS / "recipes.json"


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def protect(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Local key storage uses Windows DPAPI. Elsewhere use ELEVENLABS_API_KEY.")
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    result = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.restype = wintypes.BOOL
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(ctypes.cast(result.data, ctypes.c_void_p))


def load_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and KEY_PATH.exists():
        key = protect(KEY_PATH.read_bytes(), decrypt=True).decode("utf-8")
    if not key:
        raise RuntimeError("No API key. Run: python vector-fields/audio_workshop.py configure")
    return key


def api(path, key, body=None):
    headers = {"xi-api-key": key, "User-Agent": "VectorFields-AudioWorkshop/1",
               "Accept": "application/json" if body is None else "audio/mpeg"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            payload = response.read()
            return payload, dict(response.headers)
    except urllib.error.HTTPError as error:
        # Report only the provider error code and permission identifier.
        try:
            detail = json.loads(error.read()).get("detail", {})
            code = detail.get("status", "unknown") if isinstance(detail, dict) else "unknown"
            code = "".join(c for c in str(code)[:80] if c.isalnum() or c in "_-")
            import re
            message = detail.get("message", "") if isinstance(detail, dict) else ""
            match = re.search(r"permission\s+([a-z_]+)", message)
            permission = match.group(1) if match else "unknown"
        except (ValueError, AttributeError):
            code, permission = "unknown", "unknown"
        raise RuntimeError(f"ElevenLabs HTTP {error.code} ({code}); required permission: {permission}.") from None
    except urllib.error.URLError:
        raise RuntimeError("ElevenLabs network error. Generation is not automatically retried.") from None


def api_json(path, key):
    return json.loads(api(path, key)[0])


def status(key):
    try:
        data = api_json("/v1/user/subscription", key)
    except RuntimeError as error:
        if "(missing_permissions)" not in str(error):
            raise
        print('{"subscription_read": false, "note": "Key does not allow account/quota lookup."}', flush=True)
        return {}
    summary = {field: data.get(field) for field in
               ("tier", "status", "character_count", "character_limit")}
    remaining = max(0, (data.get("character_limit") or 0) - (data.get("character_count") or 0))
    summary["remaining_credits_reported"] = remaining
    print(json.dumps(summary, indent=2), flush=True)
    return data


def ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    sys.path.insert(0, str(LOCAL / "python"))
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def convert(source, destination):
    executable = ffmpeg()
    if not executable:
        return False
    import array
    import wave
    decoded = subprocess.run([executable, "-hide_banner", "-loglevel", "error",
                              "-i", str(source), "-vn", "-ac", "1", "-ar", "22050",
                              "-f", "f32le", "-"], check=True, stdout=subprocess.PIPE).stdout
    samples = array.array("f")
    samples.frombytes(decoded)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise RuntimeError("Empty decoded audio.")
    peak = max(abs(x) for x in samples)
    if peak < 0.00001:
        raise RuntimeError("Silent decoded audio.")
    # Keep 2 ms before the first significant sample; preserve the attack.
    first = next((i for i, x in enumerate(samples) if abs(x) >= peak * 0.005), 0)
    start = max(0, first - 44)
    samples = samples[start:]
    factor = 0.794328 / peak  # -2 dBFS sample peak, leaving mixing headroom.
    pcm = array.array("h", (max(-32768, min(32767, round(x * factor * 32767))) for x in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(22050)
        output.writeframes(pcm.tobytes())
    return True


def voice_versions(source):
    executable = ffmpeg()
    if not executable:
        return
    clean = source.with_suffix(".wav")
    input_path = clean if clean.exists() else source
    profiles = {
        "hl": "highpass=f=100,lowpass=f=4800,acompressor=threshold=0.12:ratio=2:attack=5:release=80:makeup=1.4,alimiter=limit=0.90:level=false,aresample=11025:osf=u8:dither_method=triangular",
        "radio": "highpass=f=300,lowpass=f=3200,acompressor=threshold=0.10:ratio=3:attack=2:release=60:makeup=1.6,alimiter=limit=0.85:level=false,aresample=11025:osf=u8:dither_method=triangular"
    }
    for label, filters in profiles.items():
        target = source.with_name(source.stem + "_" + label + ".wav")
        subprocess.run([executable, "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(input_path), "-vn", "-ac", "1", "-af", filters,
                        "-ar", "11025", "-c:a", "pcm_u8", str(target)], check=True)


def preview():
    cards = []
    for path in sorted(ASSETS.glob("**/*.json")):
        if path.name == "recipes.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if "request_sha256" not in data:
            continue
        mp3 = path.with_suffix(".mp3")
        if not mp3.exists():
            continue
        rel = mp3.relative_to(ASSETS).as_posix()
        text = data.get("text") or data.get("prompt", "")
        players = '<label>Original</label><audio controls preload="none" src="' + html.escape(rel, quote=True) + '"></audio>'
        clean = mp3.with_suffix(".wav")
        if data["kind"] == "sfx" and clean.exists():
            url = clean.relative_to(ASSETS).as_posix()
            players = '<label>Game WAV / level matched</label><audio controls preload="none" src="' + html.escape(url, quote=True) + '"></audio>' + players
        for suffix, label in [("_hl.wav", "Half-Life / mono 11,025 Hz, 8-bit"), ("_radio.wav", "Radio / mono 11,025 Hz, 8-bit")]:
            candidate = mp3.with_name(mp3.stem + suffix)
            if candidate.exists():
                url = candidate.relative_to(ASSETS).as_posix()
                players += '<label>' + label + '</label><audio controls preload="none" src="' + html.escape(url, quote=True) + '"></audio>'
        cards.append('<article><h2>' + html.escape(data["name"]) + '</h2><p>' +
                     html.escape(text) + '</p>' + players + '<small>' +
                     html.escape(data.get("voice_name") or data["kind"]) + '</small></article>')
    document = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>Vector Fields — Audio Workshop</title>
<style>body{font:16px system-ui;background:#10151c;color:#e9f0f6;max-width:1080px;margin:40px auto;padding:0 24px}
h1{font-size:30px} main{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px}
article{background:#1c2530;border:1px solid #344457;border-radius:12px;padding:20px}
h2{font-size:19px;margin-top:0}p{line-height:1.5;color:#bacada}audio{width:100%;margin:12px 0}small{display:block;color:#7cd9bd}
</style><h1>Vector Fields / Audio Workshop</h1>
<p>ElevenLabs listening candidates. English voices. These files are not yet connected to gameplay.</p><main>"""
    document += "".join(cards) or "<p>No generated candidates yet.</p>"
    document += "</main><script>document.addEventListener('play',e=>{document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true)</script></html>"
    path = ASSETS / "listen.html"
    path.write_text(document, encoding="utf-8")
    print(f"Listening page: {path}", flush=True)
    return path


def generate_one(key, kind, item, request, endpoint, voice=None):
    identifier = item["id"]
    if not identifier or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in identifier):
        raise RuntimeError("Invalid asset id.")
    folder = ASSETS / ("shots" if kind == "sfx" else "voices")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (identifier + ".mp3")
    meta = target.with_suffix(".json")
    pending = target.with_suffix(".pending")
    signature = hashlib.sha256(json.dumps({"endpoint": endpoint, "body": request}, sort_keys=True).encode()).hexdigest()
    if target.exists():
        if not meta.exists() or json.loads(meta.read_text(encoding="utf-8"))["request_sha256"] != signature:
            raise RuntimeError(f"Existing candidate differs: {identifier}. Use a new recipe id.")
        print(f"Cached: {identifier}", flush=True)
        if not target.with_suffix(".wav").exists():
            convert(target, target.with_suffix(".wav"))
        if kind == "voice":
            voice_versions(target)
        return
    if pending.exists():
        raise RuntimeError(f"Uncertain earlier request for {identifier}. Check ElevenLabs history before retrying.")
    json_write(pending, {"id": identifier, "started_utc": datetime.now(timezone.utc).isoformat(),
                         "request_sha256": signature})
    print(f"Generating {kind}: {identifier}", flush=True)
    try:
        audio, headers = api(endpoint, key, request)
    except RuntimeError as error:
        if str(error).startswith("ElevenLabs HTTP 4"):
            pending.unlink()
        raise
    if len(audio) < 128 or not (audio[:3] == b"ID3" or (audio[0] == 255 and audio[1] & 224 == 224)):
        raise RuntimeError(f"Invalid MP3 response for {identifier}; pending marker retained.")
    temporary = target.with_suffix(".mp3.tmp")
    temporary.write_bytes(audio)
    info = {"provider": "ElevenLabs", "kind": kind, "name": item["name"],
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "request_sha256": signature, "request": request, "endpoint": endpoint,
            "sha256": hashlib.sha256(audio).hexdigest(),
            "bytes": len(audio), "text": request.get("text", ""),
            "request_id": headers.get("request-id") or headers.get("Request-Id"),
            "reported_credit_cost": headers.get("character-cost") or headers.get("Character-Cost")}
    if voice:
        info.update(voice_id=voice["voice_id"], voice_name=voice["name"], language="en")
    json_write(meta, info)
    temporary.replace(target)
    pending.unlink()
    convert(target, target.with_suffix(".wav"))
    if kind == "voice":
        voice_versions(target)
    preview()
    print(f"Saved: {target.name}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["configure", "status", "voices", "plan", "generate", "preview"])
    parser.add_argument("--kind", choices=["sfx", "voice"], default="sfx")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--voice-ids", default="")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    recipes = json.loads(RECIPES.read_text(encoding="utf-8"))
    if args.command == "plan":
        print(json.dumps(recipes, ensure_ascii=False, indent=2))
        return
    if args.command == "preview":
        path = preview()
        if args.open:
            import webbrowser
            webbrowser.open(path.as_uri())
        return
    if args.command == "configure":
        print("Enter API key (it will not be printed):", flush=True)
        if sys.stdin.isatty():
            import getpass
            key = getpass.getpass("")
        else:
            key = sys.stdin.readline()
        key = key.strip()
        if not key or any(c.isspace() for c in key):
            raise RuntimeError("Empty or invalid key.")
        status(key)
        LOCAL.mkdir(exist_ok=True)
        (LOCAL / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
        KEY_PATH.write_bytes(protect(key.encode("utf-8")))
        print("API connected. Key saved with Windows DPAPI, outside versioned assets.", flush=True)
        return
    key = load_key()
    if args.command == "status":
        status(key)
    elif args.command == "voices":
        data = api_json("/v2/voices?page_size=100", key)
        voices = data.get("voices", [])
        json_write(LOCAL / "elevenlabs-voices.json", voices)
        print(json.dumps([{k: v.get(k) for k in ("voice_id", "name", "category", "labels", "description")}
                          for v in voices], ensure_ascii=False, indent=2))
    elif args.command == "generate":
        if not 1 <= args.limit <= 12:
            raise RuntimeError("Each listening batch is limited to 1–12 requests.")
        current = status(key)
        if current.get("character_limit") and current.get("character_count", 0) >= current["character_limit"]:
            raise RuntimeError("Included quota exhausted; no generation requested.")
        if args.kind == "sfx":
            for item in recipes["sound_effects"][:args.limit]:
                request = {"text": item["prompt"], "duration_seconds": item["duration_seconds"],
                           "prompt_influence": 0.5, "loop": False, "model_id": "eleven_text_to_sound_v2"}
                generate_one(key, "sfx", item, request, "/v1/sound-generation?output_format=mp3_44100_128")
        else:
            ids = [x.strip() for x in args.voice_ids.split(",") if x.strip()]
            if not ids:
                raise RuntimeError("Choose a voice with 'voices', then provide --voice-ids.")
            try:
                voices = api_json("/v2/voices?page_size=100", key).get("voices", [])
            except RuntimeError as error:
                if "(missing_permissions)" not in str(error):
                    raise
                # Public default IDs documented by ElevenLabs. TTS still requires
                # its own permission; this does not read restricted account data.
                voices = [
                    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George"},
                    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah"},
                    {"voice_id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel"},
                    {"voice_id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte"}
                ]
            lookup = {v["voice_id"]: v for v in voices}
            calls = 0
            for voice_id in ids:
                if voice_id not in lookup:
                    raise RuntimeError("Selected voice not found in the account's first 100 voices.")
                voice = lookup[voice_id]
                for line in recipes["voice_lines"]:
                    if calls >= args.limit:
                        break
                    item = {"id": voice_id.lower() + "_" + line["id"], "name": voice["name"] + " / " + line["event"]}
                    request = {"text": line["text"], "model_id": "eleven_v4", "language_code": "en",
                               "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
                    generate_one(key, "voice", item, request,
                                 "/v1/text-to-speech/" + voice_id + "?output_format=mp3_44100_128", voice)
                    calls += 1
        preview()
        status(key)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
