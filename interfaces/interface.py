class Interface:
    def connect(self):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    def read(self):
        raise NotImplementedError()
