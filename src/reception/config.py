"""Application configuration loaded from YAML."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """Settings for the language-model provider."""

    provider: Literal["ollama", "fake"] = "ollama"
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    timeout_s: float = 30.0


class VisionConfig(BaseModel):
    """Visitor detection (face boxes are normalised to the frame, 0-1)."""

    window_s: float = 1.5
    require_approach: bool = False
    dwell_s: float = 1.0
    center_tolerance: float = 0.25
    max_drift: float = 0.2
    growth_ratio: float = 1.15
    near_height: float = 0.18
    min_face: float = 0.08
    cooldown_s: float = 8.0
    max_age_s: float = 1.0
    iou_match: float = 0.2
    haar_scale_factor: float = 1.1
    haar_min_neighbors: int = 5
    frame_interval_ms: int = 200


class SpeechConfig(BaseModel):
    """Speech-to-text and the browser's voice activity detection."""

    model: str = "base.en"
    compute_type: str = "int8"
    beam_size: int = 1
    vad_rms_threshold: float = 0.015
    voice_threshold: float = 0.5
    min_voice_s: float = 0.3
    no_speech_threshold: float = 0.6
    min_avg_logprob: float = -1.0
    silence_ms: int = 900
    min_speech_ms: int = 300
    max_utterance_s: float = 10.0
    vocabulary: str = (
        "CHRIST University, Central Block, room 806, xerox, CCD, Gourmet, MCA, BCA, MBA, "
        "MSc AI and ML, library, admissions, Health Centre, Sky View Studio"
    )


class KioskConfig(BaseModel):
    """Session lifecycle."""

    port: int = 8765
    absent_timeout_s: float = 10.0
    idle_timeout_s: float = 20.0
    banner_s: float = 6.0


class AnalyticsConfig(BaseModel):
    """Interaction logging and the admin dashboard."""

    db_path: Path = Path("data/analytics.db")
    admin_pin: str = "2027"


class AppConfig(BaseModel):
    """All tunable settings. Nothing tunable is hard-coded elsewhere."""

    vision: VisionConfig = VisionConfig()
    speech: SpeechConfig = SpeechConfig()
    kiosk: KioskConfig = KioskConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()

    timezone: str = "Asia/Kolkata"
    knowledge_dir: Path = Path("knowledge")
    kiosk_node: str = "G:kiosk"
    route_preference: Literal["lift", "stairs"] = "lift"
    lift_cost_per_floor: float = 6.0
    stairs_cost_per_floor: float = 12.0
    intent_threshold: float = 0.35
    fuzzy_threshold: int = 80
    retrieval_threshold: float = 0.65
    top_k: int = 5
    max_speech_words: int = 40
    max_input_chars: int = 500
    llm: LLMConfig = LLMConfig()
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    intent_model_path: Path = Path("models/intent.joblib")
    seed: int = 42


def load_config(path: Path) -> AppConfig:
    """Load an AppConfig from a YAML file.

    Args:
        path: YAML file path.

    Returns:
        The validated configuration.
    """
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(data)
