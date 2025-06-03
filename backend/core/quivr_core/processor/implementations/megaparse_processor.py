import logging
import hashlib
import os
from pathlib import Path
 
import tiktoken
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from quivr_core.processor.megaparse import MegaParse
from quivr_core.processor.megaparse.config import MegaparseConfig
 
from quivr_core.files.file import QuivrFile
from quivr_core.processor.processor_base import ProcessorBase
from quivr_core.processor.registry import FileExtension
from quivr_core.processor.splitter import SplitterConfig, SemanticSplitterConfig
 
logger = logging.getLogger("quivr_core")
 
 
class MegaparseProcessor(ProcessorBase):
    """
    Megaparse processor for PDF files.
 
    It can be used to parse PDF files and split them into chunks.
 
    It comes from the megaparse library.
 
    ## Installation
    ```bash
    pip install megaparse
    ```
 
    """
 
    supported_extensions = [FileExtension.pdf, FileExtension.xls, FileExtension.xlsm, FileExtension.xlsx]
 
    def __init__(
        self,
        splitter: TextSplitter | None = None,
        splitter_config: SplitterConfig | SemanticSplitterConfig = SemanticSplitterConfig(),
        megaparse_config: MegaparseConfig = MegaparseConfig(),
    ) -> None:
        self.loader_cls = MegaParse
        self.enc = tiktoken.get_encoding("cl100k_base")
        self.splitter_config = splitter_config
        self.megaparse_config = megaparse_config
 
        if splitter:
            self.text_splitter = splitter
        else:
            # Check if semantic chunking is requested
            if isinstance(splitter_config, SemanticSplitterConfig) and splitter_config.chunking_strategy == "semantic":
                logger.info(f"Using semantic chunking with embedding model: {splitter_config.embedding_model}")
                
                # Initialize embeddings based on model
                if splitter_config.embedding_model.startswith("text-embedding"):
                    # OpenAI embeddings
                    embeddings = OpenAIEmbeddings(model=splitter_config.embedding_model)
                else:
                    # Default to OpenAI if not specified
                    logger.warning(f"Unknown embedding model {splitter_config.embedding_model}, defaulting to OpenAI")
                    embeddings = OpenAIEmbeddings()
                
                # Configure semantic chunker with advanced settings
                self.text_splitter = SemanticChunker(
                    embeddings=embeddings,
                    buffer_size=splitter_config.buffer_size,
                    add_start_index=True,
                    breakpoint_threshold_type="percentile",
                    breakpoint_threshold_amount=splitter_config.breakpoint_threshold * 100,  # Convert to percentage
                    # Add sentence split regex for better Vietnamese/multilingual support
                    sentence_split_regex=r'(?<=[.!?;])\s+|(?<=[。！？；])\s+|(?<=\.)\s+'
                )
                logger.info(f"Semantic chunker initialized with buffer_size={splitter_config.buffer_size}, threshold={splitter_config.breakpoint_threshold}")
            else:
                # Fallback to enhanced recursive character text splitter
                logger.info("Using enhanced recursive character text splitting")
                # Enhanced separators for better semantic chunking
                semantic_separators = [
                    "\n\n\n",  # Multiple line breaks (major sections)
                    "\n\n",    # Paragraph breaks
                    "\n",      # Line breaks
                    ". ",      # Sentence endings with space
                    "? ",      # Question endings
                    "! ",      # Exclamation endings
                    "; ",      # Semicolon (clause separation)
                    ", ",      # Comma (only as last resort)
                    " ",       # Word boundaries
                    ""         # Character level (final fallback)
                ]
                
                self.text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                    chunk_size=splitter_config.chunk_size,
                    chunk_overlap=splitter_config.chunk_overlap,
                    separators=semantic_separators,
                    keep_separator=True,  # Keep separators to maintain context
                    is_separator_regex=False,
                )
 
    def _extract_document_metadata(self, file: QuivrFile, document: Document) -> dict:
        """Extract enhanced metadata for better document identification and context."""
        file_path = Path(file.path)
        content = document.page_content
        
        # Basic file metadata
        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size": os.path.getsize(file.path) if os.path.exists(file.path) else 0,
            "content_hash": hashlib.md5(content.encode()).hexdigest()[:8],
        }
        
        # Document structure analysis
        lines = content.split('\n')
        metadata.update({
            "total_lines": len(lines),
            "total_characters": len(content),
            "total_tokens": len(self.enc.encode(content)),
        })
        
        # Content analysis for program/document type identification
        first_100_chars = content[:100].lower()
        metadata["content_preview"] = first_100_chars
        
        # Identify potential document type based on content patterns
        document_indicators = {
            "contract": ["contract", "agreement", "terms", "conditions", "obligations"],
            "program": ["program", "programme", "chương trình", "dự án", "project"],
            "manual": ["manual", "guide", "hướng dẫn", "instructions", "tutorial"],
            "report": ["report", "báo cáo", "analysis", "findings", "summary"],
            "specification": ["specification", "spec", "requirements", "đặc tả"],
            "policy": ["policy", "chính sách", "procedure", "quy trình", "regulation"]
        }
        
        detected_types = []
        for doc_type, keywords in document_indicators.items():
            if any(keyword in first_100_chars for keyword in keywords):
                detected_types.append(doc_type)
        
        metadata["detected_document_types"] = detected_types
        metadata["primary_document_type"] = detected_types[0] if detected_types else "general"
        
        # Extract potential program/project names (simple heuristic)
        potential_names = []
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and len(line) > 5 and len(line) < 100:
                # Look for title-like patterns
                if any(indicator in line.lower() for indicator in ["chương trình", "program", "dự án", "project"]):
                    potential_names.append(line)
        
        metadata["potential_program_names"] = potential_names[:3]  # Limit to 3 most likely names
        
        return metadata
 
    @property
    def processor_metadata(self):
        chunking_strategy = "semantic" if isinstance(self.splitter_config, SemanticSplitterConfig) and self.splitter_config.chunking_strategy == "semantic" else "enhanced_recursive"
        
        base_metadata = {
            "chunk_overlap": self.splitter_config.chunk_overlap,
            "chunking_strategy": chunking_strategy,
        }
        
        if isinstance(self.splitter_config, SemanticSplitterConfig) and self.splitter_config.chunking_strategy == "semantic":
            base_metadata.update({
                "embedding_model": self.splitter_config.embedding_model,
                "breakpoint_threshold": self.splitter_config.breakpoint_threshold,
                "buffer_size": self.splitter_config.buffer_size,
                "semantic_chunking": True
            })
        else:
            base_metadata.update({
                "separators_used": "multi_level_semantic",
                "semantic_chunking": False
            })
        
        return base_metadata
 
    async def process_file_inner(self, file: QuivrFile) -> list[Document]:
        mega_parse = MegaParse(file_path=file.path, config=self.megaparse_config)  # type: ignore
        document: Document = await mega_parse.aload()
        
        # Extract enhanced metadata for the document
        enhanced_metadata = self._extract_document_metadata(file, document)
        
        # Merge existing metadata with enhanced metadata
        document.metadata.update(enhanced_metadata)
        
        # Check if the document content needs splitting based on token count
        token_count = len(self.enc.encode(document.page_content))
        
        if token_count > self.splitter_config.chunk_size:
            docs = self.text_splitter.split_documents([document])
            
            # Add chunk-specific metadata to each chunk
            for i, doc in enumerate(docs):
                # Preserve all document-level metadata
                doc.metadata.update(enhanced_metadata)
                
                # Add chunk-specific metadata
                chunk_token_count = len(self.enc.encode(doc.page_content))
                doc.metadata.update({
                    "chunk_size": chunk_token_count,
                    "chunk_index": i,
                    "total_chunks": len(docs),
                    "chunk_position": f"{i+1}/{len(docs)}",
                    "is_first_chunk": i == 0,
                    "is_last_chunk": i == len(docs) - 1,
                })
                
                # Add context about the chunk's position in the document
                if i == 0:
                    doc.metadata["chunk_type"] = "document_start"
                elif i == len(docs) - 1:
                    doc.metadata["chunk_type"] = "document_end"
                else:
                    doc.metadata["chunk_type"] = "document_middle"
                
                # Add a unique identifier combining source and chunk
                doc.metadata["chunk_id"] = f"{enhanced_metadata['content_hash']}_chunk_{i}"
            
            return docs
        else:
            # If the document is smaller than chunk_size, return it as a single chunk
            document.metadata.update({
                "chunk_size": token_count,
                "chunk_index": 0,
                "total_chunks": 1,
                "chunk_position": "1/1",
                "is_first_chunk": True,
                "is_last_chunk": True,
                "chunk_type": "single_chunk",
                "chunk_id": f"{enhanced_metadata['content_hash']}_chunk_0",
            })
            return [document]
 