import sys
import requests
import spacy
import untangle


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


def constructSimpleQuery(predicateCode, objectCode, extraLines=""):
    return '''
        SELECT ?itemLabel WHERE {
            SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".}
            wd:''' + objectCode + ''' wdt:''' + predicateCode + ''' ?item.''' + extraLines + '''
        }
        '''


def extractAnswerListFromResult(result):
    results = untangle.parse(result)

    answers = []
    for result in results.sparql.results.children:
        answers.append(result.binding.literal.cdata)

    return answers


def getSimpleAnswer(predicateCode, objectCode, extraLines=""):
    query = constructSimpleQuery(predicateCode, objectCode, extraLines)

    request = requests.get("https://query.wikidata.org/sparql?query=" + query)

    return extractAnswerListFromResult(request.text)


def getIndexOfRoot(doc):
    for token in doc:
        if token.dep_ == "ROOT":
            return token.i


def getXOfY(X, Y, person=False):
    predicates = getCodesFromString(X, True)
    objects = getCodesFromString(Y)

    if person:
        predicateObjects = getCodesFromString(X)
    else:
        predicateObjects = ["No person here"]  # there needs to be 1 item in the predicateObjects list for the loop

    for predicate in predicates:
        for object in objects:
            for predicateObject in predicateObjects:
                if person:  # person has "position held" an instance of/subset of X
                    extraLines = '''
                    ?item wdt:P39 [wdt:P31|wdt:P279* wd:''' + predicateObject + '''].
                    '''
                else:
                    extraLines = ""  # empty, technically not necessary. Same as default argument of function

                answers = getSimpleAnswer(predicate, object, extraLines)
                hasAnswer = False
                for answer in answers:  # print all answers of this query
                    hasAnswer = True
                    print(answer)

                if hasAnswer:
                    return True  # if the query returned an answer, stop searching

    return False


def standardStrategy(doc, rootIndex):  # give me X of Y
    rootToken = doc[rootIndex]
    for XToken in rootToken.children:
        # print('\t'.join((XToken.text, XToken.lemma_, XToken.pos_, XToken.tag_, XToken.dep_, XToken.head.lemma_)))
        if XToken.dep_ in ("nsubj", "attr", "dobj"):
            for YToken in XToken.children:
                if YToken.dep_ in ("poss", "prep"):
                    if YToken.dep_ == "prep":
                        YToken = YToken.right_edge  # YToken = "of", so the right edge is the actual Y

                    Y = YToken.text
                    X = XToken.text

                    if getXOfY(X, Y, True) or getXOfY(X, Y):
                        return True

    return False


def createSpans():
    raw_spans = list(doc.ents) + list(doc.noun_chunks)
    spans = []
    # for span in raw_spans:
    #     print(span)
    for span in raw_spans:
        changed = False
        for idx in range(len(span)):
            token = span[idx]
            if token.dep_ == "poss":
                changed = True
                # print(span[0: idx + 1])
                # print(span[idx + 2: len(span)])
                spans.append(span[0: idx + 1])

                if idx + 2 < len(span):  # exception for the case of "New York's"
                    spans.append(span[idx + 2: len(span)])
                break

        if not changed:
            spans.append(span)

    for span in spans:
        if span[0].dep_ in ("det"):
            span[1: len(span)].merge()
        else:
            span.merge()


if __name__ == '__main__':
    listExampleQuestions()
    nlp = spacy.load('en')

    for line in sys.stdin:
        foundAnswer = False
        doc = nlp(line.strip())
        createSpans()

        rootIndex = getIndexOfRoot(doc)

        if rootIndex is None:  # stops crash when an empty line is entered
            continue

        # for token in doc[rootIndex].subtree:
        #     print('\t'.join((token.text, token.lemma_, token.pos_, token.tag_, token.dep_, token.head.lemma_)))

        if not standardStrategy(doc, rootIndex):
            print("No solution found, try rephrasing your query")

