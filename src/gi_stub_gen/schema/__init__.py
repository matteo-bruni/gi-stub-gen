from pydantic import BaseModel, ConfigDict

__all__ = [
    "BaseSchema",
]


class BaseSchema(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

    @property
    def debug(self):
        """
        Debug info of the schema
        """
        return f"[DEBUG]\n{self.model_dump_json(indent=2)}"
