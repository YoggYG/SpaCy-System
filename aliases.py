import json

from os import listdir
from os.path import isfile, join


class Aliases:
    class Set:
        def __init__(self, property, aliases):
            self.property = property
            self.aliases = aliases

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
