from cmath import nan
import os
import glob
from .base import BaseLoader, BaseParser
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
import structlog


logger = structlog.get_logger()


class LocalFileLoader(BaseLoader):
    def __init__(self, directory: str):
        self.directory = directory

    def list_files(self) -> list[str]:
        return [f for f in os.listdir(self.directory) if f.endswith(".pdf")]
    
class CUAD_LocalFileLoader(BaseLoader):
    def __init__(self, directory: str):
        self.directory = directory

    def list_files(self) -> list[str]:
        # Use recursive glob to find all PDFs in subdirectories
        return glob.glob(os.path.join(self.directory, "**/*.pdf"), recursive=True) 


class DoclingParser(BaseParser):
    def __init__(self):
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse(self, file_path: str):
        logger.info("parsing_started", file=file_path)
        conv = self.converter.convert(file_path)
        return {
            "doc_obj": conv.document,
            "confidence": {
                'parse_score': float(conv.confidence.parse_score),
                'layout_score': float(conv.confidence.layout_score),
                'table_score': float(conv.confidence.table_score),
                'ocr_score': float(conv.confidence.ocr_score)
                },
        }