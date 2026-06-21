# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # AWS
    AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'acko-claims')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///acko.db')
    
    # Paths
    MODEL_PATH = os.getenv('MODEL_PATH', 'models')
    CHROMA_PATH = os.getenv('CHROMA_PATH', 'data/chromadb')
    POLICY_PATH = os.getenv('POLICY_PATH', 'data/raw/policies')
    
    # Model settings
    RETRIEVAL_K = 3
    APPROVAL_THRESHOLD = 0.5
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    
    @classmethod
    def get_gemini_client(cls):
        import google.generativeai as genai
        genai.configure(api_key=cls.GEMINI_API_KEY)
        return genai