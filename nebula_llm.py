# nebula_llm.py
import time

DEFAULT_FALLBACK = "I felt a little cosmic turbulence… but I’m still here. Try again in a moment."

def nebula_fallback(reason: str | None = None) -> str:
    # keep it short + in-universe, never leak raw errors to user
    return DEFAULT_FALLBACK

def safe_generate_reply(client, messages, model="gpt-4o-mini", timeout_s: float = 30.0) -> tuple[str, str | None]:
    """
    Returns (reply_text, error_code)
    error_code is None on success, else a short string like 'rate_limit', 'auth', 'network', 'unknown'
    """
    try:
        # Responses API call
        resp = client.responses.create(
            model=model,
            input=messages,
        )
        reply_text = (resp.output_text or "").strip()
        if not reply_text:
            return (nebula_fallback("empty"), "empty")
        return (reply_text, None)

    except Exception as e:
        msg = repr(e).lower()
        if "rate limit" in msg or "429" in msg:
            return (nebula_fallback("rate_limit"), "rate_limit")
        if "401" in msg or "unauthorized" in msg or "api key" in msg:
            return (nebula_fallback("auth"), "auth")
        if "timeout" in msg:
            return (nebula_fallback("timeout"), "timeout")
        return (nebula_fallback("unknown"), "unknown")