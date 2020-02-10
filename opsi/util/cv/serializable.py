from abc import ABC, abstractmethod


class NTSerializable(ABC):
    @abstractmethod
    def nt_serialize(self):
        pass
