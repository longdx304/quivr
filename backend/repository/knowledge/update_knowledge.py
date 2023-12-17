from typing import Optional
from uuid import UUID

from models.knowledge import Knowledge
from models.settings import get_supabase_client
from pydantic import BaseModel


class KnowledgeUpdatableProperties(BaseModel):
    description: Optional[str]


def update_knowledge(
    knowledge_id: UUID, knowledge: KnowledgeUpdatableProperties
) -> Knowledge:
    supabase_client = get_supabase_client()

    response = (
        supabase_client.from_("knowledge")
        .update(knowledge.__dict__)
        .filter("id", "eq", knowledge_id)
        .execute()
    )

    if len(response.data) == 0:
        raise Exception("Error updating knowledge")

    return Knowledge(**response.data[0])
