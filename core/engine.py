# core/engine.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from core.config_loader import settings

def get_llm(temperature=0):
    """
    Get an LLM instance based on the configuration.
    """
    provider = settings.get("model.provider", "google")
    model_name = settings.get("model.name", "gemini-2.0-flash")
    api_key = settings.get("model.api_key")
    base_url = settings.get("model.base_url")

    print(f"--- [Engine] Initializing LLM: {provider}/{model_name} ---")

    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            model_kwargs={"response_mime_type": "application/json"}
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
            base_url=base_url if base_url else None
        )
    elif provider == "deepseek":
        # DeepSeek uses an OpenAI-compatible interface
        effective_base_url = base_url if base_url else "https://api.deepseek.com"
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
            base_url=effective_base_url
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")