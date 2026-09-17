from langchain.chat_models import init_chat_model

from .settings import settings


def chat_model(temperature: float = 0.0):
    return init_chat_model(
        settings.llm_model, model_provider=settings.llm_provider, temperature=temperature
    )
