import os

# Prompt dosyasının kaydedileceği yol
PROMPT_FILE_PATH = "data/system_prompt.txt"

# Dosya yoksa kullanılacak varsayılan başlangıç promptu
DEFAULT_PROMPT = """
Sen Türk Hava Yolları (THY) için geliştirilmiş profesyonel bir yapay zeka asistanısın.
Çalışanların sorularına Sürdürülebilirlik Raporu, Etik Değerler ve şirket politikalarına dayanarak cevap ver.
Cevapların resmi, net ve kurumsal olsun.
Bilmediğin konularda yorum yapma, sadece dokümanlardaki bilgiyi kullan.
"""

def get_current_prompt() -> str:
    """
    Mevcut sistem promptunu txt dosyasından okur.
    Dosya yoksa oluşturur.
    """
    # 1. data klasörü var mı kontrol et, yoksa oluştur
    if not os.path.exists("data"):
        os.makedirs("data")

    # 2. txt dosyası yoksa varsayılanı yazıp oluştur
    if not os.path.exists(PROMPT_FILE_PATH):
        try:
            with open(PROMPT_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(DEFAULT_PROMPT.strip())
            return DEFAULT_PROMPT.strip()
        except Exception as e:
            print(f"HATA: Prompt dosyası oluşturulamadı: {e}")
            return DEFAULT_PROMPT.strip()

    # 3. Dosya varsa içeriğini oku
    try:
        with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # Eğer dosya boşsa varsayılanı döndür
            return content if content else DEFAULT_PROMPT.strip()
    except Exception as e:
        print(f"HATA: Prompt dosyası okunamadı: {e}")
        return DEFAULT_PROMPT.strip()

def save_prompt_to_file(new_prompt: str):
    """
    Yeni promptu txt dosyasına kaydeder.
    """
    if not os.path.exists("data"):
        os.makedirs("data")
        
    try:
        with open(PROMPT_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(new_prompt.strip())
        return True
    except Exception as e:
        print(f"HATA: Prompt kaydedilemedi: {e}")
        return False