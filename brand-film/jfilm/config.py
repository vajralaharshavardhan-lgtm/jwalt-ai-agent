"""Loads film.yaml and exposes typed settings + project paths.

Everything that controls timing, copy, colour, typography and output
formats lives in film.yaml; code imports it from here only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent          # brand-film/
OUT = ROOT / "output"
CACHE = OUT / "cache"
STILLS = CACHE / "stills"          # Cycles projector stills (EXR)
GBUF = CACHE / "gbuffer"           # scratch for per-frame visibility buffers
FRAMES = OUT / "frames"            # final graded frames per format
AUDIO_OUT = OUT / "audio"
MASTERS = OUT / "masters"
LINEWORK = CACHE / "linework.npz"


def hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass(frozen=True)
class Format:
    key: str
    width: int
    height: int
    fov_scale: float
    label: str = ""

    @property
    def aspect(self) -> float:
        return self.width / self.height


@dataclass(frozen=True)
class ShotEntry:
    id: str
    start: float
    end: float
    title: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Config:
    fps: int
    duration: float
    formats: dict[str, Format]
    brand: dict
    palette: dict[str, tuple[float, float, float]]
    typography: dict
    shots: list[ShotEntry]
    render: dict
    audio: dict
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def n_frames(self) -> int:
        return int(round(self.duration * self.fps))

    def shot(self, shot_id: str) -> ShotEntry:
        for s in self.shots:
            if s.id == shot_id:
                return s
        raise KeyError(shot_id)

    def shot_at(self, t: float) -> ShotEntry:
        for s in self.shots:
            if s.start <= t < s.end:
                return s
        return self.shots[-1]

    def font_path(self, role: str) -> Path:
        return ROOT / self.typography[role]["font"]


@lru_cache(maxsize=1)
def load(path: str | None = None) -> Config:
    p = Path(path) if path else ROOT / "film.yaml"
    raw = yaml.safe_load(p.read_text())
    formats = {k: Format(key=k, **v) for k, v in raw["formats"].items()}
    shots = [ShotEntry(**s) for s in raw["shots"]]
    for a, b in zip(shots, shots[1:]):
        if abs(a.end - b.start) > 1e-6:
            raise ValueError(f"shot gap/overlap between {a.id} and {b.id}")
    if abs(shots[-1].end - raw["duration"]) > 1e-6:
        raise ValueError("last shot must end at `duration`")
    return Config(
        fps=int(raw["fps"]),
        duration=float(raw["duration"]),
        formats=formats,
        brand=raw["brand"],
        palette={k: hex_to_rgb(v) for k, v in raw["palette"].items()},
        typography=raw["typography"],
        shots=shots,
        render=raw["render"],
        audio=raw["audio"],
        raw=raw,
    )
