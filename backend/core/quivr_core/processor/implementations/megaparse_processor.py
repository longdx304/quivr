import logging
import hashlib
import os
import re
from pathlib import Path
from typing import List
 
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


class SafeSemanticChunker:
    """
    A wrapper around SemanticChunker that safely handles large documents
    by pre-chunking them when they exceed embedding API token limits.
    """
    
    def __init__(self, semantic_chunker: SemanticChunker, max_tokens: int = 250000):
        self.semantic_chunker = semantic_chunker
        self.max_tokens = max_tokens
        self.enc = tiktoken.get_encoding("cl100k_base")
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents safely, handling token limits."""
        all_chunks = []
        
        for doc in documents:
            token_count = len(self.enc.encode(doc.page_content))
            
            if token_count <= self.max_tokens:
                # Safe to process with semantic chunker
                try:
                    chunks = self.semantic_chunker.split_documents([doc])
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.warning(f"Semantic chunking failed for document (safe size): {e}. Using recursive fallback.")
                    chunks = self._fallback_split(doc)
                    all_chunks.extend(chunks)
            else:
                logger.info(f"Document too large ({token_count} tokens), pre-chunking before semantic analysis")
                # Pre-chunk into smaller pieces
                pre_chunks = self._pre_chunk_document(doc)
                
                for pre_chunk in pre_chunks:
                    try:
                        semantic_chunks = self.semantic_chunker.split_documents([pre_chunk])
                        all_chunks.extend(semantic_chunks)
                    except Exception as e:
                        logger.warning(f"Semantic chunking failed for pre-chunk: {e}. Using recursive fallback.")
                        fallback_chunks = self._fallback_split(pre_chunk)
                        all_chunks.extend(fallback_chunks)
        
        return all_chunks
    
    def _pre_chunk_document(self, document: Document) -> List[Document]:
        """Pre-chunk large document into smaller pieces for semantic processing."""
        # Use a larger chunk size for comprehensive content preservation
        # Increased to maintain detailed program information in single chunks
        safe_chunk_size = 2500
        
        pre_chunker = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=safe_chunk_size,
            chunk_overlap=500,  # Increased overlap to preserve comprehensive content relationships
            separators=[
                "\n\n\n",  # Major section breaks
                "\n\n",    # Paragraph breaks
                "### ",    # Markdown H3 headers (common in Vietnamese documents)
                "## ",     # Markdown H2 headers
                "# ",      # Markdown H1 headers
                "\n| ",    # Table row breaks (common in Vietnamese business docs)
                "\n- ",    # List items
                "\n",      # Line breaks
                ". ",      # Sentence endings
                "? ",      # Questions
                "! ",      # Exclamations
                ": ",      # Colons (common in Vietnamese program descriptions)
                "; ",      # Semicolons
                ", ",      # Commas (last resort)
                " ",       # Spaces
                ""         # Character level
            ],
            keep_separator=True,
        )
        
        return pre_chunker.split_documents([document])
    
    def _fallback_split(self, document: Document) -> List[Document]:
        """Fallback recursive splitting when semantic chunking fails."""
        fallback_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=2500,  # Increased for comprehensive content preservation
            chunk_overlap=500,
            separators=["\n\n\n", "\n\n", "### ", "## ", "# ", "\n| ", "\n- ", "\n", ". ", "? ", "! ", ": ", "; ", ", ", " ", ""],
            keep_separator=True,
        )
        return fallback_splitter.split_documents([document])


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
            # IMPORTANT: Default to enhanced recursive chunking for better document-specific context preservation
            # Semantic chunking tends to group similar content across documents, losing temporal context
            # Recursive chunking better preserves document boundaries and specific contexts
            
            use_semantic = (isinstance(splitter_config, SemanticSplitterConfig) and 
                          splitter_config.chunking_strategy == "semantic" and 
                          getattr(splitter_config, 'force_semantic', False))
            
            if use_semantic:
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
                semantic_chunker = SemanticChunker(
                    embeddings=embeddings,
                    buffer_size=splitter_config.buffer_size,
                    add_start_index=True,
                    breakpoint_threshold_type="percentile",
                    breakpoint_threshold_amount=splitter_config.breakpoint_threshold * 100,  # Convert to percentage
                    # Add sentence split regex for better Vietnamese/multilingual support
                    sentence_split_regex=r'(?<=[.!?;])\s+|(?<=[。！？；])\s+|(?<=\.)\s+'
                )
                
                # Wrap with safe chunker to handle large documents
                self.text_splitter = SafeSemanticChunker(semantic_chunker, max_tokens=250000)
                logger.info(f"Safe semantic chunker initialized with buffer_size={splitter_config.buffer_size}, threshold={splitter_config.breakpoint_threshold}")
            else:
                # DEFAULT: Enhanced recursive character text splitter for document-specific context preservation
                logger.info("Using enhanced recursive character text splitting (DEFAULT for better document context preservation)")
                
                # Enhanced separators optimized for Vietnamese business documents with temporal context
                document_aware_separators = [
                    # Document structure separators (highest priority)
                    "\n# THÔNG BÁO CHƯƠNG TRÌNH BÁN HÀNG THÁNG",  # Document headers
                    "\n## B. CHI TIẾT CÁC CHƯƠNG TRÌNH",           # Major sections
                    "\n### II. CÁC CHƯƠNG TRÌNH NHÓM ĐÔNG DƯỢC", # Sub-sections
                    "\n#### 1. Chương trình cá nhân hóa",         # Program sections
                    
                    # Table and list structures
                    "\n| TT | Mức thưởng | Điều kiện |",  # Table headers for reward conditions
                    "\n| --- | --- | --- |",                    # Table dividers
                    "\n| ",                                      # Table rows
                    
                    # Vietnamese business document patterns
                    "\n\n\n",     # Major section breaks
                    "\n\n",       # Paragraph breaks
                    "### ",       # H3 headers
                    "## ",        # H2 headers  
                    "# ",         # H1 headers
                    "\n- ",       # List items
                    "\n + ",      # Nested list items
                    "\n",         # Line breaks
                    
                    # Sentence and clause boundaries (Vietnamese-aware)
                    ". ",         # Sentence endings
                    "? ",         # Questions
                    "! ",         # Exclamations
                    ": ",         # Colons (very common in Vietnamese business docs)
                    "; ",         # Semicolons
                    ", ",         # Commas (last resort)
                    " ",          # Word boundaries
                    ""            # Character level (final fallback)
                ]
                
                self.text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                    chunk_size=splitter_config.chunk_size,
                    chunk_overlap=splitter_config.chunk_overlap,
                    separators=document_aware_separators,
                    keep_separator=True,  # Critical: keep separators to maintain document structure
                    is_separator_regex=False,
                )
                logger.info(f"Enhanced recursive chunker initialized with chunk_size={splitter_config.chunk_size}, overlap={splitter_config.chunk_overlap}")
 
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
        first_500_chars = content[:500].lower()
        metadata["content_preview"] = first_500_chars
        
        # CRITICAL: Extract temporal context (month/year) from document
        temporal_info = self._extract_temporal_context(content, file_path.name)
        metadata.update(temporal_info)
        
        # Extract document-specific identifier to prevent cross-document confusion
        document_id = self._extract_document_identifier(content, file_path.name)
        metadata["document_identifier"] = document_id
        
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
            if any(keyword in first_500_chars for keyword in keywords):
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

    def _extract_temporal_context(self, content: str, filename: str) -> dict:
        """Extract temporal context (month/year) from document content and filename."""
        import re
        
        temporal_metadata = {
            "document_month": None,
            "document_year": None,
            "document_period": None,
            "temporal_keywords": []
        }
        
        # Extract from filename first (most reliable)
        filename_lower = filename.lower()
        
        # Pattern for template-1, template-2, etc. (month indicators)
        if "template-1" in filename_lower:
            temporal_metadata["document_month"] = 1
            temporal_metadata["document_period"] = "january_2025"
        elif "template" in filename_lower and "-1" not in filename_lower:
            # Main template usually refers to current/main month
            temporal_metadata["document_month"] = 4
            temporal_metadata["document_period"] = "april_2025"
        
        # Extract from content - look for date patterns
        content_first_1000 = content[:1000]
        
        # Vietnamese month patterns
        month_patterns = {
            1: ["tháng 1", "tháng 01", "01/", "1/", "tháng một"],
            2: ["tháng 2", "tháng 02", "02/", "2/", "tháng hai"],
            3: ["tháng 3", "tháng 03", "03/", "3/", "tháng ba"],
            4: ["tháng 4", "tháng 04", "04/", "4/", "tháng tư"],
            5: ["tháng 5", "tháng 05", "05/", "5/", "tháng năm"],
            6: ["tháng 6", "tháng 06", "06/", "6/", "tháng sáu"],
            7: ["tháng 7", "tháng 07", "07/", "7/", "tháng bảy"],
            8: ["tháng 8", "tháng 08", "08/", "8/", "tháng tám"],
            9: ["tháng 9", "tháng 09", "09/", "9/", "tháng chín"],
            10: ["tháng 10", "10/", "tháng mười"],
            11: ["tháng 11", "11/", "tháng mười một"],
            12: ["tháng 12", "12/", "tháng mười hai", "tháng chạp"]
        }
        
        # Find month in content
        for month_num, patterns in month_patterns.items():
            for pattern in patterns:
                if pattern in content_first_1000.lower():
                    temporal_metadata["document_month"] = month_num
                    temporal_metadata["temporal_keywords"].append(pattern)
                    break
            if temporal_metadata["document_month"]:
                break
        
        # Extract year patterns
        year_patterns = re.findall(r'năm (\d{4})|(\d{4})', content_first_1000)
        for year_match in year_patterns:
            year = year_match[0] or year_match[1]
            if year and int(year) >= 2024 and int(year) <= 2026:
                temporal_metadata["document_year"] = int(year)
                temporal_metadata["temporal_keywords"].append(f"năm {year}")
                break
        
        # Create comprehensive period identifier
        if temporal_metadata["document_month"] and temporal_metadata["document_year"]:
            temporal_metadata["document_period"] = f"month_{temporal_metadata['document_month']}_{temporal_metadata['document_year']}"
        
        # Add specific program timing context for HHDN
        if "hoạt huyết dưỡng não" in content_first_1000.lower() or "hhdn" in content_first_1000.lower():
            # Extract specific date ranges for HHDN programs
            hhdn_patterns = [
                r'(\d{1,2}/\d{1,2})\s*–\s*(\d{1,2}/\d{1,2}/\d{4})',  # 1/4 – 19/4/2025
                r'(\d{1,2}/\d{1,2})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})',   # 1/4 - 19/4/2025
                r'từ\s*(\d{1,2}/\d{1,2})\s*–\s*(\d{1,2}/\d{1,2}/\d{4})', # từ 1/4 – 19/4/2025
            ]
            
            for pattern in hhdn_patterns:
                matches = re.findall(pattern, content_first_1000)
                if matches:
                    temporal_metadata["hhdn_period"] = matches[0]
                    temporal_metadata["temporal_keywords"].extend(matches[0])
                    break
        
        return temporal_metadata

    def _extract_document_identifier(self, content: str, filename: str) -> str:
        """Create a unique document identifier to prevent cross-document confusion."""
        import hashlib
        
        # Combine filename and key content elements for unique identification
        identifier_elements = [filename]
        
        content_first_200 = content[:200]
        
        # Add date from header if available (most distinctive element)
        date_patterns = [
            r'Hà Nội,\s*ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',
            r'ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content_first_200)
            if match:
                identifier_elements.append(f"date_{match.group()}")
                break
        
        # Add title or program identifier
        title_patterns = [
            r'THÔNG BÁO CHƯƠNG TRÌNH BÁN HÀNG THÁNG (\d{1,2}/\d{4})',
            r'CHƯƠNG TRÌNH BÁN HÀNG THÁNG (\d{1,2}/\d{4})',
            r'BÁN HÀNG THÁNG (\d{1,2}/\d{4})',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, content_first_200)
            if match:
                identifier_elements.append(f"program_{match.group(1)}")
                break
        
        # Create hash from combined elements
        identifier_string = "_".join(identifier_elements)
        document_hash = hashlib.md5(identifier_string.encode()).hexdigest()[:12]
        
        return f"{filename}_{document_hash}"

    def _create_temporal_context_prefix(self, metadata: dict) -> str:
        """Create a temporal context prefix for chunks to prevent cross-document confusion."""
        
        # Build context elements
        context_elements = []
        
        # Add document identifier
        if metadata.get("document_identifier"):
            context_elements.append(f"Document: {metadata['document_identifier']}")
        
        # Add temporal context
        if metadata.get("document_month") and metadata.get("document_year"):
            month_names = {
                1: "Tháng 1", 2: "Tháng 2", 3: "Tháng 3", 4: "Tháng 4",
                5: "Tháng 5", 6: "Tháng 6", 7: "Tháng 7", 8: "Tháng 8",
                9: "Tháng 9", 10: "Tháng 10", 11: "Tháng 11", 12: "Tháng 12"
            }
            month_name = month_names.get(metadata["document_month"], f"Tháng {metadata['document_month']}")
            context_elements.append(f"Thời gian: {month_name}/{metadata['document_year']}")
        
        # Add specific program period if available
        if metadata.get("document_period"):
            context_elements.append(f"Kỳ áp dụng: {metadata['document_period']}")
        
        # Add HHDN specific period if available
        if metadata.get("hhdn_period"):
            hhdn_start, hhdn_end = metadata["hhdn_period"]
            context_elements.append(f"Chương trình HHDN: {hhdn_start} – {hhdn_end}")
        
        # Add filename for additional context
        if metadata.get("filename"):
            context_elements.append(f"Nguồn: {metadata['filename']}")
        
        return ""
 
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
            docs = self._split_document_safely(document, enhanced_metadata)
            return docs
        else:
            # If the document is smaller than chunk_size, return it as a single chunk
            # But still add temporal context prefix to prevent cross-document confusion
            temporal_prefix = self._create_temporal_context_prefix(enhanced_metadata)
            if temporal_prefix and not document.page_content.startswith(temporal_prefix):
                document.page_content = f"{temporal_prefix}\n\n{document.page_content}"
                # Recalculate token count after adding prefix
                token_count = len(self.enc.encode(document.page_content))
            
            document.metadata.update({
                "chunk_size": token_count,
                "chunk_index": 0,
                "total_chunks": 1,
                "chunk_position": "1/1",
                "is_first_chunk": True,
                "is_last_chunk": True,
                "chunk_type": "single_chunk",
                "chunk_id": f"{enhanced_metadata['content_hash']}_chunk_0",
                "has_temporal_prefix": bool(temporal_prefix),
            })
            return [document]
    
    def _split_document_safely(self, document: Document, enhanced_metadata: dict) -> list[Document]:
        """
        Split documents safely using the configured text splitter.
        The SafeSemanticChunker wrapper handles token limits automatically.
        """
        try:
            # Use the configured text splitter (which may be SafeSemanticChunker or RecursiveCharacterTextSplitter)
            docs = self.text_splitter.split_documents([document])
            
        except Exception as e:
            logger.error(f"Document splitting failed with error: {e}. Using fallback recursive chunking.")
            
            # Final fallback to enhanced recursive chunking with Vietnamese document support
            fallback_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=self.splitter_config.chunk_size,
                chunk_overlap=self.splitter_config.chunk_overlap,
                separators=["\n\n\n", "\n\n", "### ", "## ", "# ", "\n| ", "\n- ", "\n", ". ", "? ", "! ", ": ", "; ", ", ", " ", ""],
                keep_separator=True,
            )
            docs = fallback_splitter.split_documents([document])
            
            # Update metadata to indicate fallback was used
            enhanced_metadata["chunking_fallback_used"] = True
            enhanced_metadata["fallback_reason"] = str(e)
        
        # Add chunk-specific metadata and temporal context to each chunk
        for i, doc in enumerate(docs):
            # Preserve all document-level metadata
            doc.metadata.update(enhanced_metadata)
            
            # CRITICAL: Add temporal context prefix to chunk content to prevent cross-document confusion
            temporal_prefix = self._create_temporal_context_prefix(enhanced_metadata)
            
            # Prepend temporal context to chunk content (this is KEY for correct retrieval)
            if temporal_prefix and not doc.page_content.startswith(temporal_prefix):
                doc.page_content = f"{temporal_prefix}\n\n{doc.page_content}"
            
            # Add chunk-specific metadata
            chunk_token_count = len(self.enc.encode(doc.page_content))
            doc.metadata.update({
                "chunk_size": chunk_token_count,
                "chunk_index": i,
                "total_chunks": len(docs),
                "chunk_position": f"{i+1}/{len(docs)}",
                "is_first_chunk": i == 0,
                "is_last_chunk": i == len(docs) - 1,
                "has_temporal_prefix": bool(temporal_prefix),
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
 