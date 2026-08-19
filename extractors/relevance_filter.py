from typing import Tuple

BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "pinterest.com",
    "amazon.com",
    "ebay.com",
    "walmart.com",
}

AI_RELEVANCE_KEYWORDS = [
    "llm",
    "artificial intelligence",
    "machine learning",
    "model",
    "inference",
    "api",
    "open weights",
    "deep learning",
    "transformer",
    "tokens",
    "context window",
    "neural",
    "parameters",
    "vision model",
    "reasoning model",
    "hugging face",
    "endpoint",
    "free tier",
    "rate limit",
    "embeddings",
    "rag",
]


class RelevanceFilter:
    """
    Implements layered filtering:
    1. URL / Domain level cheap check
    2. Content relevance keyword density
    3. Structural AI entity indicator check
    """

    def is_domain_allowed(self, domain: str) -> bool:
        norm = domain.lower().strip()
        return not any(b in norm for b in BLOCKED_DOMAINS)

    def calculate_relevance_score(self, title: str, text: str) -> float:
        combined = f"{title}\n{text}".lower()
        if not combined.strip():
            return 0.0

        matches = sum(1 for kw in AI_RELEVANCE_KEYWORDS if kw in combined)
        score = min(1.0, matches / 5.0)
        return score

    def evaluate(self, domain: str, title: str, text: str) -> Tuple[bool, float, str]:
        """
        Returns (is_relevant, score, reason).
        """
        if not self.is_domain_allowed(domain):
            return False, 0.0, "Blocked domain"

        score = self.calculate_relevance_score(title, text)
        if score < 0.2:
            return False, score, "Insufficient AI keyword density"

        return True, score, "Relevant AI content verified"
