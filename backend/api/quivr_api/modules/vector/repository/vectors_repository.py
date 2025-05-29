from typing import Any, List, Sequence
from uuid import UUID

from quivr_api.logger import get_logger
from quivr_api.modules.dependencies import BaseRepository
from quivr_api.modules.vector.entity.vector import SimilaritySearchOutput, Vector
from sqlalchemy import exc, text
from sqlmodel import Session, select

logger = get_logger(__name__)


class VectorRepository(BaseRepository):
    def __init__(self, session: Session):
        super().__init__(session)
        self.session = session

    def create_vectors(self, new_vectors: List[Vector]) -> List[Vector]:
        try:
            # Use SQLAlchemy session to add and commit the new vector
            self.session.add_all(new_vectors)
            self.session.commit()
        except exc.IntegrityError:
            # Rollback the session if there's an IntegrityError
            self.session.rollback()
            raise Exception("Integrity error occurred while creating vector.")
        except Exception as e:
            self.session.rollback()
            print(f"Error: {e}")
            raise Exception(f"An error occurred while creating vector: {e}")

        # Refresh the session to get any updated fields (like auto-generated IDs)
        for vector in new_vectors:
            self.session.refresh(vector)

        return new_vectors

    def get_vectors_by_knowledge_id(self, knowledge_id: UUID) -> Sequence[Vector]:
        query = select(Vector).where(Vector.knowledge_id == knowledge_id)
        results = self.session.execute(query)
        return results.scalars().all()

    def similarity_search(
        self,
        query_embedding: List[float],
        brain_id: UUID,
        k: int = 40,
        max_chunk_sum: int = 15000,  # Increased for better context
        similarity_threshold: float = 0.6,  # Minimum similarity threshold
        document_type_filter: str = None,  # Optional document type filter
        **kwargs: Any,
    ) -> Sequence[SimilaritySearchOutput]:
        # Enhanced SQL query with better filtering and ranking
        sql_query = text("""
            WITH ranked_vectors AS (
                SELECT
                    v.id AS vector_id,
                    kb.brain_id AS vector_brain_id,
                    v.knowledge_id AS vector_knowledge_id,
                    v.content AS vector_content,
                    v.metadata AS vector_metadata,
                    v.embedding AS vector_embedding,
                    1 - (v.embedding <=> (:query_embedding)::vector) AS calculated_similarity,
                    (v.metadata->>'chunk_size')::integer AS chunk_size,
                    (v.metadata->>'primary_document_type') AS document_type,
                    (v.metadata->>'filename') AS filename,
                    (v.metadata->>'chunk_type') AS chunk_type,
                    (v.metadata->>'chunk_position') AS chunk_position,
                    -- Enhanced ranking factors
                    CASE 
                        WHEN v.metadata->>'chunk_type' = 'document_start' THEN 1.1
                        WHEN v.metadata->>'chunk_type' = 'single_chunk' THEN 1.2
                        ELSE 1.0
                    END AS position_boost,
                    -- Document type relevance boost
                    CASE 
                        WHEN :document_type_filter IS NULL THEN 1.0
                        WHEN v.metadata->>'primary_document_type' = :document_type_filter THEN 1.3
                        WHEN v.metadata->>'detected_document_types' @> to_jsonb(:document_type_filter::text) THEN 1.2
                        ELSE 0.9
                    END AS type_boost
                FROM
                    vectors v
                INNER JOIN
                    knowledge_brain kb ON v.knowledge_id = kb.knowledge_id
                WHERE
                    kb.brain_id = :p_brain_id
                    AND 1 - (v.embedding <=> (:query_embedding)::vector) >= :similarity_threshold
            ), enhanced_ranking AS (
                SELECT
                    *,
                    (calculated_similarity * position_boost * type_boost) AS final_score
                FROM ranked_vectors
                ORDER BY
                    final_score DESC
            ), filtered_vectors AS (
                SELECT
                    vector_id,
                    vector_brain_id,
                    vector_knowledge_id,
                    vector_content,
                    vector_metadata,
                    vector_embedding,
                    calculated_similarity,
                    final_score,
                    chunk_size,
                    document_type,
                    filename,
                    chunk_type,
                    chunk_position,
                    -- Running total for chunk size limit
                    sum(chunk_size) OVER (ORDER BY final_score DESC) AS running_total,
                    -- Row number for diversity (limit chunks per document)
                    row_number() OVER (PARTITION BY filename ORDER BY final_score DESC) AS doc_rank
                FROM enhanced_ranking
            )
            SELECT
                vector_id AS id,
                vector_brain_id AS brain_id,
                vector_knowledge_id AS knowledge_id,
                vector_content AS content,
                vector_metadata AS metadata,
                vector_embedding AS embedding,
                calculated_similarity AS similarity,
                final_score,
                document_type,
                filename,
                chunk_type,
                chunk_position
            FROM filtered_vectors
            WHERE 
                running_total <= :max_chunk_sum
                AND doc_rank <= 3  -- Limit to top 3 chunks per document for diversity
            ORDER BY final_score DESC
            LIMIT :k
        """)

        params = {
            "query_embedding": query_embedding,
            "p_brain_id": brain_id,
            "k": k,
            "max_chunk_sum": max_chunk_sum,
            "similarity_threshold": similarity_threshold,
            "document_type_filter": document_type_filter,
        }

        result = self.session.execute(sql_query, params=params)
        full_results = result.all()
        
        # Enhanced result formatting with additional metadata
        formated_result = [
            SimilaritySearchOutput(
                id=row.id,
                brain_id=row.brain_id,
                knowledge_id=row.knowledge_id,
                content=row.content,
                metadata_=row.metadata,
                embedding=row.embedding,
                similarity=row.similarity,
                # Add additional quality metrics to metadata
                enhanced_metadata={
                    **row.metadata,
                    "final_score": float(row.final_score),
                    "document_type": row.document_type,
                    "filename": row.filename,
                    "chunk_type": row.chunk_type,
                    "chunk_position": row.chunk_position,
                    "retrieval_quality": "enhanced"
                }
            )
            for row in full_results
        ]
        
        # Log retrieval statistics for monitoring
        logger.info(f"Enhanced similarity search returned {len(formated_result)} chunks "
                   f"from brain {brain_id} with threshold {similarity_threshold}")
        
        return formated_result
