import spacy


class SyntaxParser:
    LANGUAGE = "en"

    def __init__(self):
        self.spacy = spacy.load(SyntaxParser.LANGUAGE)

    def parse(self, question):
        question.set_syntax(self.spacy(question.text))

        SyntaxParser.merge_spans(question.syntax)

    @staticmethod
    def merge_spans(syntax):
        for spanType in range(3):
            spans = []

            if spanType == 0:
                raw_spans = list(syntax.ents)
            elif spanType == 1:
                raw_spans = list(syntax.noun_chunks)
            else:
                raw_spans = SyntaxParser.make_custom_spans(syntax)

            for span in raw_spans:
                changed = False

                for idx in range(len(span)):
                    token = span[idx]
                    if token.dep_ == "poss":  # Do not merge noun chunks with a genitive in it. We need that.
                        changed = True
                        spans.append(span[0: idx + 1])

                        if idx + 2 < len(span):  # exception for the case of "New York's"
                            spans.append(span[idx + 2:])

                        break

                if not changed:
                    spans.append(span)

            for span in spans:
                if span[0].dep_ == "det":  # exclude the first determiner, we don't want it.
                    span[1:].merge()
                else:
                    span.merge()

    @staticmethod
    def make_custom_spans(syntax):
        phrase_definitions = [
            # if more of these phrases have to be defined, a seperate file to store them would be nice.
            "head of state",
            "head of government",
            "kingdom of the netherlands",
            "age of majority",
            "date of birth",
            "country of origin",
            "gdp per capita",
            "place of publication"
        ]
        result = []

        for doc_idx in range(len(syntax)):
            for phrase in phrase_definitions:
                # split the words in the phrase into a list to loop over
                words = phrase.split()

                if doc_idx + len(words) > len(syntax):
                    continue

                match = True

                for word_idx in range(len(words)):
                    if syntax[doc_idx + word_idx].lemma_ != words[word_idx]:
                        match = False
                        break

                if match is True:
                    result.append(syntax[doc_idx: doc_idx + len(words)])

        return result
