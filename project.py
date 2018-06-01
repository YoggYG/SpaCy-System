import sys
import requests
import spacy
import untangle
import itertools


def listExampleQuestions():
    print("Using \"ctrl-Z\" to exit the program does not free the memory of the program instance. "
          "Use \"ctrl-C\" instead.")
    print("Example questions:")
    print("What is the population in India?")
    print("What is the area of Bangladesh?")
    print("Please give me the highest point in the Alps.")
    print("What is the province of Heerenveen?")
    print("What is the country of Bremen?")
    print("Give me the mayor of the Big Apple")
    print("Tell me Brazil's president!")
    print("Who is the king of Canada?")
    print("Who is the president of Germany?")
    print("Give me Sweden's highest point please")


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
        SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".}
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
    results = untangle.parse(result)

    answers = []
    for result in results.sparql.results.children:
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
    result = list(itertools.product(*objectList))
    # print(result)
    return result


def getXOfY(X, Ylist):
    objectList = []
    predicates = getCodesFromString(X, True)
    for Y in Ylist:
        objectList.append(getCodesFromString(Y))

    predicateObjects = getCodesFromString(X)
    predicateObjects.append("")  # add an empty object. This is used to test without the extra line, in case we are not looking for a person.

    # print(predicates)
    # print(predicateObjects)

    # print(objectList)
    objectCombinations = createAllObjectCombinations(objectList)

    for predicateObject in predicateObjects:
        for objectCombination in objectCombinations:
            for predicate in predicates:
                if predicateObject != "":  # person has "position held" an instance of/subset of X
                    extraLines = '''
                    ?item wdt:P39 [wdt:P31|wdt:P279* wd:''' + predicateObject + '''].
                    '''
                else:
                    extraLines = ""  # empty

                answers = getSimpleAnswer(predicate, objectCombination, extraLines)

                if len(answers) > 0:
                    for answer in answers:  # print all answers of this query
                        print(answer)

                    return True  # if the query returned an answer, stop searching

    return False


def conjunctsOfToken(parentToken):
    result = []  # list creation like this is necessary. Otherwise all characters are seen as an item.
    result.append(parentToken.text)
    for token in parentToken.children:
        if token.dep_ == "conj":
            result.extend(conjunctsOfToken(token))

    return result


def standardStrategy(doc, rootIndex):  # give me X of Y / Y's X
    rootToken = doc[rootIndex]
    for XToken in rootToken.children:
        # print('\t'.join((XToken.text, XToken.lemma_, XToken.pos_, XToken.tag_, XToken.dep_, XToken.head.lemma_)))
        if XToken.dep_ in ("nsubj", "attr", "dobj"):  # X is one of the root's children with one of these dependencies
            for YToken in XToken.children:
                if YToken.dep_ in ("poss", "prep"):  # Y is a (grand)child of X
                    Y = []
                    Y.append(YToken.text)
                    if YToken.dep_ == "prep":
                        firstChildIdx = 0
                        for child in YToken.children:
                            if firstChildIdx == 0:
                                firstChildIdx = child.i  # YToken = "of", so the first child is the actual Y

                        YToken = doc[firstChildIdx]
                        Y = conjunctsOfToken(YToken)

                    X = XToken.text
                    # print(Y)

                    if getXOfY(X, Y):  # first check the person strat, then the object strat
                        return True

    return False


def makeSpanSingular(span):
    # May be done in the aliasing. Needs to be done for "anthems" to "anthem", but maybe that's the only exception.
    pass


def createSpans():  # combines noun chunks and entities into a single Token. Does not include the determiner.
    for spanType in range(2):
        spans = []

        if spanType == 0:
            raw_spans = list(doc.ents)
        else:
            raw_spans = list(doc.noun_chunks)

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
            makeSpanSingular(span)
            if span[0].dep_ == "det":  # exclude the first determiner, we don't want it.
                span[1:].merge()
            else:
                span.merge()


def applyAliasing():
    """
    Replaces words found in our JSON with the aliases the solver needs to solve the query.
    :return:
    """
    pass


if __name__ == '__main__':
    listExampleQuestions()
    nlp = spacy.load('en')

    for line in sys.stdin:
        if line.strip() == "":  # empty line cannot be parsed, causes crashes if not skipped
            continue

        needsTimeFilter = False
        year = 0

        applyAliasing()

        doc = nlp(line.strip())
        createSpans()   # ideally this is not done in advance, but dynamically at runtime.
                        # Degree of merges could then depend on the current strategy.

        rootIndex = getIndexOfRoot(doc)

        for token in doc[rootIndex].subtree:
            # print('\t'.join((token.text, token.lemma_, token.pos_, token.tag_, token.dep_, token.head.lemma_, str(token.i))))
            if token.dep_ == "pobj" and token.tag_ == "CD":
                needsTimeFilter = True
                year = token.text

        if needsTimeFilter:
            if standardStrategy(doc, rootIndex):
                continue
            needsTimeFilter = False

        if not standardStrategy(doc, rootIndex):
            print("Yes")  # Default answer.

