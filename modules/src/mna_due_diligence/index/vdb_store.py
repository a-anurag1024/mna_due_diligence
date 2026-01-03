from .base import BaseVectorStore
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    PointStruct, 
    VectorParams, 
    Distance, 
    OptimizersConfigDiff,
    HnswConfigDiff,
    WalConfigDiff
)
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
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                # Disable automatic indexing during batch inserts
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000,  # Only index after 20k points (vs default 20k)
                    max_segment_size=200000,   # Larger segments reduce optimization frequency
                ),
                # Configure HNSW index parameters
                hnsw_config=HnswConfigDiff(
                    m=16,                       # Number of edges per node
                    ef_construct=100,           # Construction time/accuracy tradeoff
                    full_scan_threshold=10000,  # Use full scan for small datasets
                ),
                # Enable WAL for better crash recovery
                wal_config=WalConfigDiff(
                    wal_capacity_mb=32,
                    wal_segments_ahead=0,
                )
            )
            logger.info("collection_created", collection=self.collection_name)

    async def upsert(self, points: list[PointStruct], wait: bool = True):
        """
        Upsert points to Qdrant collection.
        
        Args:
            points: List of PointStruct objects to upsert
            wait: If True, wait for the operation to complete before returning (prevents corruption)
        """
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=wait  # Wait for write to complete, preventing optimization race conditions
        )
        logger.info("vectors_upserted", count=len(points))