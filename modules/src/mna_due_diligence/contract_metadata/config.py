import os
import dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field

dotenv.load_dotenv()  # Load .env file if present


class MetadataPipelineConfig(BaseSettings):
    
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

    # Environment file support
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")



# Helper to load config
def get_config() -> MetadataPipelineConfig:
    return MetadataPipelineConfig()