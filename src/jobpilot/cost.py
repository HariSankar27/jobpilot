# ponytail: fill in real per-model rates from the provider's pricing page before
# trusting these numbers; unknown models cost 0 rather than raising.
PRICE_PER_MTOK: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
}


def cost_usd(usage: dict) -> float:
    total = 0.0
    for model, u in usage.items():
        price = PRICE_PER_MTOK.get(model, {"input": 0.0, "output": 0.0})
        total += (u["input_tokens"] * price["input"] + u["output_tokens"] * price["output"]) / 1e6
    return total
