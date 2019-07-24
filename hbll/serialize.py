from typing import Any, Dict, List, Mapping, Optional, Set, Type, Union
from uuid import UUID

from pydantic import BaseModel


# N = NodeTree = often save
# F = Function = initial load


class LinkN(BaseModel):
    node_id: UUID
    output_name: str


class InputN(BaseModel):
    link: LinkN
    value: Optional[Any]


class NodeN(BaseModel):
    type: str
    id: UUID
    settings: Dict[str, Any]
    inputs: Dict[str, InputN]


class NodeTreeN(BaseModel):
    nodes: List[NodeN]


# --------------------------------


class InputOutputF(BaseModel):
    type: str
    params: Dict[str, Any]


class FunctionF(BaseModel):
    name: str
    type: str
    settings: Dict[str, InputOutputF]
    inputs: Dict[str, InputOutputF]
    outputs: Dict[str, InputOutputF]


class ModuleF(BaseModel):
    name: str
    package: str
    version: str
    funcs: List[FunctionF]


class SchemaF(BaseModel):
    modules: List[ModuleF]

