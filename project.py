import sys
import requests
import untangle
import itertools
import re

from syntaxparser import SyntaxParser
from preprocess import PreProcess
from question import Question


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

    return query + extraLines + '''filter(YEAR(?date) = ''' + question.time_filter.year + ''').''' + endOfQuery()


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
    if question.time_filter:
        query = constructTimeFilterQuery(predicateCode, objectCodes, extraLines)
    else:
        query = constructSimpleQuery(predicateCode, objectCodes, extraLines)

    request = requests.get("https://query.wikidata.org/sparql?query=" + query)

    return extractAnswerListFromResult(request.text)


def createAllObjectCombinations(objectList):
    return list(itertools.product(*objectList))


def writeAndPrintAnswers(answers):
    res = question.id

    if not question.multiple_answers:
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

def isInstanceOf(X, Code):
    objectList = []
    objectList.append(getCodesFromString(X))
    objectCombinations = createAllObjectCombinations(objectList)
    for objectCombination in objectCombinations:
        answers = getSimpleAnswer("P31", objectCombination)

        if areValid(answers):
            for a in answers:
                if a == Code:
                    return True
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

    return query + extraLines + '''filter(YEAR(?date) = ''' + question.time_filter.year + ''').''' + endOfQuery()


def constructCompoundQuery(predicateCode, compoundPredicateCode, objectCodes, extraLines):
    query = beginningOfQuery()
    for objectCode in objectCodes:
        query += makeCompoundLine(compoundPredicateCode, objectCode)  # Y of Z

    query += makeCompoundLine(predicateCode)  # X of temp

    return query + extraLines + endOfQuery()


def getCompoundAnswer(predicateCode, compoundPredicateCode, objectCodes, extraLines=""):
    if question.time_filter:
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
        if XToken.dep_ in ("nsubj", "attr", "dobj", "pobj", "nsubjpass"):
            X = XToken.text
            for YToken in rootToken.subtree:
                if YToken.dep_ in ("nsubj", "attr", "dobj", "pobj", "nsubjpass"):
                    if YToken.i == XToken.i:
                        continue

                    if YToken.head.head.i == XToken.i:  # same as default strategy
                        continue

                    Y = conjunctsOfToken(YToken)

                    if len(Y) == 0:
                        Y.append(YToken.text)

                    if getXOfY(X, Y):
                        return True

    return False


def getCorrectChildToken(doc, token):
    if token.tag_ == "CD":
        return None

    if token.dep_ == "prep":
        firstChildIdx = 0
        for child in token.children:
            for grandChild in child.children:
                if grandChild.tag_ in ("WP", "WDT"):
                    return None

            if firstChildIdx == 0 and child.tag_ != "CD":
                firstChildIdx = child.i

        if firstChildIdx == 0:  # No valid child
            return None

        token = doc[firstChildIdx]

    return token


def standardStrategy(doc, rootIndex):  # give me X of Y / Y's X
    rootToken = doc[rootIndex]
    for XToken in rootToken.subtree:
        # print('\t'.join((XToken.text, XToken.lemma_, XToken.pos_, XToken.tag_, XToken.dep_, XToken.head.lemma_)))
        if XToken.dep_ in ("nsubj", "attr", "dobj"):  # X is one of the root's children with one of these dependencies
            X = XToken.text

            for YToken in XToken.children:
                if YToken.dep_ in ("poss", "prep"):  # Y is a (grand)child of X
                    YToken = getCorrectChildToken(doc, YToken)
                    if YToken is None:
                        continue

                    Y = conjunctsOfToken(YToken)

                    for ZToken in YToken.children:
                        if ZToken.dep_ in ("poss", "prep"):
                            ZToken = getCorrectChildToken(doc, ZToken)
                            if ZToken is None:
                                continue

                            Z = conjunctsOfToken(ZToken)

                            if getXofYofZ(X, Y, Z):
                                return True

                    if getXOfY(X, Y):  # first check the person strat, then the object strat
                        return True

    return False

def earthStrategy(doc, rootIndex):  # give me X of "the earth" (in order to answer, "what is the tallest mountain?")
    rootToken = doc[rootIndex]
    for XToken in rootToken.subtree:
        # print('\t'.join((XToken.text, XToken.lemma_, XToken.pos_, XToken.tag_, XToken.dep_, XToken.head.lemma_)))
        if XToken.dep_ in ("nsubj", "attr", "dobj"):  # X is one of the root's children with one of these dependencies
            X = XToken.text

            Y = ["the earth"]

            if getXOfY(X, Y):
                 return True

    return False

def riverStrategy(doc, rootIndex):  # X verb Y
    rootToken = doc[rootIndex]
    for XToken in rootToken.subtree:
        if XToken.lemma_ in ("from", "origin", "start", "originate"):
            for YToken in rootToken.subtree:
                if YToken.dep_ in ("nsubj", "attr", "dobj", "pobj", "nsubjpass"):
                    if isInstanceOf(YToken.lemma_, "river"):
                        #print(YToken.lemma_)
                        if getXOfY("origin of the watercourse", [YToken.lemma_]):
                            return True
                        if getXOfY("tributary", [YToken.lemma_]):
                            return True
    return False

def binarysparql(entity, property):
    sparqlurl = 'https://query.wikidata.org/sparql'
    query = 'SELECT * WHERE { wd:'+entity+' wdt:'+property+' ?answer. ?answer rdfs:label ?text}'
    data = requests.post(sparqlurl, params={'query': query, 'format': 'json'}).json()
    answers = []
    for item in data['results']['bindings']:
        if item['text']['xml:lang'] == 'en':
            answers.append(item)
    return answers

def yesNoQuestions(line):
    print("YES NO")
    wdapi = 'https://www.wikidata.org/w/api.php'
    wdparams = {'action': 'wbsearchentities', 'language': 'en', 'format': 'json'}
    m = re.search('(?:Is |is ) ?(.*) (?:the |a |an) ?(.*) of (?:the |a |an )?(.*)\?', line) #Is X the Y of Z?
    n = re.search('(?:Is |is ) ?(.*) (?:a |an ) ?(.*)\?', line) #Is Australia a continent?
    o = re.search('(?:Is |is ) ?(.*) ?(.*) (?:the |a |an )?(.*)\?', line) #Is X Y Y?
    if m is not None:                                        # Failsafe for when malformed queries occur
        entity = m.group(1)
        property = m.group(2)
        posedAnswer = m.group(3)
        #print("1", "e", entity, "p", property, "a", posedAnswer)
        wdparams['search'] = entity
        json = requests.get(wdapi, wdparams).json()
        for result in json['search']:
            entity_id = result['id']
            wdparams['search'] = property
            wdparams['type'] = 'property'
            json = requests.get(wdapi, wdparams).json()
            for result in json['search']:
                property_id = result['id']
                for answers in binarysparql(entity_id, property_id):
                    if posedAnswer.lower() == answers['text']['value'].lower():
                        print('Yes')
                        return True
    elif n is not None: 
        entity = n.group(1)
        posedAnswer = n.group(2)
        #print("2", entity, 'is instance of' , posedAnswer)
        wdparams['search'] = entity
        json = requests.get(wdapi, wdparams).json()
        for result in json['search']:
            entity_id = result['id']
            property_id = 'P31'
            for answers in binarysparql(entity_id, property_id):
                if posedAnswer.lower() == answers['text']['value'].lower():
                    print('Yes')
                    return True 
    else:
        return False
    print('No')
    return True

if __name__ == '__main__':
    printInstructions()
    answerFile = "answers.txt"

    pre_process = PreProcess()
    syntax_parser = SyntaxParser()

    with open(answerFile, "w") as file:
        file.write("")

    for line in sys.stdin:
        if line.strip() == "":  # empty line cannot be parsed, causes crashes if not skipped
            continue

        lines = line.split('\t')

        if not lines:
            continue

        if len(lines) == 1:  # solely for testing, so that we don't have to use official format
            question = Question("", lines[0].strip())
        else:
            question = Question(lines[0], lines[1].strip())

        if not question.is_valid():
            continue

        pre_process.process(question)
        print(question)

        syntax_parser.parse(question)

        for token in question.syntax[question.syntax_root].subtree:
            print('\t'.join((token.text, token.lemma_, token.pos_, token.tag_, token.dep_, token.head.lemma_, str(token.i))))
            if token.dep_ == "pobj" and token.tag_ == "CD" and not question.time_filter:  # save the first of multiple years
                question.set_time_filter(token.text)

        if question.time_filter:
            if standardStrategy(question.syntax, question.syntax_root):
                continue

            question.remove_time_filter()

        if question.text.split(" ", 1)[0] == "is": #check if the first word is is
            if yesNoQuestions(question.text):       #perform yes/no function
                continue

        if standardStrategy(question.syntax, question.syntax_root):
            continue

        print("Trying subject/object strategy next")
        if subjectObjectStrategy(question.syntax, question.syntax_root):
            continue

        print("Trying earth strategy next")
        if earthStrategy(question.syntax, question.syntax_root):
            continue

        print("Trying river strategy next")
        if riverStrategy(question.syntax, question.syntax_root):
            continue

        print("Guessing")

        with open(answerFile, "a+") as file:
            file.write(question.id + "\tYes\n")  # Default answer.
        print(question.id + "\tYes")  # Default answer.
