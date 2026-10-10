# ElevenLabs audio listening tests

All character dialogue is in English. These are development candidates, not new lootpool weapons or sounds already connected to gameplay.

## First batch

Six isolated firing signatures: R1 service rifle, suppressed compact pistol, heavy shotgun, Bedrock industrial launcher, induction discharge and Abyss pneumatic harpoon. Each recipe requests one immediate shot, with no music or ambient background. The model's result still needs listening review for repeated shots and unwanted tails. The game WAV export decodes to float, trims leading silence with a 2 ms attack margin and matches sample peaks to -2 dBFS before 16-bit quantization; the original MP3 remains untouched.

Three short English lines have been generated with Daniel and Sarah (eleven_v4):

- Reload: "Reloading. Cover me."
- Contact: "Contact ahead. Stay sharp."
- Shield loss: "Shield down. Moving to cover."

Voice directions are design notes; the current stock-voice API receives the line and voice settings, not these notes. Music is deferred until the firing and voice tests have been reviewed.

## Half-Life voice format

An audit of the installed Steam Half-Life files is recorded in `half-life-audio-reference.json`. Barney (178 WAVs), scientist (385), G-Man (18), VOX (616) and FVOX (142) are all uncompressed mono PCM at **11,025 Hz, 8-bit**. HGrunt has 326 at that format and three at 22,050 Hz, 8-bit.

The retro character comes from restricted bandwidth and 8-bit quantization, alongside the original performances and processing. This is different from lossy MP3 compression. Our own voices keep the original ElevenLabs MP3 plus three WAV exports:

- `.wav`: mono 22,050 Hz, signed 16-bit PCM; a cleaner game-compatible reference.
- `_hl.wav`: mono 11,025 Hz, unsigned 8-bit PCM, 100 Hz high-pass / 4,800 Hz low-pass, mild dynamic compression and peak limiting.
- `_radio.wav`: same retro PCM format, 300–3,200 Hz voice band with stronger compression.

The two filters are our proposed sound design, not a claim to reproduce Valve's original studio processing. No original Half-Life recordings are copied into the candidates.

## Local setup

The API key is encrypted with Windows DPAPI for the current Windows account in `vector-fields/.local/elevenlabs-key.dpapi`. The entire local directory is ignored by Git. An `ELEVENLABS_API_KEY` environment variable can override it. Keys are not written into audio metadata or HTML.

The key needs Sound Effects access and Text to Speech access. Voices read access is used to list account voices; the tool can also use public default IDs documented by ElevenLabs when that permission is absent. User read access is optional for quota reporting.

```powershell
python vector-fields/audio_workshop.py configure
python vector-fields/audio_workshop.py status
python vector-fields/audio_workshop.py voices
python vector-fields/audio_workshop.py generate --kind sfx --limit 6
python vector-fields/audio_workshop.py generate --kind voice --voice-ids VOICE_ONE,VOICE_TWO --limit 6
python vector-fields/audio_workshop.py preview --open
```

`Atelier - Audio.cmd` opens the listening comparison page. FFmpeg is supplied by the local `imageio-ffmpeg` package under `vector-fields/.local/python`, or by a system installation.

The workshop saves original responses, request parameters, hashes and the reported credit cost when supplied by ElevenLabs. Existing matching candidates are reused. Changed recipes need a new ID. There are no automatic generation retries; an uncertain request leaves a `.pending` marker so the provider history can be checked before another charge. Explicit HTTP 4xx rejections clear that marker.

The batch limit controls request count, not a monetary cap. Quota is checked when User read is allowed. API access and billing entitlements depend on the account; the workshop does not upgrade a subscription or change billing settings.

## API references

- [Sound effects](https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert)
- [Text to speech](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
- [User subscription](https://elevenlabs.io/docs/api-reference/user/subscription/get)
- [Voice list](https://elevenlabs.io/docs/api-reference/voices/search)

## First batch results

Twelve successful generation requests produced six shots and six voice performances. Each voice has clean, Half-Life and radio WAV versions. WAV headers, durations, non-silence, original-response hashes and all audio links were checked; see `validation.json`. Final selection still requires listening.

Public default voice IDs: [ElevenLabs voice documentation](https://github.com/elevenlabs/plugin/blob/main/skills/general/text-to-speech/SKILL.md#voice-ids).
