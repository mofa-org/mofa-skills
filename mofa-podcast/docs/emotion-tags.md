# Emotion Tags

Each dialogue line must declare an emotion. The tag is mapped to a TTS style
prompt before synthesis.

| Tag | Style |
|-----|-------|
| `calm` | natural, composed tone |
| `excited` | energetic, enthusiastic |
| `serious` | formal, weighty |
| `warm` | friendly, inviting |
| `angry` | intense, forceful |
| `sad` | somber, reflective |
| `cheerful` | upbeat, positive |
| `dramatic` | theatrical, intense |
| `curious` | inquisitive, wondering |
| `thoughtful` | contemplative, measured |

If you need a tone not on this list, pick the closest match — unknown emotion
strings fall back to a neutral synthesis prompt rather than failing the run.
