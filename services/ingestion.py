import os
import shutil
import time
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from core.config import settings

def run_ingestion():
    print(" Akıllı Veritabanı Güncellemesi Başlatılıyor...")

    DATA_PATH = settings.PDF_SOURCE_DIR
    DB_PATH = settings.VECTOR_DB_PATH

    # 1. Klasör Kontrolü
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        return "Veri klasörü oluşturuldu."
    current_files = set([f for f in os.listdir(DATA_PATH) if f.lower().endswith('.pdf')])
    
    # Embedding Modelini Hazırla
    try:
        embeddings = OllamaEmbeddings(
            model=settings.EMBED_MODEL,
            base_url="http://localhost:11434"
        )
    except Exception as e:
        return f" Embedding hatası: {e}"

    # 2. Veritabanına Bağlan (Eğer DB klasörü yoksa sıfırdan oluşturur, varsa bağlanır)
    vectorstore = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )

    # 3. Veritabanındaki Mevcut Dosyaları Tespit Et
    existing_sources = set()
    try:
        existing_data = vectorstore.get(include=["metadatas"])
        for meta in existing_data.get('metadatas', []):
            if meta and 'source' in meta:
                filename = os.path.basename(meta['source'])
                existing_sources.add(filename)
    except Exception as e:
        print("Uyarı: Mevcut veritabanı okunamadı. Sıfırdan başlanacak.")

    files_to_add = current_files - existing_sources
    files_to_delete = existing_sources - current_files

    print(f" Klasördeki PDF'ler: {len(current_files)}")
    print(f" Veritabanından Silinecek: {len(files_to_delete)}")
    print(f" Veritabanına Eklenecek: {len(files_to_add)}")

    if not files_to_add and not files_to_delete:
        return " Herhangi bir değişiklik yok. Veritabanı güncel."

    # 5. SİLİNEN PDF'LERİ TEMİZLE
    if files_to_delete:
        print(f" Eski kayıtlar temizleniyor: {list(files_to_delete)}")
        data = vectorstore.get(include=["metadatas"])
        ids_to_delete = []
        
        for i, meta in enumerate(data.get('metadatas', [])):
            if meta and 'source' in meta:
                if os.path.basename(meta['source']) in files_to_delete:
                    ids_to_delete.append(data['ids'][i])
        
        if ids_to_delete:
            vectorstore.delete(ids=ids_to_delete)
            print(f" {len(ids_to_delete)} adet eski parça silindi.")

    # 6. SADECE YENİ PDF'LERİ EKLE
    if files_to_add:
        documents = []
        for pdf_file in files_to_add:
            print(f" Yeni dosya okunuyor: {pdf_file}")
            file_path = os.path.join(DATA_PATH, pdf_file)
            try:
                loader = PyMuPDFLoader(file_path)
                documents.extend(loader.load())
            except Exception as e:
                print(f" Dosya okuma hatası ({pdf_file}): {e}")

        if documents:
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(documents)
            print(f" Toplam {len(splits)} yeni parça vektörleştiriliyor...")
            
            # Sadece yeni parçaları veritabanına ilave et (Eskilerin üzerine yazmaz)
            vectorstore.add_documents(documents=splits)
            print(" Yeni dosyalar eklendi!")

    return f"Güncelleme Tamamlandı! Eklendi: {len(files_to_add)}, Silindi: {len(files_to_delete)}"

if __name__ == "__main__":
    run_ingestion()