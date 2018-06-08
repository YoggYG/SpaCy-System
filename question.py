class Question:
    def __init__(self, id, text):
        self.id = id
        self.text = text

    def is_valid(self):
        if self.text == "":
            return False

        return True
