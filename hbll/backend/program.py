from .manager import Manager
from .pipeline_recursive import RecursivePipeline


class Program:
    def __init__(self):
        self.manager = Manager()
        self.pipeline = RecursivePipeline()
