class Question:
    class TimeFilter:
        def __init__(self, year):
            self.year = year

    def __init__(self, id, text):
        self.id = id
        self.text = text
        self.time_filter = None

    def is_valid(self):
        if self.text == "":
            return False

        return True

    def set_time_filter(self, year):
        self.time_filter = Question.TimeFilter(year)

    def remove_time_filter(self):
        self.time_filter = None
