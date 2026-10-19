# Barrad Archive Field Recordings

Three original, fictional, non-voice attachments, synthesized by `tools/Build-BarradArchiveAudio.cjs`. No recordings, voices or music from EaW or other works are embedded. These are authored archive props, not canonical source material or authentic field recordings.

| Case | Sound | Length |
| --- | --- | ---: |
| Shaft echo | Ventilation, test knocks and delayed reflections | 9 s |
| Lower presence | Low listening-post noise, distant impacts, two interruptions | 9 s |
| Reactor | Uneven mechanical hum, casing ticks and resonances | 9 s |

Files: `mod/HoISubmod/sound/HSM_BAR/archive/{echo,entity,reactor}.wav`, mono 44.1 kHz PCM16. Seeded noise, resonant impulses, DC blocking and fade envelopes make regeneration deterministic. No voice generator or external audio dependency is required.

The play icon appears only on each case's released **Field File** page. It requires the same owner, Service and investigation/study gates as the documents. Historical recordings survive loss of current access; playback never grants evidence or changes rewards. Copy selection does not change the recording.

`sound/HSM_BAR_archive.asset` registers native UI-category one-shots; each button uses `clicksound`. Volume is 0.65 and the native `max_audible = 1` / `max_audible_behaviour = fail` prevents overlapping repeats of the same clip. There is no pause/stop transport: a started clip finishes after nine seconds, including after changing pages. Switching cases can play different clips concurrently.

Native references: installed HOI4 `sound/gui/gtd/gtd_gui.asset` (UI-category additions), `sound/gui/gui_sound_effects.asset` (`ui_doctrine_tab_air` one-shot contract), and EaW `sound/eaw_vo_Chrysalis_sound.asset` / `sound/eaw_vo_Chrysalis_soundeffect.asset` (sound-file registration). No engine files are overridden.

```powershell
node tools/Build-BarradArchiveAudio.cjs
node tools/Test-BarradArchiveAudio.cjs
```

Validation checks actual PCM headers/data, duration, nonblank samples, peak/RMS/DC, boundary fades, deterministic generation, localization and native hookups, plus positive and negative archive access fixtures. It does not certify subjective sound quality or native playback. In-game listening, UI volume and rapid page changes still require a full HOI4 restart and playtest.
