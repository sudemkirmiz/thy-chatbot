import os
import gc
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from core.config import settings
from services.prompt_manager import get_current_prompt, save_prompt_to_file
from services.model_manager import get_current_model_name, save_model_name

class RAGService:
    def __init__(self):
        self.initialize()

    def initialize(self):
        print(" RAG Servisi Yükleniyor...")
        self.rag_chain = None
        self.system_prompt = get_current_prompt()
        self.vectorstore = None 
        self.retriever = None
        
        current_model = get_current_model_name()
        print(f" Aktif LLM Modeli: {current_model}")

        # 1. Embedding (Vektörleştirici - Hep Yerel Kalır)
        try:
            self.embeddings = OllamaEmbeddings(
                model=settings.EMBED_MODEL,
                base_url="http://localhost:11434"
            )
        except Exception:
            self.embeddings = None

        # 2. Vector Store
        if os.path.exists(settings.VECTOR_DB_PATH) and self.embeddings:
            try:
                self.vectorstore = Chroma(
                    persist_directory=settings.VECTOR_DB_PATH,
                    embedding_function=self.embeddings
                )
                self.retriever = self.vectorstore.as_retriever(
                    search_type="mmr",  # similarity yerine mmr 
                    search_kwargs={
                        "k": 15,       
                        "fetch_k": 40 
                    }
                )
                print(" Veritabanı Bağlandı.")
            except Exception as e:
                print(f" DB Hatası: {e}")
        else:
            print(" Veritabanı henüz yok.")

        # 3. LLM SEÇİMİ (SADELEŞTİRİLMİŞ MANTIK)
        try:
            # A) Eğer isimde "gemini" geçiyorsa -> Google Cloud
            if "gemini" in current_model.lower():
                print("  Google Cloud Modeli (Gemini) Devrede...")
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    print(" UYARI: GOOGLE_API_KEY bulunamadı!")
                
                self.llm = ChatGoogleGenerativeAI(
                    model=current_model,
                    google_api_key=api_key,
                    temperature=0.7
                )
            
            # B) Geriye kalan her şey -> Yerel Ollama
            else:
                print(f" Yerel Ollama Modeli ({current_model}) Devrede...")
                self.llm = ChatOllama(
                    model=current_model,
                    base_url="http://localhost:11434",
                    temperature=0.7
                )

        except Exception as e:
            print(f" LLM Yükleme Hatası: {e}")
            self.llm = None

        # 4. Zincir
        self._build_chain()

    def release_resources(self):
        print(" Kaynaklar serbest bırakılıyor...")
        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None
        gc.collect()

    def _build_chain(self):
        if not self.llm or not self.retriever:
            self.rag_chain = None
            return

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        full_system_prompt = (
            f"{self.system_prompt}\n\n"
            "Dokümanlar (Context):\n{context}\n\n"
            "Sadece bu bilgilere göre cevapla."
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", full_system_prompt),
            ("human", "{input}")
        ])

        self.rag_chain = (
            {"context": self.retriever | format_docs, "input": RunnablePassthrough()}
            | prompt_template
            | self.llm
            | StrOutputParser()
        )

    def reload_knowledge(self):
        print(" Sistem tazeleniyor...")
        self.initialize()

    def update_system_prompt(self, new_prompt: str):
        save_prompt_to_file(new_prompt)
        self.system_prompt = new_prompt
        self._build_chain()

    def update_model(self, new_model_name: str):
        print(f" Model değiştiriliyor: {new_model_name}")
        save_model_name(new_model_name)
        self.initialize()

    def ask(self, query: str):
        if not self.rag_chain:
            return {"answer": " Sistem şu an güncelleniyor, lütfen bekleyin.", "sources": []}
        try:
            docs = self.retriever.invoke(query)
            sources = [d.metadata.get("source", "Bilinmeyen") for d in docs]
            answer = self.rag_chain.invoke(query)
            return {"answer": answer, "sources": sources}
        except Exception:
            return {"answer": "Hata oluştu.", "sources": []}

rag_service = RAGService()