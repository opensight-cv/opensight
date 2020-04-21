from typing import Callable, List, Union

try:
    from _pynetworktables._impl.api import NtCoreApi
    from _pynetworktables._impl.constants import NT_UNASSIGNED
    from _pynetworktables._impl.value import Value
    from networktables import NetworkTableEntry, NetworkTables, NetworkTablesInstance

    NT_AVAIL = True
except ImportError:
    NT_AVAIL = False
    NetworkTables = None

# These are the types that are allowed to be stored in NT
# Not the actual types themselves, these are the Python equivalents
NT_TYPES = Union[
    bool,
    int,
    float,
    str,
    bytes,
    bytearray,
    List[bool],
    List[int],
    List[float],
    List[str],
]

_missing = object()


class NetworkDict:
    def __init__(self, table: str, networktable: "NetworkTablesInstance" = None):
        self.networktable = networktable or NetworkTables
        self.api: NtCoreApi = self.networktable._api
        self.path = (  # Has start and end "/"
            self.networktable.PATH_SEPARATOR
            + self._cleanup_path(table)
            + self.networktable.PATH_SEPARATOR
        )

    # Helper methods

    def _cleanup_path(self, path: str):
        return path.strip().strip(self.networktable.PATH_SEPARATOR).strip()

    def _get_path(self, name: str) -> str:
        return self.path + self._cleanup_path(name)

    def _get_entry(self, name: str) -> "Value":  # Returns None if entry does not exist
        if not isinstance(name, str):
            raise TypeError("Key must be type str")

        path = self._get_path(name)

        entry: NetworkTableEntry

        with self.api.storage.m_mutex:
            # _getOrNew does not lock mutex itself; will this cause problems?
            entry = self.api.storage._getOrNew(path)

        value: Value = entry.value

        # Return None if entry does not exist or is unassigned
        return value if (value is not None) and (value.type != NT_UNASSIGNED) else None

    def get_subtable(self, table: str) -> "NetworkDict":
        table = self.path + self._cleanup_path(table)

        return NetworkDict(table, self.networktable)

    # Getters and setters

    def get(self, name: str, default: NT_TYPES = _missing) -> NT_TYPES:
        entry = self._get_entry(name)

        if entry is None:
            if default is not _missing:  # If a default is specified
                return default

            raise KeyError(name)

        return entry.value

    # Only allows you to set value of existing type
    def set_safe(self, name: str, value: NT_TYPES) -> None:
        entry = self._get_entry(name)

        # Calculated using Python type (bool, str, float)
        try:
            create_value_func: Callable[..., Value] = Value.getFactory(value)
        except ValueError as e:  # getFactory raises ValueError when it should be raising TypeError
            raise TypeError(*e.args)

        if entry is not None:
            # Calculated using NT type (NT_BOOLEAN, NT_STRING, NT_DOUBLE)
            if Value.getFactoryByType(entry.type) != create_value_func:
                # The factories don't match, which means the types don't match
                # Do not allow implicit type conversion
                raise TypeError(
                    "Existing type {} does not match: {}".format(
                        entry.type, type(value)
                    )
                )

        # Convert Python type into NT type
        nt_value: Value = create_value_func(value)

        # Returns False on error (type mismatch)
        successful = self.api.setEntryValue(self._get_path(name), nt_value)

        if not successful:
            raise TypeError(
                "Existing type {} does not match: {}".format(entry.type, type(value))
            )

    def set(self, name: str, value: NT_TYPES) -> None:
        # Calculated using Python type (bool, str, float)
        try:
            create_value_func: Callable[..., Value] = Value.getFactory(value)
        except ValueError as e:  # getFactory raises ValueError when it should be raising TypeError
            raise TypeError(*e.args)

        nt_value: Value = create_value_func(value)

        self.api.setEntryTypeValue(self._get_path(name), nt_value)

    @classmethod
    def _delete_table(cls, nttable):
        for key in nttable.getKeys():
            nttable.delete(key)

        for subtable in nttable.getSubTables():
            ntsubtable = nttable.getSubTable(subtable)
            cls._delete_table(ntsubtable)

    # Dangerous: recursive
    def delete_table(self, table):
        table = self.path + self._cleanup_path(table)
        nttable = self.networktable.getTable(table)

        self._delete_table(nttable)

    def delete(self, name: str) -> None:
        entry = self._get_entry(name)

        if entry is None:
            raise KeyError(name)

        self.api.deleteEntry(self._get_path(name))

    def exists(self, name: str) -> bool:
        return self._get_entry(name) is not None

    # Implement dict-like interface

    def __getitem__(self, key) -> NT_TYPES:
        return self.get(key)

    def __setitem__(self, key, value) -> None:
        self.set(key, value)

    def __delitem__(self, key) -> None:
        self.delete(key)

    def __contains__(self, key) -> bool:
        return self.exists(key)


"""
Example usage:

    NetworkTables.initialize()

    nt_dict = NetworkDict("my_table")

    nt_dict["entryB"] = "string"
    try:
        # Attempt to implicitly change type
        nt_dict["entryB"] = False
    except TypeError:
        print("Does not allow override of initial type")

    print(nt_dict["entryB"])

"""
