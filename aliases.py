from os import listdir
from os.path import isfile, join


class Aliases:
    DIRECTORY = "aliases/"

    def __init__(self):
        files = [file for file in listdir(Aliases.DIRECTORY) if isfile(join(Aliases.DIRECTORY, file))]

        print(files)
