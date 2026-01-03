import os
import asyncio
import traceback
import uuid
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import IndexPipelineConfig
from mna_due_diligence.db import Base, FileState, ProcessingStatus
from .ingestion import CUAD_LocalFileLoader, LocalFileLoader, DoclingParser
from .processing import HierarchicalChunkerWrapper, BGEEmbedder
from .vdb_store import QdrantStore
from qdrant_client.models import PointStruct, ExtendedPointId


logger = structlog.get_logger()



class IndexPipelineOrchestrator:
    def __init__(self, config: IndexPipelineConfig):
        self.config = config
        self.logger = logger.bind(module="orchestrator")
        
        # --- INFRASTRUCTURE SETUP ---
        # 1. Database Engine
        self.db_engine = create_async_engine(self.config.DB_URL, echo=False)
        self.SessionLocal = async_sessionmaker(self.db_engine, expire_on_commit=False)
        
        # 2. Pipeline Modules
        # We initialize them here using the passed config
        #self.loader = LocalFileLoader(directory=self.config.DATA_DIR)
        self.loader = CUAD_LocalFileLoader(directory=self.config.DATA_DIR)
        self.parser = DoclingParser() # Docling config is internal to class for now
        self.chunker = HierarchicalChunkerWrapper()
        self.embedder = BGEEmbedder(
            model_name=self.config.EMBEDDING_MODEL, 
            device=self.config.DEVICE
        )
        self.vector_store = QdrantStore(
            url=self.config.QDRANT_URL, 
            collection_name=self.config.COLLECTION_NAME
        )


    async def _initialize_resources(self):
        """Creates SQL tables and Vector Collections if they don't exist."""
        self.logger.info("system_initialization_started")
        
        # Init MySQL Tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Init Qdrant Collection
        await self.vector_store.ensure_collection()
        self.logger.info("system_initialization_complete")


    async def _get_or_create_file_state(self, session: AsyncSession, filename: str) -> FileState:
        """Checks DB for file status. Creates new record if missing."""
        result = await session.execute(select(FileState).where(FileState.filename == filename))
        record = result.scalars().first()
        
        if not record:
            record = FileState(filename=filename, status=ProcessingStatus.PENDING)
            session.add(record)
            await session.commit()
            
        return record


    async def _update_status(self, 
                             session: AsyncSession, 
                             filename: str, 
                             status: ProcessingStatus,
                             markdown: str = None, 
                             page_count: str = None, 
                             error: str = None):
        """Helper to update state in SQL."""
        stmt = update(FileState).where(FileState.filename == filename).values(
            status=status, 
            markdown=markdown, 
            page_count=page_count,
            error_message=error
        )
        await session.execute(stmt)
        await session.commit()


    async def _process_single_file(self, session: AsyncSession, filename: str):
        """The core logic pipeline for a single document."""
        log = self.logger.bind(filename=filename)
        
        try:
            # 1. Update State -> PROCESSING
            await self._update_status(session, filename, ProcessingStatus.PROCESSING)
            log.info("processing_started")

            # 2. Parse (CPU Bound)
            # Note: In a real heavy app, run this in a threadpool: 
            # await asyncio.to_thread(self.parser.parse, path)
            #file_path = os.path.join(self.config.DATA_DIR, filename)
            file_path = filename  # CUAD loader gives full path
            parser_return = self.parser.parse(file_path)
            doc_obj = parser_return['doc_obj']
    
            # 3. Chunk
            chunks = self.chunker.chunk(doc_obj)
            log.info("document_chunked", count=len(chunks))

            # 4. Embed (GPU Bound)
            texts = [c['enriched_text'] for c in chunks]
            vectors = self.embedder.embed(texts)

            # 5. Store (Network Bound)
            # Normalize filename to use forward slashes for JSON compatibility
            normalized_filename = filename.replace("\\", "/")
            points = [
                PointStruct(
                    id=uuid.uuid4(),
                    vector=vec,
                    payload={**chunk, **parser_return["confidence"], "filename": normalized_filename, "chunk_index": i}
                ) 
                for i, (chunk, vec) in enumerate(zip(chunks, vectors))
            ]
            await self.vector_store.upsert(points)

            # 6. Update State -> COMPLETED
            await self._update_status(session, filename, ProcessingStatus.COMPLETED, markdown=doc_obj.export_to_markdown(), page_count=len(doc_obj.pages))
            log.info("processing_completed_successfully")

        except Exception as e:
            log.error("processing_failed", error=str(e)+traceback.format_exc())
            await self._update_status(session, filename, ProcessingStatus.FAILED, error=str(e))


    async def run(self):
        """Main entry point to run the pipeline."""
        await self._initialize_resources()
        
        files = self.loader.list_files()
        self.logger.info("files_found", count=len(files))

        async with self.SessionLocal() as session:
            for filename in files:
                # Resumability Check
                record = await self._get_or_create_file_state(session, filename)
                
                if record.status == ProcessingStatus.COMPLETED:
                    self.logger.info("skipping_already_completed", filename=filename)
                    continue
                
                # Execute Pipeline
                await self._process_single_file(session, filename)

        await self.db_engine.dispose()
        self.logger.info("pipeline_finished")