import spacy
import json


class SyntaxParser:
    LANGUAGE = "en"
    CUSTOM_PHRASES = "syntax/customphrases.json"

    def __init__(self):
        self.spacy = spacy.load(SyntaxParser.LANGUAGE)
        self.custom_phrases = SyntaxParser.load_custom_phrases()

    def parse(self, question):
        question.set_syntax(self.spacy(question.text))

        self.merge_spans(question.syntax)

    @staticmethod
    def load_custom_phrases():
        return json.load(open(SyntaxParser.CUSTOM_PHRASES))["phrases"]

    def merge_spans(self, syntax):
        for spanType in range(3):
            spans = []

            if spanType == 0:
                raw_spans = list(syntax.ents)
            elif spanType == 1:
                raw_spans = list(syntax.noun_chunks)
            else:
                raw_spans = self.make_custom_spans(syntax)

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

    def make_custom_spans(self, syntax):
        phrase_definitions = self.custom_phrases
        print(phrase_definitions)
        result = []

        for doc_idx in range(len(syntax)):
            for phrase in phrase_definitions:
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
