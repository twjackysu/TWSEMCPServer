from pydantic import BaseModel, ConfigDict

class TWSEBaseModel(BaseModel):
    """Base model for all TWSE data structures."""
    
    model_config = ConfigDict(
        extra='ignore',  # Ignore unknown fields
        populate_by_name=True,  # Allow populating by field name or alias
    )
