from pydantic import BaseModel


class LLMModel(BaseModel):
    """LLM models stored in the database that are allowed to be used by the users.
    Args:
        BaseModel (BaseModel): Pydantic BaseModel
    """

    name: str = "gpt-40-mini"
    price: int = 1
    max_input: int = 10000
    max_output: int = 10000
