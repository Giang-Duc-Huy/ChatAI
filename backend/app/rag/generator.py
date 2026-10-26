from ..config import ANTHROPIC_API_KEY, LLM_MODEL, PRICE_IN, PRICE_OUT
from .prompts import SYSTEM_PROMPT, REFUSAL, build_context

_client = None

def generate(question: str, chunks: list, sufficient: bool):
    """Trả về (answer, usage_cost_dict). Không đủ căn cứ -> từ chối, không gọi LLM (tiết kiệm chi phí)."""
    if not sufficient:
        return REFUSAL, {"in": 0, "out": 0, "usd": 0.0}
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=30.0)
    msg = _client.messages.create(
        model=LLM_MODEL, max_tokens=600, temperature=0, system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"NGỮ CẢNH:\n{build_context(chunks)}\n\nCÂU HỎI: {question}"}])
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    i, o = msg.usage.input_tokens, msg.usage.output_tokens
    return text, {"in": i, "out": o, "usd": round((i * PRICE_IN + o * PRICE_OUT) / 1e6, 6)}
