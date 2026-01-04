import os
import asyncio
import traceback
import uuid
import structlog
from sqlalchemy import select, update, Insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import MetadataPipelineConfig
from mna_due_diligence.db import Base, FileState, ProcessingStatus, Contract
from .extractor import MetadataExtractor
from qdrant_client.models import PointStruct, ExtendedPointId


logger = structlog.get_logger()



class MetadataPipelineOrchestrator:
    def __init__(self, config: MetadataPipelineConfig):
        self.config = config
        self.logger = logger.bind(module="metadata_extraction_orchestrator")
        
        # --- INFRASTRUCTURE SETUP ---
        # 1. Database Engine
        self.db_engine = create_async_engine(self.config.DB_URL, echo=False)
        self.SessionLocal = async_sessionmaker(self.db_engine, expire_on_commit=False)
        
        # 2. Pipeline Module
        self.extractor = MetadataExtractor(model="gpt-4.1-nano")
        


    async def _initialize_resources(self):
        """Creates SQL tables and Vector Collections if they don't exist."""
        self.logger.info("system_initialization_started")
        
        # Init MySQL Tables
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


    async def _check_if_file_processed(self, session: AsyncSession, filename: str) -> bool:
        """Check if the file has already been processed successfully."""
        select_stmt = select(Contract).where(Contract.filename == filename)
        result = await session.execute(select_stmt)
        record = result.scalars().first()
        return record is not None
    
    
    async def _list_files_to_process(self) -> list[str]:
        """Lists all files in the DB."""
        files = []
        async with self.SessionLocal() as session:
            result = await session.execute(select(FileState.filename).where(
                FileState.status == ProcessingStatus.COMPLETED
            ))
            records = result.scalars().all()
            files.extend(records)
        return files


    async def _process_single_file(self, session: AsyncSession, filename: str):
        """The core logic pipeline for a single document."""
        log = self.logger.bind(filename=filename)
        try:
            # 1. Get the markdown content from DB
            select_stmt = select(FileState).where(FileState.filename == filename)
            result = await session.execute(select_stmt)
            file_record = result.scalars().first()
            if not file_record:
                raise ValueError(f"File record for {filename} not found in DB.")
            markdown = file_record.markdown
            if not markdown:
                raise ValueError(f"No markdown content found for {filename}.")
            # 2. Extract Metadata
            metadata = self.extractor.extract(markdown)
            log.info("metadata_extraction_successful", metadata=metadata.dict())
            # 3. Add the metadata to DB
            add_stmt = Insert(Contract).values(
                filename=filename,
                title=metadata.contract_title,
                contract_type=metadata.contract_type,
                party_a=metadata.party_a,
                party_b=metadata.party_b,
                effective_date=metadata.effective_date,
                expiration_date=metadata.expiration_date,
                governing_law=metadata.governing_law
            )
            await session.execute(add_stmt)
            await session.commit()
        except Exception as e:
            log.error("processing_failed", error=str(e)+traceback.format_exc())


    async def run(self):
        """Main entry point to run the pipeline."""
        files = await self._list_files_to_process()
        self.logger.info("pipeline_started", file_count=len(files))

        async with self.SessionLocal() as session:
            for filename in files:
                # Resumability Check
                check = await self._check_if_file_processed(session, filename)
                if check:
                    self.logger.info("skipping_already_completed", filename=filename)
                    continue
                
                # Execute
                await self._process_single_file(session, filename)

        await self.db_engine.dispose()
        self.logger.info("pipeline_finished")