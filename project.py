import sys
import requests
import spacy
import untangle
import itertools

from aliases import Aliases


aliases = Aliases()


def printInstructions():
    print("Using \"ctrl-Z\" to exit the program does not free the memory of the program instance. "
          "Use \"ctrl-C\" instead.")


def getCodesFromString(word, isProperty=False):
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbsearchentities',
        'language': 'en',
        'format': 'json'
    }

    if isProperty:  # returns property codes "Pxx"
        params['type'] = 'property'

    params['search'] = word
    json = requests.get(url, params).json()

    codes = []
    for result in json['search']:
        codes.append("{}".format(result['id']))

    return codes


def beginningOfQuery():
    return '''
    SELECT ?itemLabel WHERE {
        SERVICE wikibase:label {bd:serviceParam wikibase:language "en".}
    '''


def endOfQuery():
    return '''
    }
    '''


def makeSimpleLine(predicateCode, objectCode):
    return '''
    wd:''' + objectCode + ''' wdt:''' + predicateCode + ''' ?item.
    '''


def constructSimpleQuery(predicateCode, objectCodes, extraLines=""):
    query = beginningOfQuery()
    for objectCode in objectCodes:
        query += makeSimpleLine(predicateCode, objectCode)

    return query + extraLines + endOfQuery()


def makeTimeFilterLine(predicateCode, objectCode):
    return '''
    wd:''' + objectCode + ''' p:''' + predicateCode + ''' [pq:P585 ?date; ps:''' + predicateCode + ''' ?item].
    '''


def constructTimeFilterQuery(predicateCode, objectCodes, extraLines=""):
    query = beginningOfQuery()
    for objectCode in objectCodes:
        query += makeTimeFilterLine(predicateCode, objectCode)

    return query + extraLines + '''filter(YEAR(?date) = ''' + year + ''').''' + endOfQuery()


def extractAnswerListFromResult(result):
    if result.split()[0] == "SPARQL-QUERY:":
        print("Query Timeout Exception Caught.")
        return []

    results = untangle.parse(result)

    answers = []
    for result in results.sparql.results.children:
        if result.binding.literal["xml:lang"] is None:
            if result.binding.literal.cdata[0] == 'Q':
                continue

        if result.binding.literal.cdata in answers:
            continue

        answers.append(result.binding.literal.cdata)

    return answers


def getSimpleAnswer(predicateCode, objectCodes, extraLines=""):
    if needsTimeFilter:
        query = constructTimeFilterQuery(predicateCode, objectCodes, extraLines)
    else:
        query = constructSimpleQuery(predicateCode, objectCodes, extraLines)

    request = requests.get("https://query.wikidata.org/sparql?query=" + query)

    return extractAnswerListFromResult(request.text)


def getIndexOfRoot(doc):
    for token in doc:
        if token.dep_ == "ROOT":
            return token.i


def createAllObjectCombinations(objectList):
    return list(itertools.product(*objectList))


def writeAndPrintAnswers(answers):
    res = questionID

    if answerAmount is False:
        for answer in answers:  # print all answers of this query
            res += "\t" + answer
    else:
        res += "\t" + str(len(answers))

    with open(answerFile, "a+") as file:
        file.write(res + "\n")

    print(res)


def areValid(answers):
    if len(answers) > 0:
        return True

    return False


def getXOfY(X, YList):
    objectList = []
    predicates = getCodesFromString(X, True)
    for Y in YList:
        objectList.append(getCodesFromString(Y))

    predicateObjects = definePredicateObjectLines(getCodesFromString(X))

    # print(predicates)
    # print(predicateObjects)
    # print(objectList)

    objectCombinations = createAllObjectCombinations(objectList)

    for predicateObject in predicateObjects:
        for objectCombination in objectCombinations:
            for predicate in predicates:
                extraLines = predicateObject

                answers = getSimpleAnswer(predicate, objectCombination, extraLines)

                if areValid(answers):
                    writeAndPrintAnswers(answers)

                    return True  # if the query returned an answer, stop searching

    return False


def makeTimeFilterCompoundLine(predicateCode):
    return '''
    ?temp p:''' + predicateCode + ''' [pq:P585 ?date; ps:''' + predicateCode + ''' ?item].
    '''


def makeCompoundLine(predicateCode, objectCode=None):
    if objectCode is None:
        return '''
        ?temp wdt:''' + predicateCode + ''' ?item.
        '''
    else:
        return '''
        wd:''' + objectCode + ''' wdt:''' + predicateCode + ''' ?temp.
        '''


def constructTimeFilterCompoundQuery(predicateCode, compoundPredicateCode, objectCodes, extraLines):
    query = beginningOfQuery()
    for objectCode in objectCodes:
        query += makeCompoundLine(compoundPredicateCode, objectCode)

    query += makeTimeFilterCompoundLine(predicateCode)

    return query + extraLines + '''filter(YEAR(?date) = ''' + year + ''').''' + endOfQuery()


def constructCompoundQuery(predicateCode, compoundPredicateCode, objectCodes, extraLines):
    query = beginningOfQuery()
    for objectCode in objectCodes:
        query += makeCompoundLine(compoundPredicateCode, objectCode)  # Y of Z

    query += makeCompoundLine(predicateCode)  # X of temp

    return query + extraLines + endOfQuery()


def getCompoundAnswer(predicateCode, compoundPredicateCode, objectCodes, extraLines=""):
    if needsTimeFilter:
        query = constructTimeFilterCompoundQuery(predicateCode, compoundPredicateCode, objectCodes, extraLines)
    else:
        query = constructCompoundQuery(predicateCode, compoundPredicateCode, objectCodes, extraLines)

    request = requests.get("https://query.wikidata.org/sparql?query=" + query)

    return extractAnswerListFromResult(request.text)


def definePredicateObjectLines(objects, compound=False):
    if compound:
        name = "?temp"
    else:
        name = "?item"

    res = []
    for object in objects:
        line = '''
        ''' + name + ''' wdt:P39|wdt:P31* [wdt:P31|wdt:P279* wd:''' + object + '''].
        '''
        res.append(line)

    res.append("\n")
    return res


def getXofYofZ(X, YList, ZList):  # compound questions (only one level)
    if len(YList) != 1:
        print("YList is length " + str(len(YList)))

    predicates = getCodesFromString(X, True)
    predicateObjects = definePredicateObjectLines(getCodesFromString(X))

    Y = YList[0]

    compoundPredicates = getCodesFromString(Y, True)
    compoundPredicateObjects = definePredicateObjectLines(getCodesFromString(Y), True)

    objectList = []

    for Z in ZList:
        objectList.append(getCodesFromString(Z))

    # print(predicates)
    # print(predicateObjects)
    # print(objectList)

    objectCombinations = createAllObjectCombinations(objectList)

    for predicateObject in predicateObjects:
        for compoundPredicateObject in compoundPredicateObjects:
            for objectCombination in objectCombinations:
                for predicate in predicates:
                    for compoundPredicate in compoundPredicates:
                        extraLines = predicateObject + compoundPredicateObject

                        answers = getCompoundAnswer(predicate, compoundPredicate, objectCombination, extraLines)

                        if areValid(answers):
                            writeAndPrintAnswers(answers)

                            return True  # if the query returned an answer, stop searching

    return False


def conjunctsOfToken(token):
    result = []  # list creation like this is necessary. Otherwise all characters are seen as an item.
    if len(list(token.children)) == 0:
        for siblingToken in token.head.children:
            if siblingToken.dep_ == "punct":  # Do not allow conjunctions with a comma between the last two nouns.
                return result

    result.append(token.text)
    for childToken in token.children:
        if childToken.dep_ == "conj":
            result.extend(conjunctsOfToken(childToken))

    return result


def subjectObjectStrategy(doc, rootIndex):  # X verb Y
    rootToken = doc[rootIndex]
    for XToken in rootToken.subtree:
        if XToken.dep_ in ("nsubj", "attr", "dobj", "pobj"):
            for YToken in rootToken.subtree:
                if YToken.dep_ in ("nsubj", "attr", "dobj"):
                    if YToken.i == XToken.i:
                        continue

                    X = XToken.text
                    Y = conjunctsOfToken(YToken)

                    if len(Y) == 0:
                    	Y.append(YToken.text)

                    if getXOfY(X, Y):
                        return True

    return False


def standardStrategy(doc, rootIndex):  # give me X of Y / Y's X
    rootToken = doc[rootIndex]
    for XToken in rootToken.subtree:
        # print('\t'.join((XToken.text, XToken.lemma_, XToken.pos_, XToken.tag_, XToken.dep_, XToken.head.lemma_)))
        if XToken.dep_ in ("nsubj", "attr", "dobj"):  # X is one of the root's children with one of these dependencies
            for YToken in XToken.children:
                if YToken.dep_ in ("poss", "prep"):  # Y is a (grand)child of X
                    Y = []
                    Y.append(YToken.text)
                    if YToken.dep_ == "prep":
                        firstChildIdx = 0
                        for child in YToken.children:
                            badChild = False
                            for grandChild in child.children:
                                if grandChild.tag_ in ("WP", "WDT"):
                                    firstChildIdx = 0
                                    badChild = True
                                    break

                            if badChild:
                                break

                            if firstChildIdx == 0:
                                firstChildIdx = child.i  # YToken = "of", so the first child is the actual Y

                        if firstChildIdx == 0:
                            continue

                        YToken = doc[firstChildIdx]
                        Y = conjunctsOfToken(YToken)

                    X = XToken.text

                    print(X)
                    print(Y)

                    for ZToken in YToken.children:
                        if ZToken.dep_ in ("poss", "prep"):
                            Z = []
                            if ZToken.tag_ == "CD":
                                continue
                            Z.append(ZToken.text)
                            if ZToken.dep_ == "prep":
                                firstChildIdx = 0
                                for child in ZToken.children:
                                    badChild = False
                                    for grandChild in child.children:
                                        if grandChild.tag_ in ("WP", "WDT"):
                                            firstChildIdx = 0
                                            badChild = True
                                            break

                                    if badChild:
                                        break
                                    if firstChildIdx == 0 and child.tag_ != "CD":
                                        firstChildIdx = child.i

                                if firstChildIdx == 0:  # only second child is a year, so no compound question.
                                    continue

                                ZToken = doc[firstChildIdx]
                                Z = conjunctsOfToken(ZToken)

                            if getXofYofZ(X, Y, Z):
                                return True

                    if getXOfY(X, Y):  # first check the person strat, then the object strat
                        return True

    return False


def makeCustomSpans():
    phraseDefinitions = [  # if more of these phrases have to be defined, a seperate file to store them would be nice.
        "head of state",
        "head of government",
        "kingdom of the netherlands",
        "age of majority",
        "date of birth",
        "country of origin",
        "gdp per capita",
        "place of publication"
    ]
    res = []

    for doc_idx in range(len(doc)):
        for phrase in phraseDefinitions:
            wordList = phrase.split()  # split the words in the phrase into a list to loop over
            if doc_idx + len(wordList) > len(doc):
                continue

            match = True
            for word_idx in range(len(wordList)):
                if doc[doc_idx + word_idx].lemma_ != wordList[word_idx]:
                    match = False
                    break

            if match is True:
                res.append(doc[doc_idx: doc_idx + len(wordList)])

    return res


def mergeSpans():  # combines noun chunks and entities into a single Token. Does not include the determiner.
    for spanType in range(3):
        spans = []

        if spanType == 0:
            raw_spans = list(doc.ents)
        elif spanType == 1:
            raw_spans = list(doc.noun_chunks)
        else:
            raw_spans = makeCustomSpans()

        # for span in raw_spans:
        #     print(span)

        for span in raw_spans:
            changed = False
            for idx in range(len(span)):
                token = span[idx]
                if token.dep_ == "poss":  # Do not merge noun chunks with a genitive in it. We need that.
                    changed = True
                    # print(span[0: idx + 1])
                    # print(span[idx + 2: len(span)])
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


def setAnswerAmount():
    phraseDefinitions = [
        "how many"
    ]

    for doc_idx in range(len(doc)):
        for phrase in phraseDefinitions:
            wordList = phrase.split()  # split the words in the phrase into a list to loop over
            if doc_idx + len(wordList) > len(doc):
                continue

            match = True
            for word_idx in range(len(wordList)):
                if doc[doc_idx + word_idx].lemma_ != wordList[word_idx]:
                    match = False
                    break

            if match is True:
                return True

    return False


def restructureSentence(line):
    wordList = line.split()
    if wordList[0] in ("in", "on"):
        for idx in range(len(wordList)):
            if wordList[idx] in ("is", "was", "does", "do", "lies", "can"):
                maxIdx = len(wordList)
                if wordList[-1] in ("lie?", "live?", "flow?"):
                    maxIdx -= 1
                res = wordList[1] + " is " + " ".join(wordList[2: idx]) + " of " + " ".join(wordList[idx + 1: maxIdx])
                return res

    return line


if __name__ == '__main__':
    printInstructions()
    nlp = spacy.load('en')
    answerFile = "answers.txt"

    with open(answerFile, "w") as file:
        file.write("")

    for line in sys.stdin:
        if line.strip() == "":  # empty line cannot be parsed, causes crashes if not skipped
            continue

        lineList = line.split('\t')

        if len(lineList) < 1:
            continue

        if len(lineList) == 1:  # solely for testing, so that we don't have to use official format
            questionID = ""
            line = aliases.parse(lineList[0].strip())
        else:
            questionID = lineList[0]
            line = aliases.parse(lineList[1].strip())

        if line == "":  # Double check.
            continue

        while True:
            oldLine = line
            line = restructureSentence(line)
            if oldLine == line:
                break

            line = aliases.parse(line)

        print(line)
        
        needsTimeFilter = False
        year = 0

        doc = nlp(line)
        mergeSpans()   # ideally this is not done in advance, but dynamically at runtime.
                        # Degree of merges could then depend on the current strategy.

        answerAmount = setAnswerAmount()  # set to true by checking for "how many"

        rootIndex = getIndexOfRoot(doc)

        for token in doc[rootIndex].subtree:
            print('\t'.join((token.text, token.lemma_, token.pos_, token.tag_, token.dep_, token.head.lemma_, str(token.i))))
            if token.dep_ == "pobj" and token.tag_ == "CD" and not needsTimeFilter:  # save the first of multiple years
                needsTimeFilter = True
                year = token.text

        if needsTimeFilter:
            if standardStrategy(doc, rootIndex):
                continue
            needsTimeFilter = False

        if standardStrategy(doc, rootIndex):
            continue
        
        print("Trying subject/object strategy next")
        if subjectObjectStrategy(doc, rootIndex):
            continue

        with open(answerFile, "a+") as file:
            file.write(questionID + "\tYes\n")  # Default answer.
        print(questionID + "\tYes")  # Default answer.
