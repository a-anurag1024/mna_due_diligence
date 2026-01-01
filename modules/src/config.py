from pydantic_settings import BaseSettings
import dotenv 
import os

dotenv.load_dotenv()  # Load .env file if present

class Settings(BaseSettings):
    # Paths
    DATA_DIR: str = "./data/CUAD_v1"
    
    # MySQL Config (Metadata & State)
    DB_URL: str = "mysql+aiomysql://user:password@localhost/mna_db"
    
    # Qdrant Config (Vectors)
    QDRANT_URL: str = "http://localhost:1333" # Or ":memory:" for testing
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")  # Load from env variable
    COLLECTION_NAME: str = "contracts_v1"
    
    # Hardware
    DEVICE: str = "cuda" # or "cpu"
    BATCH_SIZE: int = 1  # Low batch size for 6GB VRAM safety

settings = Settings()