from pydantic_settings import BaseSettings
import dotenv 
import os

dotenv.load_dotenv()  # Load .env file if present

class Settings(BaseSettings):
    # Paths
    DATA_DIR: str = "./data/CUAD_v1"
    
    # MySQL Config (Metadata & State)
    MYSQL_USER: str = os.getenv("MYSQL_USER", "mna_user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "secure_user_password")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "mna_db")
    
    @property
    def DB_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    # Qdrant Config (Vectors)
    QDRANT_URL: str = "http://localhost:1333" # Or ":memory:" for testing
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")  # Load from env variable
    COLLECTION_NAME: str = "contracts_v1"
    
    # Hardware
    DEVICE: str = "cuda" # or "cpu"
    BATCH_SIZE: int = 1  # Low batch size for 6GB VRAM safety

settings = Settings()