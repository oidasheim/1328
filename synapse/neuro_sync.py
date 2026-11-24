from dataclasses import dataclass


@dataclass(frozen=True)
class NeuroSyncCue:
    time: float
    event: str
    visual: str
    intensity: float = 1.0


def build_cues(beats: list[float], drop_times: list[float] | None = None) -> list[NeuroSyncCue]:
    """Create safe, beat-aligned audiovisual cues.

    This is an editing aid, not a claim that music can force dopamine release or
    control a listener. Strobe-like effects should be reviewed for photosensitivity.
    """
    drops = set(round(value, 3) for value in (drop_times or []))
    cues: list[NeuroSyncCue] = []
    for beat in beats:
        key = round(float(beat), 3)
        if key in drops:
            cues.append(NeuroSyncCue(float(beat), "drop", "wobble_zoom", 1.0))
        else:
            cues.append(NeuroSyncCue(float(beat), "beat", "cut", 0.6))
    return cues
