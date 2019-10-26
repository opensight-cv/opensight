class Unduplicator:
    def __init__(self):
        self.keys = set()

    def add(self, key):
        if key in self.keys:
            return False
        self.keys.add(key)
        return True

    def remove(self, key):
        try:
            self.keys.discard(key)
            return True
        except KeyError:
            pass
        return False
