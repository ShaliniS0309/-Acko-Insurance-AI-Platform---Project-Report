# app/rag_chatbot.py
import os
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .config import Config
from .database import get_session, save_chat_log

class PolicyChatbot:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=Config.CHROMA_PATH)
        self.embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=Config.GEMINI_API_KEY
        )
        self.collection = self._get_or_create_collection()
        self.genai = Config.get_gemini_client()
        self.model = self.genai.GenerativeModel('gemini-1.5-flash')
    
    def _get_or_create_collection(self):
        try:
            return self.client.get_collection("acko_policies")
        except:
            return self.client.create_collection(
                name="acko_policies",
                embedding_function=self.embedding_fn
            )
    
    def index_policies(self, pdf_paths):
        """Load PDFs and index them in ChromaDB"""
        all_chunks = []
        for path in pdf_paths:
            loader = PyPDFLoader(path)
            docs = loader.load()
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=Config.CHUNK_SIZE,
                chunk_overlap=Config.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata['source'] = os.path.basename(path)
            all_chunks.extend(chunks)
        
        # Add to ChromaDB
        documents = [c.page_content for c in all_chunks]
        metadatas = [c.metadata for c in all_chunks]
        ids = [f"chunk_{i}" for i in range(len(documents))]
        
        # Batch add
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            end = min(i + batch_size, len(documents))
            self.collection.add(
                documents=documents[i:end],
                metadatas=metadatas[i:end],
                ids=ids[i:end]
            )
        return len(documents)
    
    def query(self, question, user_id=None):
        """Answer a policy question using RAG"""
        # Retrieve relevant chunks
        results = self.collection.query(
            query_texts=[question],
            n_results=Config.RETRIEVAL_K
        )
        
        chunks = results['documents'][0] if results['documents'] else []
        sources = [m.get('source', 'unknown') for m in results['metadatas'][0]] if results['metadatas'] else []
        
        if not chunks:
            answer = "I couldn't find that information in our policy documents. Please contact our support team."
        else:
            context = "\n\n".join(chunks)
            prompt = f"""
            You are Acko Insurance's AI assistant. Answer the customer's question using ONLY the context provided.
            
            CONTEXT:
            {context}
            
            CUSTOMER QUESTION: {question}
            
            RULES:
            1. Answer in simple, clear language
            2. Only use information from the context
            3. If the answer isn't in context, say "I don't have that information"
            4. Be friendly and helpful
            5. Keep it concise
            
            ANSWER:
            """
            response = self.model.generate_content(prompt)
            answer = response.text
            if sources:
                answer += f"\n\n📚 Source: {', '.join(set(sources))}"
        
        # Log interaction
        if user_id:
            session = get_session()
            save_chat_log(session, {
                'user_id': user_id,
                'intent': 'policy_qa',
                'question': question,
                'answer': answer,
                'sources': ', '.join(set(sources))
            })
        
        return {'answer': answer, 'sources': sources, 'chunks_used': len(chunks)}