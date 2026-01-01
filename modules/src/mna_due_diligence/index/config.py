import os
import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field

dotenv.load_dotenv()  # Load .env file if present


class IndexPipelineConfig(BaseSettings):
    # Paths
    DATA_DIR: str = Field(default="./data/CUAD_v1/full_contract_pdf", description="Directory containing source PDFs")
    
    # Database (Metadata & State)
    MYSQL_USER: str = Field(default="user", description="MySQL user")
    MYSQL_PASSWORD: str = Field(default="password", description="MySQL password")
    MYSQL_DATABASE: str = Field(default="mna_db", description="MySQL database name")
    MYSQL_HOST: str = Field(default="localhost", description="MySQL host")
    MYSQL_PORT: int = Field(default=3306, description="MySQL port")
    
    @computed_field
    @property
    def DB_URL(self) -> str:
        """Construct the database URL from MySQL credentials"""
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
    
    # Vector Database (Qdrant)
    QDRANT_URL: str = Field(default="http://localhost:1333", description="Qdrant server URL")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")  # Load from env variable
    COLLECTION_NAME: str = Field(default="contracts_v1", description="Qdrant collection name")
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-base-en-v1.5", description="HuggingFace model name")
    
    # Hardware / Performance
    DEVICE: str = Field(default="cuda", description="'cuda' or 'cpu'")
    BATCH_SIZE: int = Field(default=1, description="Batch size for embedding (keep low for 6GB VRAM)")

    # Environment file support
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")



# Helper to load config
def get_config() -> IndexPipelineConfig:
    return IndexPipelineConfig()