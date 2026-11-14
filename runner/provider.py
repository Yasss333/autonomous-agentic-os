"""LiteLLM provider calls for OpenRouter.

Rules enforced here:
- api_key is passed explicitly per call; never a global.
- Only allowlisted free models may be used (paid fallback disabled).
- Per-request timeout and token caps; usage is measured and reported.
"""

import time
from dataclasses import dataclass, field

import litellm

from . import config

litellm.suppress_debug_info = True


class ProviderError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass
class Usage:
    model_id: str
    payer: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    cost_known: bool = False


@dataclass
class Completion:
    text: str
    usage: Usage
    raw: dict = field(default_factory=dict)


def _model_id(requested: str | None) -> str:
    model = requested or next(iter(sorted(config.FREE_MODEL_ALLOWLIST)))
    if model not in config.FREE_MODEL_ALLOWLIST:
        raise ProviderError(
            "model_not_allowed",
            f"Model '{model}' is not in the free demo allowlist",
        )
    return model


def complete(
    *,
    api_key: str,
    payer: str,
    messages: list[dict],
    model_id: str | None = None,
    max_tokens: int = config.MAX_OUTPUT_TOKENS,
    timeout: int = config.MODEL_TIMEOUT_SECONDS,
) -> Completion:
    model = _model_id(model_id)
    if not api_key:
        raise ProviderError("needs_key", "No provider key available for this run")

    started = time.monotonic()
    try:
        resp = litellm.completion(
            model=f"openrouter/{model}",
            api_key=api_key,
            messages=messages,
            max_tokens=max_tokens,
            timeout=timeout,
            num_retries=0,
        )
    except Exception as exc:  # litellm raises many types
        text = str(exc).lower()
        if "authentication" in text or "invalid" in text and "key" in text:
            raise ProviderError("invalid_key", "Provider rejected the API key", retryable=False) from exc
        if "rate" in text or "429" in text or "timeout" in text or "timed out" in text:
            raise ProviderError("provider_busy", "Free provider is busy; retry later", retryable=True) from exc
        raise ProviderError("provider_error", f"Provider call failed: {type(exc).__name__}", retryable=True) from exc

    elapsed = time.monotonic() - started
    usage_obj = getattr(resp, "usage", None)
    input_tokens = getattr(usage_obj, "prompt_tokens", None) if usage_obj else None
    output_tokens = getattr(usage_obj, "completion_tokens", None) if usage_obj else None

    cost = None
    cost_known = False
    try:
        cost = litellm.completion_cost(completion_response=resp)
        cost_known = cost is not None
    except Exception:
        pass

    text_out = ""
    try:
        text_out = resp.choices[0].message.content or ""
    except Exception:
        pass

    return Completion(
        text=text_out,
        usage=Usage(
            model_id=f"openrouter/{model}",
            payer=payer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(cost) if cost_known else None,
            cost_known=cost_known,
        ),
        raw={"elapsed_seconds": round(elapsed, 2)},
    )
