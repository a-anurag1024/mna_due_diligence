from abc import ABC, abstractmethod
from typing import Any, List, Dict



class BaseLoader(ABC):
    @abstractmethod
    def list_files(self) -> List[str]: pass

    
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> Dict: pass


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, document: Any) -> List[Dict]: pass


class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]: pass


class BaseVectorStore(ABC):
    @abstractmethod
    async def upsert(self, points: List[Any]): pass