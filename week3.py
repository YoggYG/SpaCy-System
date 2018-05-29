import sys
import requests
import untangle
import re

#P1696: inverse of (for properties) eg. capital is inverse of capital of


def listExampleQuestions():
    print("Example questions:")
    print("1. What is the population of India?")
    print("2. What is the area of Bangladesh?")
    print("3. What is the province of Heerenveen?")
    print("4. What is the country of Bremen?")
    print("5. What is the highest point of the Alps?")
    print("6. What is the country of the cape of good hope?")
    print("7. Who is the king of Canada?")
    print("8. Who is the president of Germany?")
    print("9. Who is the mayor of the big apple?")
    print("10. Who is the head of state of the kingdom of the Netherlands?")


def getCodesFromString(word, isProperty=False):
    url = 'https://www.wikidata.org/w/api.php'
    params = {
        'action': 'wbsearchentities',
        'language': 'en',
        'format': 'json'
    }

    if isProperty:
        params['type'] = 'property'

    params['search'] = word
    json = requests.get(url, params).json()
    codes = []
    for result in json['search']:
        codes.append("{}".format(result['id']))

    return codes


def getSimpleAnswer(predicateCode, objectCode, extraLines = ""):
    query = '''
    SELECT ?itemLabel WHERE {
        SERVICE wikibase:label {bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".}
        wd:''' + objectCode + ''' wdt:''' + predicateCode + ''' ?item.''' + extraLines + '''
    }
    '''
    request = requests.get("https://query.wikidata.org/sparql?query=" + query)
    results = untangle.parse(request.text)

    answers = []

    for result in results.sparql.results.children:
        answers.append(result.binding.literal.cdata)

    return answers


def personAPIStrategy(xOfY):
    hasAnswer = False
    for ofMatch in re.finditer(r'(\sof\s)', xOfY):
        X = xOfY[:ofMatch.start()]
        Y = xOfY[ofMatch.end():]
        matchY = re.match(r'^(?:T|t)he\s(?P<Y>.+)$', Y)
        if matchY is not None:
            Y = matchY.group('Y')

        predicates = getCodesFromString(X, True)
        predicateObjects = getCodesFromString(X)
        objects = getCodesFromString(Y)
        for predicate in predicates:
            for object in objects:
                for predicateObject in predicateObjects:
                    extraLines = '''
                    ?item wdt:P39 [wdt:P31|wdt:P279* wd:''' + predicateObject + '''].
                    '''
                    answers = getSimpleAnswer(predicate, object, extraLines)
                    for answer in answers:
                        hasAnswer = True
                        print(answer)
                    if hasAnswer:
                        return True
    return False


def standardAPIStrategy(xOfY):
    hasAnswer = False
    for ofMatch in re.finditer(r'(\sof\s)', xOfY):
        X = xOfY[:ofMatch.start()]
        Y = xOfY[ofMatch.end():]
        matchY = re.match(r'^(?:T|t)he\s(?P<Y>.+)$', Y)
        if matchY is not None:
            Y = matchY.group('Y')

        predicates = getCodesFromString(X, True)
        objects = getCodesFromString(Y)
        for predicate in predicates:
            for object in objects:
                answers = getSimpleAnswer(predicate, object)
                for answer in answers:
                    hasAnswer = True
                    print(answer)
                if hasAnswer:
                    return True
    return False


if __name__ == '__main__':
    listExampleQuestions()

    for line in sys.stdin:
        foundAnswer = False
        line = line.rstrip()

        match = re.match(r'^(?:W|w)ho\sis\sthe\s(?P<xOfY>.+?)\??$', line)
        if match is not None:
            xOfY = match.group('xOfY')
            if personAPIStrategy(xOfY) or standardAPIStrategy(xOfY):
                continue

        match = re.match(r'(?:W|w)hat\sis\sthe\s(?P<xOfY>.+?)\??$', line)
        if match is not None:
            xOfY = match.group('xOfY')
        else:
            xOfY = line

        foundAnswer = standardAPIStrategy(xOfY)
        if not foundAnswer:
            print("could not find an answer")
