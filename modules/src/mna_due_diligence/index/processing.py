from .base import BaseChunker, BaseEmbedder
from docling_core.transforms.chunker import HierarchicalChunker
from fastembed import TextEmbedding
from typing import List, Dict, Any
import structlog


logger = structlog.get_logger()


class HierarchicalChunkerWrapper(BaseChunker):
    def __init__(self):
        self.chunker = HierarchicalChunker(chunk_size=500, chunk_overlap=50)

    def chunk(self, doc_obj: Any) -> List[Dict]:
        chunks = []
        for chunk in self.chunker.chunk(doc_obj):
            # Enriched Context: Parent Headers + Content
            header_path = " > ".join([h for h in chunk.meta.headings]) if chunk.meta.headings else ">"
            enriched_text = f"Context: {header_path}\nContent: {chunk.text}"
            
            chunks.append({
                "text": chunk.text,
                "enriched_text": enriched_text,
                "headers": header_path,
                "page": chunk.meta.doc_items[0].prov[0].page_no if chunk.meta.doc_items else None,
                "is_table": bool(chunk.meta.doc_items and chunk.meta.doc_items[0].label == "table")
            })
        return chunks


class BGEEmbedder(BaseEmbedder):
    def __init__(self, model_name="BAAI/bge-m3", device="cuda"):
        providers = ["CUDAExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        logger.info("loading_model", model=model_name, device=device)
        self.model = TextEmbedding(model_name=model_name, providers=providers)

    def embed(self, texts: List[str]) -> List[List[float]]:
        # FastEmbed handles batching internally, but we stay safe with the config
        return list(self.model.embed(texts, batch_size=1))