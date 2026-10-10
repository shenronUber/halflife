"""Produce original bilingual operator voices and deterministic game assets offline.

The encrypted ElevenLabs key is loaded by audio_workshop; it never enters assets.
Commands: design, generate, build, preview, status. Requests are resumable and
ambiguous provider outcomes keep a pending marker instead of being retried.
"""
from __future__ import annotations
import argparse, base64, hashlib, html, json, re, sys, wave, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import audio_workshop as audio

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets/audio/operators"
DATA = ROOT / "data/voices.json"
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def catalog():
    data = read(DATA)
    assert 1 <= len(data["actors"]) <= 8
    assert len({a["id"] for a in data["actors"]}) == len(data["actors"])
    effects = read(ROOT / "data/effects.json")["effects"]
    assert all(e["id"] in data["events"] for e in effects)
    assert len(set(data["events"])) == len(data["events"])
    assert len(data["events"]) <= 32, "Voice scheduler capacity exceeded"
    for actor in data["actors"]:
        assert set(actor["lines"]) == set(data["events"])
        assert all(1 <= len(actor["lines"][event]) <= 16 for event in data["events"])
    return data
def folder(actor):
    p = ASSETS / actor["id"]
    p.mkdir(parents=True, exist_ok=True)
    return p
def signature(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
def json_request(target, endpoint, body, key):
    pending = target.with_suffix(".pending")
    if target.exists():
        result = read(target)
        if result["request_sha256"] != signature(body):
            raise RuntimeError(f"Request changed: {target}. Use a new version.")
        return result
    if pending.exists():
        raise RuntimeError(f"Unknown previous outcome: {pending}. Inspect provider history.")
    audio.json_write(pending, {"endpoint": endpoint, "request_sha256": signature(body)})
    try:
        payload, headers = audio.api(endpoint, key, body)
    except RuntimeError as error:
        if str(error).startswith("ElevenLabs HTTP 4"):
            pending.unlink()
        raise
    result = {"request_sha256": signature(body), "request": body,
              "response": json.loads(payload),
              "request_id": headers.get("request-id") or headers.get("Request-Id")}
    audio.json_write(target, result)
    pending.unlink()
    return result
def design():
    key = audio.load_key()
    audio.status(key)
    for i, actor in enumerate(catalog()["actors"]):
        dst = folder(actor)
        body = {"voice_description": actor["direction"], "text": actor["audition"],
                "model_id": "eleven_ttv_v3", "seed": 1917 + i,
                "guidance_scale": 5}
        result = json_request(dst / "design.json", "/v1/text-to-voice/design", body, key)
        previews = result["response"]["previews"]
        for j, item in enumerate(previews):
            (dst / f"audition_{j+1}.mp3").write_bytes(base64.b64decode(item["audio_base_64"]))
        selected = previews[0]["generated_voice_id"]
        created = json_request(dst / "voice.json", "/v1/text-to-voice",
            {"voice_name": "VF / " + actor["name"], "voice_description": actor["direction"],
             "generated_voice_id": selected,
             "labels": {"gender": "male", "accent": actor["accent"], "use_case": "video_game"}}, key)
        print("VOICE", actor["id"], created["response"]["voice_id"], flush=True)
    preview()
def line_items():
    for actor in catalog()["actors"]:
        for event, variants in actor["lines"].items():
            for variant, text in enumerate(variants):
                yield actor, event, variant, text
def generate(limit):
    key = audio.load_key()
    quota = audio.status(key)
    if quota.get("remaining_credits_reported", 1) <= 0:
        raise RuntimeError("Included quota exhausted.")
    jobs = list(line_items())
    jobs = [job for job in jobs if not (folder(job[0]) / f"{job[1]}_{job[2]}.json").exists()][:limit]
    # At most two requests in flight, each writes distinct assets.
    def one(job):
        actor, event, variant, text = job
        dst = folder(actor)
        voice = read(dst / "voice.json")["response"]["voice_id"]
        body = {"text": text, "model_id": "eleven_v4",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}}
        stem = dst / f"{event}_{variant}"
        pending = stem.with_suffix(".pending")
        if pending.exists():
            raise RuntimeError(f"Uncertain earlier TTS outcome: {pending}")
        request_hash = signature(body)
        audio.json_write(pending, {"request_sha256": request_hash, "voice_id": voice})
        try:
            raw, headers = audio.api("/v1/text-to-speech/" + voice + "?output_format=mp3_44100_128", key, body)
        except RuntimeError as error:
            if str(error).startswith("ElevenLabs HTTP 4"):
                pending.unlink()
            raise
        if len(raw) < 128 or not (raw[:3] == b"ID3" or (raw[0] == 255 and raw[1] & 224 == 224)):
            raise RuntimeError("Invalid MP3 response; pending marker retained.")
        stem.with_suffix(".mp3").write_bytes(raw)
        if not audio.convert(stem.with_suffix(".mp3"), stem.with_name(stem.name+"_master.wav")):
            raise RuntimeError("ffmpeg is required to build engine WAVs.")
        audio.json_write(stem.with_suffix(".json"),
            {"provider": "ElevenLabs", "voice_id": voice, "model_id": "eleven_v4",
             "event": event, "variant": variant, "text": text, "request": body,
             "request_sha256": request_hash, "sha256": hashlib.sha256(raw).hexdigest(),
             "request_id": headers.get("request-id") or headers.get("Request-Id"),
             "reported_credit_cost": headers.get("character-cost") or headers.get("Character-Cost")})
        pending.unlink()
        game_wav(stem.with_name(stem.name+"_master.wav"),stem.with_suffix(".wav"))
        print("SAVED", actor["id"], event, variant, flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for _ in pool.map(one, jobs):
            pass
    audio.status(key)
    preview()
# Match the previous installed-Half-Life voice audit, without degrading masters.
HL_FILTER = "highpass=f=100,lowpass=f=4800,acompressor=threshold=0.12:ratio=2:attack=5:release=80:makeup=1.4,alimiter=limit=0.90:level=false,aresample=11025:osf=u8:dither_method=triangular"
def game_wav(master, destination):
    executable = audio.ffmpeg()
    if not executable:
        raise RuntimeError("ffmpeg is required for the Half-Life export.")
    subprocess.run([executable,"-hide_banner","-loglevel","error","-y","-i",str(master),
                    "-vn","-ac","1","-af",HL_FILTER,"-ar","11025","-c:a","pcm_u8",str(destination)],check=True)
def retro():
    for actor,event,vi,text in line_items():
        wav = folder(actor)/f"{event}_{vi}.wav"
        master = wav.with_name(wav.stem+"_master.wav")
        if not master.exists():
            if not wav.exists():
                continue
            with wave.open(str(wav)) as w:
                assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2),wav
            shutil.copy2(wav,master)
        game_wav(master,wav)
    print("Half-Life exports: mono PCM, 11025 Hz, unsigned 8-bit, filtered and compressed.",flush=True)
# The native HL text renderer uses a legacy single-byte font. Keep the synthesis
# Cyrillic/native spellings, but transliterate subtitle metadata for that renderer.
def caption(text):
    text = re.sub(r"\[[^\]]+\]\s*", "", text)
    ru = {"а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"yo","ж":"zh","з":"z","и":"i","й":"y",
          "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
          "х":"kh","ц":"ts","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya"}
    text = "".join((ru[c.lower()].capitalize() if c.isupper() else ru[c]) if c.lower() in ru else c for c in text)
    import unicodedata
    text = ''.join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    greek = dict(zip("αβγδεζηθικλμνξοπρσςτυφχψω", ["a","v","g","d","e","z","i","th","i","k","l","m","n","x","o","p","r","s","s","t","y","f","ch","ps","o"]))
    text = ''.join((greek[c.lower()].capitalize() if c.isupper() else greek[c]) if c.lower() in greek else c for c in text)
    return text.replace("\u00df", "ss").encode("ascii", "ignore").decode()
def build():
    retro()
    data = catalog()
    report = {"actors": [], "clips": [], "missing": []}
    lines = []
    for ai, actor in enumerate(data["actors"]):
        report["actors"].append({"id": actor["id"], "name": actor["name"], "accent": actor["accent"]})
        for event, variants in actor["lines"].items():
            for vi, text in enumerate(variants):
                wav = folder(actor) / f"{event}_{vi}.wav"
                if not wav.exists():
                    report["missing"].append(str(wav))
                    continue
                meta = read(wav.with_suffix('.json'))
                assert meta['text'] == text and meta['event'] == event and meta['variant'] == vi, wav
                assert meta['voice_id'] == read(folder(actor)/'voice.json')['response']['voice_id'], wav
                assert meta['sha256'] == hashlib.sha256(wav.with_suffix('.mp3').read_bytes()).hexdigest(), wav
                with wave.open(str(wav)) as w:
                    assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1,1,11025), wav
                    duration = w.getnframes()/w.getframerate()
                    assert 0.15 < duration <= 8, (wav, duration)
                clip = {"actor": ai, "event": data["events"].index(event), "variant": vi,
                        "path": f"vf_voices/{actor['id']}/{event}_{vi}.wav", "text": caption(text),
                        "duration": round(duration, 4), "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}
                lines.append(clip)
                report["clips"].append(clip)
    if report["missing"]:
        raise RuntimeError(f"{len(report['missing'])} voice WAVs missing. Run generate.")
    assert len(lines) < 256
    q = lambda s: json.dumps(s, ensure_ascii=True)
    h = ["// Generated by vector-fields/voice_workshop.py build. Edit data/voices.json.",
         "#ifndef VF_VOICE_CATALOG_H", "#define VF_VOICE_CATALOG_H", "namespace vfv {",
         "enum Event {"+",".join("E_"+x for x in data["events"])+", EventCount };",
         "struct Actor {const char *id,*name;};", "static const Actor Actors[]={"]
    h += ["{"+q(a["id"])+","+q(a["name"])+"}," for a in data["actors"]]
    h += ["};","struct Clip {int actor,event,variant; const char *path,*text; float duration;};",
          "static const Clip Clips[]={"]
    h += ["{"+f'{c["actor"]},{c["event"]},{c["variant"]},'+q(c["path"])+","+q(c["text"])+","+str(c["duration"])+"f}," for c in lines]
    h += ["};", "static const int ActorCount=sizeof(Actors)/sizeof(Actors[0]);",
          "static const int ClipCount=sizeof(Clips)/sizeof(Clips[0]);",
          "static const char* Events[]={"+",".join(q(e) for e in data["events"])+"};", "}", "#endif"]
    (ROOT.parent / "game_shared/vf_voice_catalog.h").write_text("\n".join(h)+"\n")
    report["format"] = {"channels":1, "sample_rate":11025, "sample_width":1}
    audio.json_write(ASSETS / "manifest.json", report)
    print("BUILT", len(lines), "clips", flush=True)
    preview()
def preview():
    cards = []
    for actor in catalog()["actors"]:
        dst = folder(actor)
        content = [f'<article><h2>{html.escape(actor["name"])}</h2><p>{html.escape(actor["accent"]+" / "+actor["temperament"])}</p>']
        for audition in sorted(dst.glob("audition_*.mp3")):
            rel = audition.relative_to(ASSETS).as_posix()
            content.append(f'<details><summary>Voice design / {audition.stem}</summary><audio controls preload="none" src="{rel}"></audio></details>')
        for event, variants in actor["lines"].items():
            for vi, text in enumerate(variants):
                wav = dst / f"{event}_{vi}.wav"
                if wav.exists():
                    rel = wav.relative_to(ASSETS).as_posix()
                    master = wav.with_name(wav.stem+"_master.wav").relative_to(ASSETS).as_posix()
                    original = wav.with_suffix(".mp3").relative_to(ASSETS).as_posix()
                    content.append(f'<div class="clip" data-event="{event}"><small>{event} / {vi+1}</small><p>{html.escape(text)}</p><label>Half-Life / game WAV</label><audio controls preload="none" src="{rel}"></audio><details><summary>Compare clean master and original</summary><label>Clean master</label><audio controls preload="none" src="{master}"></audio><label>ElevenLabs original</label><audio controls preload="none" src="{original}"></audio></details></div>')
        content.append("</article>")
        cards.append("".join(content))
    document = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Vector Fields / Operator voices</title>
<style>body{font:16px system-ui;background:#10151c;color:#e9f0f6;margin:36px;padding:0 18px}h1{margin-bottom:6px}p{line-height:1.45;color:#c0cfdb}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}article{background:#1c2530;border:1px solid #344457;border-radius:12px;padding:18px}h2{font-size:22px}.clip{border-top:1px solid #344457;margin-top:16px;padding-top:12px}small{color:#7cd9bd}audio{width:100%;height:36px}select{font:inherit;margin:12px 0 24px;padding:8px;background:#1c2530;color:white}@media(max-width:1100px){main{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){main{grid-template-columns:1fr}}</style>
<h1>Six voices. Six very different tempers.</h1>
<p>Original male operators. English dialogue with native interjections. Game WAVs: mono 11,025 Hz / 8-bit, filtered and compressed to match our Half-Life reference. Originals and clean masters are preserved.</p>
<label for="filter">Compare an event: </label><select id="filter"><option value="">All events</option>"""
    document += "".join(f'<option>{e}</option>' for e in catalog()["events"])+"</select><main>"+"".join(cards)+"</main>"
    document += """<script>document.querySelector('#filter').onchange=e=>document.querySelectorAll('.clip').forEach(c=>c.hidden=!!e.target.value&&c.dataset.event!==e.target.value);document.addEventListener('play',e=>document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()}),true)</script></html>"""
    (ASSETS/"listen.html").write_text(document,encoding="utf-8")
if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["design","generate","build","preview","status","retro"])
    p.add_argument("--limit",type=int,default=200)
    a = p.parse_args()
    try:
        if a.command == "generate": generate(a.limit)
        elif a.command == "status": audio.status(audio.load_key())
        else: globals()[a.command]()
    except (RuntimeError,OSError,ValueError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)

