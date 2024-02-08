import dataclasses
import logging
from typing import Callable, Dict, List, Optional, Type

from opsi.manager.manager_schema import Function, ModuleItem
from opsi.manager.types import AnyType, RangeType, Slide

from .schema import FunctionF, InputOutputF, ModuleF, SchemaF

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------


def _rangetype_serialize(type):
    if not isinstance(type, RangeType):
        return None

    return InputOutputF(type="Range", params=type.serialize())


def _slide_serialize(type):
    if not isinstance(type, Slide):
        return None

    return InputOutputF(type="Slide", params=type.serialize())


def _tuple_serialize(type):
    if not isinstance(type, tuple):
        return None

    return InputOutputF(type="Enum", params={"items": type})


_type_name: Dict[Type, str] = {AnyType: "Any"}
# Each item in _abnormal_types takes in a type and returns InputOutputF if the
# parser supports the type, or None if it does not
_abnormal_types: List[Callable[[Type[any]], Optional[InputOutputF]]] = [
    _slide_serialize,
    _rangetype_serialize,
    _tuple_serialize,
]  # add new type parsers here


def get_type(_type: Type) -> InputOutputF:
    if _type in (None, type(None)):
        return None

    if _type in _type_name:
        name = _type_name.get(_type)
        return InputOutputF(type=name)

    for parser in _abnormal_types:
        IO = parser(_type)

        if IO is not None:
            return IO

    return InputOutputF(type=_type.__name__)


def get_field_type(field) -> InputOutputF:
    io = get_type(field.type)
    if field.default and field.default is not dataclasses.MISSING:
        io.params["default"] = field.default
    return io


def get_types(types):
    # there are no instances of an input or output having type None
    return {name: get_type(_type) for name, _type in types.items()}


def get_settings_types(types):
    pruned_types = []
    # if none, just don't show it
    for _type in types:
        if type(_type.type) is not type(None):
            pruned_types.append(_type)
    return {field.name: get_field_type(field) for field in pruned_types}


def _serialize_funcs(funcs: Dict[str, Type[Function]]) -> List[FunctionF]:
    return [
        FunctionF(
            name=func.__name__,
            type=func.type,
            settings=get_settings_types(func.SettingTypes),
            inputs=get_types(func.InputTypes),
            outputs=get_types(func.OutputTypes),
        )
        for func in funcs.values()
    ]


def _serialize_modules(modules: Dict[str, ModuleItem]) -> List[ModuleF]:
    return [
        ModuleF(
            package=mod_package,
            version=mod.info.version,
            funcs=_serialize_funcs(mod.funcs),
        )
        for mod_package, mod in modules.items()
    ]


def export_manager(manager: "Manager") -> SchemaF:
    return SchemaF(modules=_serialize_modules(manager.modules))
