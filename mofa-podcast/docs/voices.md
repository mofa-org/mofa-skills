# Voices

## Built-in presets

The following preset voices ship with the deployment and are always available:

`vivian` (default), `serena`, `ryan`, `aiden`, `eric`, `dylan`, `uncle_fu`,
`ono_anna`, `sohee`.

## Cloned voices

Use `mofa-fm.fm_voice_save` to register a cloned voice first, then reference it
in scripts by name with the `clone:` prefix (e.g. `clone:sarah`).

## Listing voices

Call `podcast_voices` only when the user explicitly asks to browse or choose
voices. Both preset and saved clones are returned.

## Anti-pattern: voice listing is not a precheck

Do NOT call `mofa-fm.fm_voice_list` (or any other voice-listing tool) as a
precheck before generating a podcast. If the user names speaker voices, use
those names directly in the script and let `podcast_generate` / TTS return a
recoverable unknown-voice error if a voice is unavailable. Voice-listing tools
are intended for explicit user-driven browsing, not implicit validation —
calling them speculatively wastes tokens and slows the agent loop.
