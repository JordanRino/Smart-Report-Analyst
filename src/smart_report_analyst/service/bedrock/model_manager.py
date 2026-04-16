"""BedrockModel factory for Strands — process-wide singleton.

``BedrockModel`` wraps a boto3 Bedrock Runtime client. Building a new instance per
Strands ``Agent`` (and per turn) repeated client construction and TCP/TLS setup.
This module returns one shared model per process for identical configuration.

The cached instance is treated as read-only after construction. If settings that
affect the client change at runtime (unusual; tests may do this), the cache key
mismatch triggers construction of a new model.
"""

from __future__ import annotations

import threading
from typing import Any

from botocore.config import Config as BotocoreConfig
from strands.models import BedrockModel

from smart_report_analyst.config.settings import Settings, get_settings

_lock = threading.Lock()
_cached_model: BedrockModel | None = None
_cache_key: tuple[Any, ...] | None = None


def _bedrock_singleton_key(settings: Settings) -> tuple[Any, ...]:
    """Hashable config identity; must stay in sync with ``BotocoreConfig`` below."""
    return (
        settings.BEDROCK_MODEL_ID or "",
        settings.AWS_REGION,
        3,  # max_attempts
        "standard",  # retry mode
        10,  # connect_timeout
        120,  # read_timeout
        # When guardrails are passed into ``BedrockModel()``, extend this tuple.
    )


def get_process_bedrock_model() -> BedrockModel:
    """Return the shared ``BedrockModel`` for this process (thread-safe)."""
    global _cached_model, _cache_key

    settings = get_settings()
    model_id = settings.BEDROCK_MODEL_ID
    if not model_id:
        raise ValueError("BEDROCK_MODEL_ID must be set when AGENT_BACKEND=strands.")

    key = _bedrock_singleton_key(settings)
    with _lock:
        if _cached_model is not None and _cache_key == key:
            return _cached_model

        boto_config = BotocoreConfig(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=120,
        )
        # Apply the guardrails once the we have access to perform: bedrock:ApplyGuardrail perms
        # guardrail_kwargs = bedrock_model_guardrail_kwargs()
        _cached_model = BedrockModel(
            model_id=model_id,
            region_name=settings.AWS_REGION,
            boto_client_config=boto_config,
            # **guardrail_kwargs,
        )
        _cache_key = key
        return _cached_model


def build_bedrock_model() -> BedrockModel:
    """Backward-compatible alias: same shared instance as :func:`get_process_bedrock_model`."""
    return get_process_bedrock_model()


def clear_process_bedrock_model_cache() -> None:
    """Drop the cached model (for tests or dynamic config reload). Not used in production paths."""
    global _cached_model, _cache_key
    with _lock:
        _cached_model = None
        _cache_key = None
