from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

# N = NodeTree = often save
# F = Function = initial load


# Constant flags, to be False eventually
FUNC_INSTEAD_OF_MODS = True
LINKS_INSTEAD_OF_INPUTS = True


class LinkN(BaseModel):
    id: UUID
    name: str


class InputN(BaseModel):
    link: Optional[LinkN] = None
    value: Optional[Any] = None


class NodeN(BaseModel):
    type: str
    id: UUID
    settings: Dict[str, Any] = {}
    if LINKS_INSTEAD_OF_INPUTS:
        inputs: Dict[str, Optional[LinkN]] = {}
    else:
        inputs: Dict[str, InputN] = {}


class NodeTreeN(BaseModel):
    nodes: List[NodeN] = []


# --------------------------------


class InputOutputF(BaseModel):
    type: str
    params: Dict[str, Any] = {}


class FunctionF(BaseModel):
    name: str
    type: str
    settings: Dict[str, InputOutputF] = {}
    inputs: Dict[str, InputOutputF] = {}
    outputs: Dict[str, InputOutputF] = {}


class ModuleF(BaseModel):
    package: str
    version: str
    funcs: List[FunctionF] = []


class SchemaF(BaseModel):
    if FUNC_INSTEAD_OF_MODS:
        funcs: List[FunctionF] = []
    else:
        modules: List[ModuleF] = []
