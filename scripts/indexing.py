import asyncio
import logging
import structlog
from pathlib import Path

from mna_due_diligence.index.orchestrator import IndexPipelineOrchestrator
from mna_due_diligence.index.config import get_config


# Ensure logs directory exists
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure standard logging with file handler
file_handler = logging.FileHandler("logs/indexing.log", mode="a")
file_handler.setLevel(logging.INFO)

# Remove default handlers and add only file handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()  # Remove console handler
root_logger.addHandler(file_handler)

# Configure structlog to use standard logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


async def main():
    # 1. Load Config
    config = get_config()
    config.DATA_DIR = "./data/CUAD_v1/full_contract_pdf"  # Ensure data directory is set correctly
    
    # 2. Instantiate Orchestrator
    orchestrator = IndexPipelineOrchestrator(config)
    
    # 3. Run
    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())