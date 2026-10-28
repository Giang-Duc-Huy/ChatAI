from ..config import GOOGLE_API_KEY, LLM_MODEL, PRICE_IN, PRICE_OUT
from .prompts import SYSTEM_PROMPT, REFUSAL, build_context

_client = None

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

    response = _client.models.generate_content(
        model=LLM_MODEL,
        contents=f"NGỮ CẢNH:\n{build_context(chunks)}\n\nCÂU HỎI: {question}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=600,
            temperature=0,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini không trả về nội dung văn bản.")
    usage = response.usage_metadata
    if usage is None or usage.prompt_token_count is None or usage.candidates_token_count is None:
        raise RuntimeError("Gemini không trả về đầy đủ thông tin token usage.")
    input_tokens = usage.prompt_token_count
    output_tokens = usage.candidates_token_count
    usd = None
    if PRICE_IN is not None and PRICE_OUT is not None:
        usd = round((input_tokens * PRICE_IN + output_tokens * PRICE_OUT) / 1e6, 6)
    return text, {"in": input_tokens, "out": output_tokens, "usd": usd}
