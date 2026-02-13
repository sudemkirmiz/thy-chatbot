from langchain_ollama import ChatOllama, OllamaEmbeddings
from core.config import settings

def get_llm():
    """
    Sohbet Modelini (Beyin) başlatır.
    """
    llm = ChatOllama(
        model=settings.LLM_MODEL,    
        temperature=settings.TEMPERATURE,
        keep_alive="1h"  
    )
    return llm

def get_embeddings():
    """
    Embedding Modelini başlatır.
    """
    embeddings = OllamaEmbeddings(
        model=settings.EMBED_MODEL
    )
    return embeddings