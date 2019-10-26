class Unduplicator:
    def __init__(self):
        self.keys = []

    def add(self, key):
        if key in self.keys:
            return False
        self.keys.append(key)
        return True

    def remove(self, key):
        if key not in self.keys:
            return False
        self.keys.remove(key)
        return True
