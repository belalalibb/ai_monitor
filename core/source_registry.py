from typing import List
from data_mining.models.schemas import ProviderInfo

DEFAULT_PROVIDERS: List[ProviderInfo] = [
    ProviderInfo(
        name="OpenAI",
        domain="openai.com",
        description="Creator of GPT-4, GPT-4o, o1, o3-mini and ChatGPT platform.",
        official_urls=[
            "https://openai.com/news",
            "https://platform.openai.com/docs/models",
            "https://openai.com/index",
        ],
        categories=["llm", "multimodal", "reasoning", "api"],
    ),
    ProviderInfo(
        name="Anthropic",
        domain="anthropic.com",
        description="Creator of Claude 3.5 Sonnet, Claude 3.5 Haiku, and Claude 3.7 series.",
        official_urls=[
            "https://www.anthropic.com/news",
            "https://docs.anthropic.com/en/docs/about-claude/models",
        ],
        categories=["llm", "vision", "reasoning", "api"],
    ),
    ProviderInfo(
        name="Google",
        domain="deepmind.google",
        description="Google DeepMind, Gemini 2.0 series, Gemma open weights models.",
        official_urls=[
            "https://deepmind.google/discover/blog",
            "https://ai.google.dev/gemini-api/docs/models/gemini",
        ],
        categories=["llm", "multimodal", "open_weights", "cloud_ai"],
    ),
    ProviderInfo(
        name="Meta AI",
        domain="ai.meta.com",
        description="Meta AI Research, Llama 3 series open weights models.",
        official_urls=[
            "https://ai.meta.com/blog",
            "https://llama.meta.com",
        ],
        categories=["open_weights", "llm", "multimodal", "research"],
    ),
    ProviderInfo(
        name="DeepSeek",
        domain="deepseek.com",
        description="DeepSeek-R1 reasoning models, DeepSeek-V3 open weights models.",
        official_urls=[
            "https://www.deepseek.com",
            "https://api-docs.deepseek.com",
        ],
        categories=["open_weights", "reasoning", "coding", "api", "free_tier"],
    ),
    ProviderInfo(
        name="Mistral AI",
        domain="mistral.ai",
        description="Mistral Large, Pixtral, Codestral, and open-weight models.",
        official_urls=[
            "https://mistral.ai/news",
            "https://docs.mistral.ai/getting-started/models",
        ],
        categories=["llm", "coding", "open_weights", "api"],
    ),
    ProviderInfo(
        name="xAI",
        domain="x.ai",
        description="Grok 2, Grok 3 series models and API platform.",
        official_urls=[
            "https://x.ai/blog",
            "https://docs.x.ai",
        ],
        categories=["llm", "vision", "reasoning", "api"],
    ),
    ProviderInfo(
        name="Microsoft",
        domain="azure.microsoft.com",
        description="Azure AI Studio, Phi-3 / Phi-4 small language models.",
        official_urls=[
            "https://azure.microsoft.com/en-us/blog/topics/artificial-intelligence",
            "https://learn.microsoft.com/en-us/azure/ai-services",
        ],
        categories=["cloud_ai", "slm", "enterprise"],
    ),
    ProviderInfo(
        name="NVIDIA",
        domain="nvidia.com",
        description="NVIDIA NIM, NeMo, Megatron, and AI inference microservices.",
        official_urls=[
            "https://blogs.nvidia.com/blog/category/deep-learning",
            "https://build.nvidia.com",
        ],
        categories=["inference", "nim", "open_weights", "free_tier"],
    ),
    ProviderInfo(
        name="Alibaba",
        domain="qwenlm.github.io",
        description="Alibaba Qwen 2.5 series, Qwen 2.5-Coder, QwQ reasoning models.",
        official_urls=[
            "https://qwenlm.github.io/blog",
            "https://github.com/QwenLM",
        ],
        categories=["open_weights", "coding", "reasoning", "multimodal"],
    ),
    ProviderInfo(
        name="Hugging Face",
        domain="huggingface.co",
        description="Open source model hub, Hugging Face Inference API and Spaces.",
        official_urls=[
            "https://huggingface.co/blog",
            "https://huggingface.co/models",
        ],
        categories=["open_weights", "hub", "free_tier", "datasets"],
    ),
    ProviderInfo(
        name="Groq",
        domain="groq.com",
        description="LPU Inference Engine providing ultra-fast inference for open models.",
        official_urls=[
            "https://groq.com/blog",
            "https://console.groq.com/docs/models",
        ],
        categories=["inference", "speed", "api", "free_tier"],
    ),
    ProviderInfo(
        name="Cohere",
        domain="cohere.com",
        description="Command R, Command R+, Embed, and RAG enterprise models.",
        official_urls=[
            "https://cohere.com/blog",
            "https://docs.cohere.com/docs/models",
        ],
        categories=["llm", "rag", "embeddings", "api"],
    ),
    ProviderInfo(
        name="Stability AI",
        domain="stability.ai",
        description="Stable Diffusion 3, Stable Audio, Stable Video Diffusion.",
        official_urls=[
            "https://stability.ai/news",
        ],
        categories=["image_generation", "video_generation", "audio", "open_weights"],
    ),
    ProviderInfo(
        name="OpenRouter",
        domain="openrouter.ai",
        description="Unified API gateway offering diverse commercial and free AI models.",
        official_urls=[
            "https://openrouter.ai/models",
            "https://openrouter.ai/docs",
        ],
        categories=["aggregator", "free_tier", "api"],
    ),
]


def get_default_providers() -> List[ProviderInfo]:
    return list(DEFAULT_PROVIDERS)


def init_default_providers(repo=None) -> None:
    from data_mining.db.repository import Repository
    r = repo or Repository()
    for p in DEFAULT_PROVIDERS:
        r.upsert_provider(p)
