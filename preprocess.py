from aliases import Aliases


class PreProcess:
    def __init__(self):
        self.aliases = Aliases()

    def process(self, question):
        self.process_restructuring(question)

    def process_aliases(self, question):
        question.text = self.aliases.parse(question.text)

    def process_restructuring(self, question):
        self.restructure_question(question)

    def restructure_question(self, question):
        unstructured = question.text

        words = question.text.split()

        if words[0] in ("in", "on"):
            for idx in range(len(words)):
                if words[idx] in ("is", "was", "does", "do", "lies", "can"):
                    max_index = len(words)

                    if words[-1] in ("lie?", "live?", "flow?"):
                        max_index -= 1

                    if idx == 2:
                        res = " ".join(words[1: max_index])

                    else:
                        res = words[1] + " is " + " ".join(words[2: idx]) + " of " + " ".join(
                            words[idx + 1: max_index])

                    question.text = res

        self.process_aliases(question)

        if unstructured != question.text:
            self.restructure_question(question)
