class Question:
    class TimeFilter:
        def __init__(self, year):
            self.year = year

    def __init__(self, id, text):
        self.id = id
        self.text = text
        self.time_filter = None
        self.syntax = None
        self.multiple_answers = False
        self.syntax_root = None

    def __str__(self):
        return self.text

    def is_valid(self):
        if self.text == "":
            return False

        return True

    def set_time_filter(self, year):
        self.time_filter = Question.TimeFilter(year)

    def remove_time_filter(self):
        self.time_filter = None

    def set_syntax(self, syntax):
        self.syntax = syntax

    def set_multiple_answers(self):
        self.multiple_answers = True

    def set_syntax_root_index(self, index):
        self.syntax_root = index
