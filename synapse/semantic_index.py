"""OpenCLIP-backed DuckDB clip index and semantic similarity search."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import math

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
EMBEDDING_DIM = 512


def validate_embedding(vector: Sequence[float], dimension: int = EMBEDDING_DIM) -> list[float]:
    if len(vector) != dimension:
        raise ValueError(f"Expected embedding dimension {dimension}, got {len(vector)}")
    values = [float(value) for value in vector]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Embedding contains non-finite values")
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 0:
        raise ValueError("Embedding norm must be positive")
    return [value / norm for value in values]


def load_openclip(device: str | None = None):
    """Load OpenCLIP lazily so core SYNAPSE does not require ML dependencies."""
    try:
        import open_clip
        import torch
    except ImportError as exc:
        raise RuntimeError("Install semantic extras: pip install '.[semantic]'") from exc

    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED
    )
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(selected_device).eval()
    return model, preprocess, tokenizer, torch, selected_device


def encode_text(text: str, model_bundle, dimension: int = EMBEDDING_DIM) -> list[float]:
    if not text.strip():
        raise ValueError("Text prompt cannot be empty")
    model, _, tokenizer, torch, device = model_bundle
    tokens = tokenizer([text]).to(device)
    with torch.inference_mode():
        features = model.encode_text(tokens)
        features = features / features.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    return validate_embedding(features[0].detach().cpu().float().tolist(), dimension)


def encode_image(image, model_bundle, dimension: int = EMBEDDING_DIM) -> list[float]:
    model, preprocess, _, torch, device = model_bundle
    tensor = preprocess(image).unsqueeze(0).to(device)
    with torch.inference_mode():
        features = model.encode_image(tensor)
        features = features / features.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    return validate_embedding(features[0].detach().cpu().float().tolist(), dimension)


@dataclass(frozen=True)
class ClipMatch:
    path: str
    duration: float
    score: float


class DuckDBSemanticIndex:
    """Persistent DuckDB index; existing databases are never deleted."""

    def __init__(self, path: str | Path, dimension: int = EMBEDDING_DIM):
        try:
            import duckdb
        except ImportError as exc:
            raise RuntimeError("Install semantic extras: pip install '.[semantic]'") from exc
        if dimension != EMBEDDING_DIM:
            raise ValueError(f"This OpenCLIP profile expects {EMBEDDING_DIM} dimensions")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(self.path))
        self.connection.execute(f"""
            CREATE TABLE IF NOT EXISTS clips (
                path VARCHAR PRIMARY KEY,
                duration DOUBLE NOT NULL,
                embedding FLOAT[{dimension}] NOT NULL,
                model VARCHAR NOT NULL DEFAULT '{MODEL_NAME}:{PRETRAINED}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def upsert(self, path: str | Path, duration: float, embedding: Sequence[float]) -> None:
        if not math.isfinite(float(duration)) or duration <= 0:
            raise ValueError("Clip duration must be a positive finite number")
        vector = validate_embedding(embedding)
        self.connection.execute(
            "INSERT OR REPLACE INTO clips(path,duration,embedding,model,updated_at) "
            "VALUES (?, ?, ?::FLOAT[512], ?, CURRENT_TIMESTAMP)",
            [str(Path(path).resolve()), float(duration), vector, f"{MODEL_NAME}:{PRETRAINED}"],
        )

    def search(self, embedding: Sequence[float], limit: int = 8,
               excluded_paths: Iterable[str] = ()) -> list[ClipMatch]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        vector = validate_embedding(embedding)
        excluded = [str(Path(item).resolve()) for item in excluded_paths]
        if excluded:
            rows = self.connection.execute("""
                SELECT path, duration,
                       array_cosine_similarity(embedding, ?::FLOAT[512]) AS score
                FROM clips
                WHERE path NOT IN (SELECT UNNEST(?))
                ORDER BY score DESC, path ASC LIMIT ?
            """, [vector, excluded, limit]).fetchall()
        else:
            rows = self.connection.execute("""
                SELECT path, duration,
                       array_cosine_similarity(embedding, ?::FLOAT[512]) AS score
                FROM clips
                ORDER BY score DESC, path ASC LIMIT ?
            """, [vector, limit]).fetchall()
        return [ClipMatch(str(path), float(duration), float(score)) for path, duration, score in rows]

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM clips").fetchone()[0])

    def close(self) -> None:
        self.connection.close()
