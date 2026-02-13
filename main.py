import os
import shutil
import uvicorn
import json
import urllib.request
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from services.rag_service import rag_service
from services.ingestion import run_ingestion
from core.config import settings

from services.model_manager import get_current_model_name

app = FastAPI(title=settings.PROJECT_NAME)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Modeller ---
class QueryRequest(BaseModel):
    text: str

class AdminPromptRequest(BaseModel):
    password: str
    new_prompt: str

class FileActionRequest(BaseModel):
    password: str
    filename: str

class ModelUpdateRequest(BaseModel):
    password: str
    model_name: str

# --- Endpointler ---

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat(request: QueryRequest):
    # Sistem hazır değilse hata dön
    if not rag_service.rag_chain:
        return {"answer": "⚠️ Sistem şu an güncelleniyor, lütfen bekleyin.", "sources": []}

    # Akış (Streaming) Fonksiyonu
    def generate_response():
        try:
            docs = rag_service.retriever.invoke(request.text)
            sources = list(set([d.metadata.get("source", "Bilinmeyen") for d in docs]))
            
            yield json.dumps({"type": "sources", "data": sources}) + "\n"

            for chunk in rag_service.rag_chain.stream(request.text):
                yield json.dumps({"type": "token", "data": chunk}) + "\n"

            yield json.dumps({"type": "end", "data": ""}) + "\n"
        
        except Exception as e:
            yield json.dumps({"type": "error", "data": str(e)}) + "\n"

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")

@app.post("/admin/update-prompt")
def update_prompt(request: AdminPromptRequest):
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")
    rag_service.update_system_prompt(request.new_prompt)
    return {"message": "Prompt güncellendi"}

@app.post("/admin/list-files")
def list_files(request: FileActionRequest):
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")
    
    if not os.path.exists(settings.PDF_SOURCE_DIR):
        return {"files": []}
    
    files = [f for f in os.listdir(settings.PDF_SOURCE_DIR) if f.lower().endswith(".pdf")]
    return {"files": files}

@app.post("/admin/delete-file")
def delete_file(request: FileActionRequest):
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")

    file_path = os.path.join(settings.PDF_SOURCE_DIR, request.filename)
    if os.path.exists(file_path):
        rag_service.release_resources()
        try:
            os.remove(file_path)
        except PermissionError:
            rag_service.reload_knowledge()
            raise HTTPException(status_code=500, detail="Dosya kullanımda.")
        
        run_ingestion()
        rag_service.reload_knowledge()
        return {"success": True, "message": f"{request.filename} silindi."}
    else:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

@app.post("/admin/upload-doc")
async def upload_document(file: UploadFile = File(...), password: str = Form(...)):
    if password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF.")

    os.makedirs(settings.PDF_SOURCE_DIR, exist_ok=True)
    save_path = os.path.join(settings.PDF_SOURCE_DIR, file.filename)
    
    rag_service.release_resources()
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        rag_service.reload_knowledge()
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

    msg = run_ingestion()
    rag_service.reload_knowledge()
    return {"success": True, "message": f"Yüklendi. {msg}"}

# --- YENİ: MODEL YÖNETİMİ ENDPOINTLERİ ---

# --- main.py İÇİNDEKİ MODEL ÇEKME FONKSİYONU ---

@app.post("/admin/get-models")
def get_available_models(request: AdminPromptRequest):
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")
    
    local_models = []
    
    # 1. Yerel Modelleri Çek ve Filtrele
    try:
        url = "http://localhost:11434/api/tags"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            
            # BURASI ÖNEMLİ: Nomic ve Embed içerenleri LİSTEDEN AT
            for m in data["models"]:
                name = m["name"]
                if "nomic" in name or "embed" in name:
                    continue # Bunu listeye alma, atla.
                local_models.append(name)
                
    except Exception as e:
        print(f"Ollama bağlantı hatası: {e}")
        # Hata olursa varsayılan bir şeyler ekle
        local_models = ["llama3"] 

    # 2. Senin İstediğin Özel Modeller (Cloud ve Sabitler)
    # Not: Gemini 2.5 henüz yok, o yüzden 1.5 Pro ve Flash ekliyorum.
    custom_models = [
        "gemini-2.5-flash",    # Google Hızlı
        "gemini-1.5-pro",      # Google Zeki
        "gpt-oss:120b-cloud"   # Senin Özel Modelin
    ]

    # 3. Listeleri Birleştir (Çift kayıt olmasın diye set kullanıp list'e çeviriyoruz)
    all_models = sorted(list(set(custom_models + local_models)))
    
    # Listede 'nomic' hala varsa zorla temizle 
    all_models = [m for m in all_models if "nomic" not in m]

    current = get_current_model_name()
    
    return {"models": all_models, "current": current}

@app.post("/admin/set-model")
def set_model(request: ModelUpdateRequest):
    if request.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Yanlış Şifre")
    
    rag_service.update_model(request.model_name)
    return {"success": True, "message": f"Model değiştirildi: {request.model_name}"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_excludes=["data/*"])