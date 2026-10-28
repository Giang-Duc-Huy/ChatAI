import random
import time

from ..config import GOOGLE_API_KEY, LLM_MODEL, PRICE_IN, PRICE_OUT
from .prompts import SYSTEM_PROMPT, REFUSAL, build_context

_client = None
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRY_DELAYS_SECONDS = (0.5, 1.5)

def _generate_content_with_retry(**kwargs):
    for attempt in range(len(_RETRY_DELAYS_SECONDS) + 1):
        try:
            return _client.models.generate_content(**kwargs)
        except Exception as error:
            if (
                getattr(error, "code", None) not in _RETRYABLE_STATUS_CODES
                or attempt == len(_RETRY_DELAYS_SECONDS)
            ):
                raise
            time.sleep(_RETRY_DELAYS_SECONDS[attempt] + random.uniform(0, 0.25))

def _needs_completion(response, text: str) -> bool:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        reason = getattr(candidate, "finish_reason", None)
        if str(reason).endswith("MAX_TOKENS"):
            return True

    return not text.rstrip().endswith((".", "!", "?", "…", "]"))

def generate(question: str, chunks: list, sufficient: bool):
    """Trả về (answer, usage_cost_dict). Không đủ căn cứ -> từ chối, không gọi LLM (tiết kiệm chi phí)."""
    if not sufficient:
        return REFUSAL, {"in": 0, "out": 0, "usd": 0.0}
    from google.genai import types
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("Chưa cấu hình GOOGLE_API_KEY trong file .env.")
        from google import genai
        _client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=types.HttpOptions(timeout=30_000),
        )

    contents = f"NGỮ CẢNH:\n{build_context(chunks)}\n\nCÂU HỎI: {question}"
    generation_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=1024,
        temperature=0,
    )
    response = _generate_content_with_retry(
        model=LLM_MODEL,
        contents=contents,
        config=generation_config,
    )
    responses = [response]
    text = (response.text or "").strip()
    if text and _needs_completion(response, text):
        response = _generate_content_with_retry(
            model=LLM_MODEL,
            contents=(
                f"{contents}\n\nCÂU TRẢ LỜI TRƯỚC BỊ NGẮT GIỮA CHỪNG:\n{text}\n\n"
                "Hãy viết lại toàn bộ câu trả lời thành câu hoàn chỉnh, kết thúc tự nhiên. "
                "Chỉ dùng thông tin trong ngữ cảnh."
            ),
            config=generation_config,
        )
        responses.append(response)
        text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini không trả về nội dung văn bản.")
    if _needs_completion(response, text):
        raise RuntimeError("Gemini vẫn trả về câu trả lời chưa hoàn chỉnh sau khi thử tạo lại.")
    usage_records = [result.usage_metadata for result in responses]
    if any(
        usage is None or usage.prompt_token_count is None or usage.candidates_token_count is None
        for usage in usage_records
    ):
        raise RuntimeError("Gemini không trả về đầy đủ thông tin token usage.")
    input_tokens = sum(usage.prompt_token_count for usage in usage_records)
    output_tokens = sum(usage.candidates_token_count for usage in usage_records)
    usd = None
    if PRICE_IN is not None and PRICE_OUT is not None:
        usd = round((input_tokens * PRICE_IN + output_tokens * PRICE_OUT) / 1e6, 6)
    return text, {"in": input_tokens, "out": output_tokens, "usd": usd}
