from numpy import ndarray

from . import _wrappers


class Mat:
    def __init__(self, img: ndarray):
        self.img = img

    @classmethod
    def from_matbw(cls, matbw):
        return cls(_wrappers.matBW_to_mat(matbw.img))

    @property
    def mat(self):
        return self

    @property
    def matBW(self):
        raise TypeError


class MatBW:
    def __init__(self, img: ndarray):
        self.img = img
        self._mat = None

    @property
    def mat(self):
        if self._mat is None:  # TODO: should this be cached? draw on mat in place?
            self._mat = _wrappers.matBW_to_mat(self)
        return self._mat

    @property
    def matBW(self):
        return self
