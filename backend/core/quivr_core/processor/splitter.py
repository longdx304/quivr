from pydantic import BaseModel
 
 
class SplitterConfig(BaseModel):
    """
    This class is used to configure the chunking of the documents.
 
    Chunk size is the number of characters in the chunk.
    Chunk overlap is the number of characters that the chunk will overlap with the previous chunk.
    """
 
    chunk_size: int = 1500
    chunk_overlap: int = 300
 
class SemanticSplitterConfig(SplitterConfig):
    """
    This class is used to configure the chunking of the documents.
 
    Chunk size is the number of characters in the chunk.
    Chunk overlap is the number of characters that the chunk will overlap with the previous chunk.
    """
 
    chunking_strategy: str = "semantic"
    embedding_model: str = "text-embedding-3-large"
    breakpoint_threshold: float = 0.5
    add_embeddings_to_chunks: bool = False
    buffer_size: int = 5