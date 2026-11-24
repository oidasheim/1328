"""Human-readable intention generation from sections and energy."""
from __future__ import annotations

from .models import Intent, SongAST


def generate_intents(song: SongAST) -> list[Intent]:
    intents = []
    for section in song.sections:
        tags = ("fast",) if section.energy >= 0.65 else ("atmosphere",)
        camera = "push" if section.energy >= 0.65 else "steady"
        color = "warm" if section.energy >= 0.65 else "natural"
        intents.append(Intent(section.name, section.start, section.end, section.energy, tags, camera, color))
    return intents
