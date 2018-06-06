import json

from os import listdir
from os.path import isfile, join


class Aliases:
    class Set:
        def __init__(self, property, aliases):
            self.property = property
            self.aliases = aliases

        def parse(self, sentence):
            for alias in self.aliases:
                sentence = sentence.replace(alias, self.property)

            return sentence

    DIRECTORY = "aliases/"

    def __init__(self):
        self.sets = []

        for file in listdir(Aliases.DIRECTORY):
            if isfile(join(Aliases.DIRECTORY, file)):
                with open(join(Aliases.DIRECTORY, file)) as file:
                    self.addFile(file)

    def addFile(self, file):
        data = json.load(file)
        set = Aliases.Set(data["property"], data["aliases"])

        self.sets.append(set)

    def firstLower(self, sentence):
        if len(sentence) == 0:
            return sentence

        return sentence[0].lower() + sentence[1:]

    def parse(self, sentence):
        sentence = self.firstLower(sentence)
        while True:  # Apply the aliasing until no more change (some aliases may depend on others)
            old_sentence = sentence
            for set in self.sets:
                sentence = set.parse(sentence)

            if old_sentence == sentence:
                return sentence
