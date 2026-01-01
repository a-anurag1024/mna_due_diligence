from .base import BaseVectorStore
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from config import settings
import structlog


logger = structlog.get_logger()


class QdrantStore(BaseVectorStore):
    def __init__(self,
                 url: str = None,
                 collection_name: str = None):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.client = AsyncQdrantClient(url=self.url,
                                        api_key=settings.QDRANT_API_KEY)
    
    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )

    async def upsert(self, points: list[PointStruct]):
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info("vectors_upserted", count=len(points))