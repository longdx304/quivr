import logging
from typing import Any, List, Type, TypeVar

import tiktoken
from langchain_community.document_loaders import (
    BibtexLoader,
    CSVLoader,
    Docx2txtLoader,
    NotebookLoader,
    PythonLoader,
    UnstructuredEPubLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredODTLoader,
    UnstructuredPDFLoader,
    UnstructuredPowerPointLoader,
)
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.text import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import TextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings

from quivr_core.files.file import FileExtension, QuivrFile
from quivr_core.processor.processor_base import ProcessorBase
from quivr_core.processor.splitter import SemanticSplitterConfig, SplitterConfig

logger = logging.getLogger("quivr_core")

P = TypeVar("P", bound=BaseLoader)


class ProcessorInit(ProcessorBase):
    def __init__(self, *args, **loader_kwargs) -> None:
        pass


# FIXME(@aminediro):
# dynamically creates Processor classes. Maybe redo this for finer control over instanciation
# processor classes are opaque as we don't know what params they would have -> not easy to have lsp completion
def _build_processor(
    cls_name: str, load_cls: Type[P], cls_extensions: List[FileExtension | str]
) -> Type[ProcessorInit]:

    class _Processor(ProcessorBase):
        supported_extensions = cls_extensions

        def __init__(
            self,
            splitter: TextSplitter | None = None,
            splitter_config: SplitterConfig = SemanticSplitterConfig(),
            **loader_kwargs: dict[str, Any],
        ) -> None:
            self.enc = tiktoken.get_encoding("cl100k_base")
            self.loader_cls = load_cls
            self.loader_kwargs = loader_kwargs

            self.splitter_config = splitter_config

            if splitter:
                self.text_splitter = splitter
            else:
                # self.text_splitter = (
                #     RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                #         chunk_size=splitter_config.chunk_size,
                #         chunk_overlap=splitter_config.chunk_overlap,
                #     )
                # )
                logger.info(f"Using semantic splitter with config with file DOCX")
                embeddings = OpenAIEmbeddings(model=splitter_config.embedding_model)
                self.text_splitter = SemanticChunker(
                    embeddings=embeddings,
                    buffer_size=splitter_config.buffer_size,
                    add_start_index=True,
                    breakpoint_threshold_type="percentile",
                    breakpoint_threshold_amount=splitter_config.breakpoint_threshold * 100,  # Convert to percentage
                    # Add sentence split regex for better Vietnamese/multilingual support
                    sentence_split_regex=r'(?<=[.!?;])\s+|(?<=[。！？；])\s+|(?<=\.)\s+'
                )

        @property
        def processor_metadata(self) -> dict[str, Any]:
            return {
                "processor_cls": self.loader_cls.__name__,
                "splitter": self.splitter_config.model_dump(),
            }

        async def process_file_inner(self, file: QuivrFile) -> list[Document]:
            if hasattr(self.loader_cls, "__init__"):
                # NOTE: mypy can't correctly type this as BaseLoader doesn't have a constructor method
                loader = self.loader_cls(file_path=str(file.path), **self.loader_kwargs)  # type: ignore
            else:
                loader = self.loader_cls()

            documents = await loader.aload()
            docs = self.text_splitter.split_documents(documents)

            # Add chunk-specific metadata to each chunk
            for i, doc in enumerate(docs):
                # Preserve all document-level metadata
                doc.metadata.update(documents.metadata)
                
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
                doc.metadata["chunk_id"] = f"{documents.metadata['content_hash']}_chunk_{i}"

            return docs

    return type(cls_name, (ProcessorInit,), dict(_Processor.__dict__))


CSVProcessor = _build_processor("CSVProcessor", CSVLoader, [FileExtension.csv])
TikTokenTxtProcessor = _build_processor(
    "TikTokenTxtProcessor", TextLoader, [FileExtension.txt]
)
DOCXProcessor = _build_processor(
    "DOCXProcessor", Docx2txtLoader, [FileExtension.docx, FileExtension.doc]
)
XLSXProcessor = _build_processor(
    "XLSXProcessor", UnstructuredExcelLoader, [FileExtension.xlsx, FileExtension.xls, FileExtension.xlsm]
)
PPTProcessor = _build_processor(
    "PPTProcessor", UnstructuredPowerPointLoader, [FileExtension.pptx]
)
MarkdownProcessor = _build_processor(
    "MarkdownProcessor",
    UnstructuredMarkdownLoader,
    [FileExtension.md, FileExtension.mdx, FileExtension.markdown],
)
EpubProcessor = _build_processor(
    "EpubProcessor", UnstructuredEPubLoader, [FileExtension.epub]
)
BibTexProcessor = _build_processor("BibTexProcessor", BibtexLoader, [FileExtension.bib])
ODTProcessor = _build_processor(
    "ODTProcessor", UnstructuredODTLoader, [FileExtension.odt]
)
HTMLProcessor = _build_processor(
    "HTMLProcessor", UnstructuredHTMLLoader, [FileExtension.html]
)
PythonProcessor = _build_processor("PythonProcessor", PythonLoader, [FileExtension.py])
NotebookProcessor = _build_processor(
    "NotebookProcessor", NotebookLoader, [FileExtension.ipynb]
)
UnstructuredPDFProcessor = _build_processor(
    "UnstructuredPDFProcessor", UnstructuredPDFLoader, [FileExtension.pdf]
)
