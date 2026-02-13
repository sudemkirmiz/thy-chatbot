import os
from core.config import settings

# Model adının saklanacağı dosya
MODEL_FILE_PATH = "data/current_model.txt"

def get_current_model_name() -> str:
    """
    Kayıtlı modeli okur. Dosya yoksa .env içindeki varsayılanı döner.
    """
    # Klasör kontrolü
    if not os.path.exists("data"):
        os.makedirs("data")

    # Dosya yoksa varsayılanı oluştur
    if not os.path.exists(MODEL_FILE_PATH):
        try:
            with open(MODEL_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(settings.LLM_MODEL)
            return settings.LLM_MODEL
        except:
            return settings.LLM_MODEL

    # Dosya varsa oku
    try:
        with open(MODEL_FILE_PATH, "r", encoding="utf-8") as f:
            model = f.read().strip()
            return model if model else settings.LLM_MODEL
    except:
        return settings.LLM_MODEL

def save_model_name(new_model: str):
    """Yeni modeli dosyaya kaydeder."""
    if not os.path.exists("data"):
        os.makedirs("data")
        
    try:
        with open(MODEL_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(new_model.strip())
        return True
    except Exception as e:
        print(f"Model kaydedilemedi: {e}")
        return False