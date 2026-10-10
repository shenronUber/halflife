# Six bilingual operators

The dialogue archive contains **233 original ElevenLabs performances**, of which 227 remain active. Its six spoken deaths are replaced in gameplay by **102 nonverbal cries** for the same six male characters:

| Actor | Accent and code switching | Temperament |
| --- | --- | --- |
| Rocco Bellini | Italian / English | Flamboyant showman; warm raspy tenor |
| Lucien Moreau | French / English | Elegant, dry and sarcastic baritone |
| Diego Vega | Spanish / English | Quick, bright, provocative skirmisher |
| Viktor Volkov | Russian / English | Low gravel bass, clipped deadpan humour |
| Otto Stahl | German / English | Stern baritone, methodical and dryly sarcastic |
| Nikos Petros | Greek / English | Warm husky baritone, proud and exuberant |

Dialogue remains mostly English. Brief native interjections use native spellings in synthesis; the legacy Half-Life subtitle font receives transliteration where necessary. Voices are original generated characters, with no real-person voice reference. `data/voices.json` is the editable script and direction source.

## In the game

A server-selected random voice is assigned on each actual spawn and kept for that life. Save/load preserves its identity. **J** calls `cmd vf_taunt`; a six-second cooldown and priority gate suppress repeated presses. Nearby players hear the same positional WAV through the native sound protocol. Speech uses CHAN_VOICE and does not interrupt weapon or footstep channels.

Each first appearance retains the actor's original `spawn` line. A real death marks the next life for **respawn** instead: three frustrated, comic, fourth-wall responses per actor (18 performances), blaming the controller, the weapon or the game/engine. The new life still receives a random actor. The last private clip is retained across lives to avoid an immediate identical repeat, and the death context is saved independently of whether voices are enabled. Auditioning a death line does not count as a real death.

Respawn complaints are **owner-only**. The server sends a reliable `VFVoice` packet only to that player and emits no positional sound for this event. The owner plays the precached sample locally on CHAN_VOICE, with no attenuation; other clients receive neither the complaint nor its caption. Local playback remains enabled when subtitles are turned off. Bots have no human owner and do not broadcast these personal complaints. A pending spawn line is cancelled by death or restore.

Successful reloads, enemy player kills, injuries, critical health (crossing 25), armor depletion and recognised legacy elemental damage trigger appropriate lines. Deaths trigger a separate nonverbal cry. Each event has a cooldown, and variants avoid immediate repetition. Critical health, armor loss and elemental cues take precedence over generic pain. Death preempts the current utterance. Spectators and dead players cannot taunt. Killing a teammate or oneself does not earn a kill quip.

The eight elements, eight paired reactions and five tactical states now have a server-authoritative temporary lifecycle, shared visuals and contextual speech. Legacy elemental damage applies the corresponding state for four seconds. Applying a compatible second primary consumes both primaries and creates their paired reaction (A+B = B+A); only primaries combine, with no triple reaction. If multiple partners are present, the most recently applied compatible primary wins. Reapplying an active state refreshes its duration without replaying its onset line. These states currently implement visual/audio feedback; damage, movement and tactical ability balance remain to be designed.

Effect onsets coalesce for 120 ms, so rapidly applied components announce their result. A reaction has priority over a primary cue. A blocked effect cue waits at most two seconds, and is cancelled if its state expires, is removed or the player dies. Critical health and armor loss take precedence over elemental dialogue on the same hit. Normal and gib deaths both emit one short nonverbal cry per life, selected from active elemental states before clearing them. Spawn, restore and disconnect clear temporary states; late joiners receive active states with their remaining duration, without replaying old speech.

Future gameplay should call `VF_ApplyPlayerEffect(player, vfs::S_EFFECT, duration)` from `dlls/vf_status.h`, rather than emitting a voice separately. The same entry point is exercised by the developer panel.

Client `vf_voice_subtitles`: 0 off, 1 own character (default), 2 nearby received voice events. Server `vf_voices 0` disables character speech; `vf_taunts 0` disables taunts. Sound volume follows the engine's master volume.

## Taunts, counters and bot decisions

**J** sends a normal taunt when no recent audible provocation is remembered. If another living player taunted within the configured radius and the engine's potentially audible region, the same key selects **counter_taunt**: three aggressive generic responses per actor (18 new performances). The latest heard normal taunt supplies the target. A counter is consumed only when speech actually starts, so a blocked key press does not discard a valid reply. Taunts and counters share a cooldown. A response does not create another response opportunity, preventing autonomous infinite chains.

The reply opportunity lasts through the source clip plus five seconds by default. The target must still be alive, in the same life, within range and audible when the answer is requested. Death, respawn, restore, disconnect/reused slots and expiry cannot leave a valid stale target. A late joiner does not inherit earlier taunts. The positional taunt attenuation and subtitle recipients follow the configured radius. Speech remains on native CHAN_VOICE.

Bots using FL_FAKECLIENT, including the tested jk_botti clients, run the same dialogue layer from player think. They occasionally provoke a visible nearby opponent and can answer an audible human or bot. Each heard normal taunt gets one probability roll; a declined reply is not retried via the initiative chance. Replies wait until the source line is finished, then apply a small randomized delay. Damage, effects, death and cooldowns retain priority over social speech. This adds vocal decisions alongside the existing navigation and combat AI; it does not modify their pathfinding or chase targets.

Settings are server cvars. The launchers preserve a local **vf_voice_behavior.cfg** in each mod; editing the file and executing it on the server persists preferences across launches. The source defaults are `data/voice_behavior.cfg`.

| Setting | Default | Meaning / supported range |
| --- | --- | --- |
| `vf_voices` | 1 | All character speech enabled |
| `vf_taunts` | 1 | Human and bot social speech enabled |
| `vf_counter_taunts` | 1 | Contextual reply selection enabled |
| `vf_taunt_radius` | 768 | Hearing range in native game units; 256–1024 |
| `vf_counter_window` | 5 | Reply grace after the source clip; 0–30 seconds |
| `vf_taunt_cooldown` | 6 | Shared taunt/counter cooldown; 1–60 seconds |
| `vf_bot_taunts` | 1 | Bot initiative and counters enabled |
| `vf_bot_taunt_chance` | 0.25 | Initiative chance at each eligible check; 0–1 |
| `vf_bot_taunt_interval` | 12 | Minimum interval between checks, with jitter up to 1.5x; 2–120 seconds |
| `vf_bot_counter_chance` | 0.7 | Probability of answering a heard taunt; 0–1 |
| `vf_bot_counter_delay` | 0.8 | Delay after the heard line ends, jitter 0.7–1.3x; 0.1–5 seconds |

To make bots answer every audible taunt while never initiating:

```
vf_bot_taunts 1
vf_bot_taunt_chance 0
vf_bot_counter_chance 1
```

In the dedicated bot launcher, use `rcon vf_bot_counter_chance 1` from the game console, or edit `runtime/jk-botti-research/engine/valve/vf_voice_behavior.cfg` and run `rcon exec vf_voice_behavior.cfg`. Normal play uses `runtime/vector-engine/vf_visual/vf_voice_behavior.cfg`. Setting `vf_bot_taunts 0` mutes their new social speech while keeping normal injury, reload and death lines.

The native attenuation calculation follows the engine's [sound spatialization code](https://github.com/FWGS/xash3d-fwgs/blob/master/engine/client/sound/s_main.c) and [1000-unit clip-distance constant](https://github.com/FWGS/xash3d-fwgs/blob/master/engine/client/sound.h). The 256-unit lower bound keeps attenuation within the native sound protocol limit. Client volume, focus muting and user hearing cannot be inferred by server logic; hearing eligibility uses geography and the native audible-region check.

## Apply effects and test timing

Open **F3 → Test joueur / voix → Activer le test developpeur**. Select a primary, reaction or tactical state, choose 6, 12 or 30 seconds, then press **Sur moi**. The menu closes and the active-state HUD displays the remaining time alongside the normal character subtitle. Reopen F3 to apply a second primary, choose an actor, or press **Combiner A+B** for an atomic pair. Other players see the applied effect and hear its positional dialogue.

**Retirer mes effets** clears states and pending onset dialogue. **Reinitialiser le scenario / voix** also clears dialogue cooldowns, allowing repeated fresh laboratory scenarios. The action buttons apply actual injury, armor loss, critical damage, burns, death or gib damage through the ordinary damage pipeline. Normal **R** reload and **J** taunt retain their existing hooks; enemy kills trigger the killer's line.

Console equivalents (local play or `sv_cheats 1`):

```
vf_effect_player_test
cmd vf_status_dev 1
cmd vf_status_apply hydro 12
cmd vf_status_apply electro 12
cmd vf_status_pair toxic thermal 6
cmd vf_status_info
vf_status_client
cmd vf_status_clear
cmd vf_status_reset
cmd vf_status_dev 0
```

Activation is per player. Disabling the developer option or revoking server cheats clears laboratory states. Ordinary multiplayer clients cannot enable the test mode, apply effects, reset speech or choose an actor. State durations must be finite and between 0.2 and 30 seconds for developer commands. Rendering is limited to four particle signatures and one halo per visible player; all active local states remain accessible through `vf_status_info`. Temporary states are intentionally omitted from saves.

## Half-Life quality target

The prior audit in `assets/audio/elevenlabs/half-life-audio-reference.json` measured Barney, scientists, G-Man and announcements at mono 11025 Hz, unsigned 8-bit PCM. All 233 deployed operator WAVs use that format. Each original MP3 and clean mono 22050 Hz / 16-bit master remain in the workshop, outside runtime sounds.

The voice export applies 100 Hz high-pass, 4800 Hz low-pass, mild 2:1 compression, limiting and triangular dither before 8-bit quantisation. These filters are our sound design, not a measurement of Valve studio processing. The 40 new weapon FX exports also use mono 11025 Hz / 8-bit, preserving their clean derived masters and using a 35 Hz lower cutoff to retain shot body. No clean master is deployed in either sound bank.

## Listen and audition

Open `Atelier - Voix.cmd` for the six-actor listening page. Its event filter compares the same situation across actors, and every card offers the exact game WAV, clean master and ElevenLabs original.

In local play, or a server with cheats enabled:

```
cmd vf_voice_set rocco
cmd vf_voice_preview taunt
cmd vf_voice_preview respawn
cmd vf_voice_preview arc_chain
cmd vf_voice_info
```

Actor choices are `rocco`, `lucien`, `diego`, `viktor`, `otto`, `nikos`; event names are in `data/voices.json`. `cmd vf_voice_test pain|burn|shock|armor|critical|death|gib` deliberately applies real damage and is reserved for development tests. Actor overrides, forced events and damage probes are rejected on ordinary multiplayer servers.

## Build and validation

```
python vector-fields/voice_workshop.py design
python vector-fields/voice_workshop.py generate
python vector-fields/voice_workshop.py build
powershell -File vector-fields/build_voices.ps1
python vector-fields/tests/voices_test.py --mode assets
python vector-fields/tests/voices_test.py --mode native
python vector-fields/tests/voices_test.py --mode multiplayer
python vector-fields/tests/status_voice_test.py --mode native
python vector-fields/tests/status_voice_multiplayer_test.py
python vector-fields/tests/taunt_engine_test.py
python vector-fields/tests/bot_voice_test.py
python vector-fields/tests/respawn_voice_test.py
```

Only `design` and `generate` contact ElevenLabs or spend credits. Keys use the existing Windows DPAPI store; no API key or network speech dependency is shipped in the game. Completed requests are cached; ambiguous outcomes retain a pending marker. `build_voices.ps1` writes DLLs to `build/voices` to avoid concurrent build-directory collisions. The normal `build.ps1` and `play.py` also include the voice catalog and deployment.

Validation reports are written under `build/*-verification.json`; owner-only respawns are covered by `respawn-native-verification.json`. Native tests run isolated copies of Xash and the mod so their map, configuration and save files do not interfere with other work. Final interpretation and accent quality remain subject to human listening; native tests check event dispatch and delivery, not subjective acting quality.

## Integrated nonverbal death bank

Actual player, bot and GIGN target deaths now select from `assets/audio/operator-deaths`: **102 nonverbal performances, each three seconds or less** (standard + eight elements + eight coupled reactions for each of the six actors). Phase, Null, Ward, Reveal and Overclock map to standard death. Reactions take precedence over primaries, then the most recently applied state wins. The old spoken death files are not precached or emitted. Cries interrupt speech, play once per life and never display subtitles. Private frustrated dialogue remains at respawn. See [DEATH-VOICES.md](DEATH-VOICES.md) for chamber probes and native validation; **Atelier - Cris de mort.cmd** opens the listening page.

## Engine impact

**No engine changes are required.** The mod uses existing sound precaching, positional native sound messages, CHAN_VOICE, cvars and a three-byte dialogue user message and a separate four-byte caption-free death packet. The shared tables live in `game_shared/vf_voice_catalog.h` and `vf_status_catalog.h`; server authority and scheduling live in `dlls/vf_voice.cpp` and `vf_status.cpp`. A bounded 44-byte user message replicates effect snapshots on transitions and on late join. The client validates state packets, renders attached effects and displays subtitles and remaining durations. The packet is capped below 256 clips. Internet latency, physical keyboard input and subjective mix balance are outside the automated local tests.

## Provider references

- https://elevenlabs.io/docs/api-reference/text-to-voice/design
- https://elevenlabs.io/docs/api-reference/text-to-voice/create
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert
