# Nonverbal contextual death bank

Version 2 integrates **102 short performances: six existing actors x 17 death causes**, each strictly **three seconds or less**, into actual player, bot and GIGN test-target deaths. The six historical spoken death clips are excluded from precaching and cannot be selected by gameplay or auditions.

Each performance centers on one intense, compact scream (at most two vocal attacks), shaped by the cause. It signals death immediately, with no sentence, complaint, prolonged agony or terminal-breath sequence. The six old spoken death recordings are retained only as historical source assets. Frustrated dialogue belongs to the private respawn event, after the character is alive again.

The bank includes standard death (bullet/ordinary fatal damage), eight primaries and eight coupled reactions. **Phase, Null, Ward, Reveal and Overclock use standard death**; no special files are generated for these tactical states. The explicit mapping is in `data/death_voices.json` and the final manifest.

| Cause | Compact vocal performance |
| --- | --- |
| standard | Un seul cri de douleur soudain, attaque nette, mort immediate. |
| hydro | Un cri noye bref, gorge serree et couleur liquide. |
| electro | Un cri crispe coupe de spasmes electriques. |
| cryo | Un cri serre et raidi par le froid. |
| thermal | Un cri aigu de brulure, panique explosive. |
| toxic | Un cri rauque expulse par une gorge intoxiquee. |
| corrosion | Un cri de douleur rugueux, gorge agresse par l'acide. |
| sonic | Un cri tendu et vibrant, douleur de resonance. |
| kinetic | Un cri court et brutal avec l'air chasse par l'impact. |
| arc_chain | Un cri noye et electrique, hache dans une gorge serree. |
| superconduction | Un cri froid et crispe, secoue de spasmes electriques. |
| shatter | Un cri abrupt de fracture, froid et tranchant. |
| resonant_impact | Un cri d'impact brutal avec tremblement resonant. |
| cavitation | Un cri rugueux et liquide, gorge vibrante irritee. |
| caustic_contagion | Un cri etouffe, rapeux, gorge attaquee par poison et acide. |
| toxic_ignition | Un cri explosif et rauque de gorge empoisonnee qui brule. |
| steam_veil | Un cri suffoque, souffle coince par la vapeur. |

The actor identities come from the existing six ElevenLabs generated voices. The workshop does not create replacement speakers. Nonverbal direction uses [ElevenLabs audio tags](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-do-audio-tags-work-with-eleven-v3-and-v4); [Scribe](https://elevenlabs.io/docs/api-reference/speech-to-text/convert) checks decoded dry recordings for unintended lexical words. Audio-event tags and nonverbal interjections are accepted; other words block the final build. This automated check cannot guarantee acting quality or that a listener will recognize the cause.

New single-scream takes replace the original long sequences. Raw MP3 and source 22050 Hz / 16-bit masters are retained for provenance. The exported dry master removes dead air; any sustained cry over 2.8 seconds is shortened with pitch-preserving time compression. A 55 ms release avoids an abrupt cutoff. Both playable masters and every final game WAV have a strict three-second cap. The cause-specific sound color (for example muffled water or electrical modulation) and existing Half-Life chain produce mono **11025 Hz / unsigned 8-bit PCM**. The final manifest has empty text and no subtitle for these nonverbal clips.

Open **Atelier - Cris de mort.cmd** to compare one cause across the six actors and listen to game WAV, processed master and compact dry cry. The bank is in `assets/audio/operator-deaths`; both launchers deploy the game WAVs to `sound/vf_deaths`. `death-bank-game.zip` contains only the 102 game WAVs and their manifest, already arranged as `sound/vf_deaths` and `vf/death-voice-manifest.json`. Both the main launcher and the jk_botti launcher synchronize this bank along with the current DLLs.

```
python vector-fields/death_voice_workshop.py generate --limit 102
python vector-fields/death_voice_workshop.py check-speech --limit 102
python vector-fields/death_voice_workshop.py build
python vector-fields/tests/death_voice_assets_test.py
python vector-fields/tests/death_voice_native_test.py
python vector-fields/tests/respawn_voice_test.py
```

Version 1 and rejected takes are retained outside the active bank and ZIP. Generation and transcription use the existing encrypted key and versioned cache results. An uncertain request outcome leaves a pending marker for inspection rather than an automatic retry. Build and preview are offline.

## Native death dispatch

`VF_VoiceKilled` reads the victim's active server state **before** `VF_StatusClear`. The selected actor remains the actor of that life. `vfd::CauseFor` ignores expired states and all five tactical states. An active paired reaction takes priority over an active primary; if several states have the same kind, the most recently applied wins. With no eligible state, selection is `standard`. This chooses a cry; it does not reapply an effect or deal additional damage.

The same selector is used by `CVFRangeTarget::Killed`, before its reset. Every cause has priority 100 and replaces lower-priority speech on native positional CHAN_VOICE. The once-per-life guard prevents `Killed` and `DeathSound` from playing twice; gib deaths use the first hook too. Death cancels queued onset/spawn speech. `vf_voices 0` suppresses cries as well as dialogue. A death audition does not consume the real-death guard or mark a private respawn.

The bank stays separate from the historical 233-entry dialogue catalog, avoiding its byte-sized clip-index limit. `game_shared/vf_death_catalog.h` is generated offline. The four-byte `VFDeath` packet contains an entity short, actor byte and cause byte, for client validation and diagnostics, using reliable MSG_PAS_R like the native sound. Audio itself uses native sound replication; the receiver does not play a duplicate sound or display a caption. No engine modification or internet connection is required during play.

## Try it in the chamber

Restart **Jouer - Vector Fields.cmd**, then press **F4**. Shooting a target six times with a chosen elemental profile activates its state; killing it during the six-second state plays its matching cry. Targets respawn after two seconds. The existing **F3 > Test joueur / voix** controls apply states to the player and trigger real normal/gib deaths.

For a controlled target example, in the console (solo, or with `sv_cheats 1`):

```text
cmd vf_range_reset 0
cmd vf_range_voice 0 rocco
cmd vf_range_effect 0 hydro
cmd vf_range_effect 0 electro
cmd vf_range_kill 0
```

This kills target 0 with the `arc_chain` cry. `vf_range_effect 0 EFFECT [SECONDS]` accepts the 21 authoritative state IDs, including direct paired reactions. `vf_range_voice` accepts the six existing actor IDs. These probes are restricted to `vf_range` and developer access. `vf_range_info` reports all states; `vf_range_reset` restores a dead target for immediate iteration.

The native matrix exercises all 102 files through actual target damage, tactical fallback for all six actors, all 21 states on actual player deaths, normal/gib paths, expired/cleared states, automatic pair formation, simultaneous-state precedence and a real six-bullet proc. The two-client respawn regression verifies nearby death metadata and continued owner-only complaints. These checks prove dispatch and native loading; subjective acting and mix balance still need listening.

