from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be blank")
        return value


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class EdgeCreate(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)
    latency: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("source", "destination")
    @classmethod
    def clean_node_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Node names must not be blank")
        return value


class EdgeOut(BaseModel):
    id: int
    source: str
    destination: str
    latency: float


class ShortestRouteRequest(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    destination: str = Field(min_length=1, max_length=120)

    @field_validator("source", "destination")
    @classmethod
    def clean_node_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Node names must not be blank")
        return value


class ShortestRouteResponse(BaseModel):
    total_latency: float
    path: list[str]


class RouteHistoryOut(BaseModel):
    id: int
    source: str
    destination: str
    total_latency: float
    path: list[str]
    created_at: datetime
