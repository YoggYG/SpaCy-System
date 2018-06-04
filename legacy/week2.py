import sys
import requests
import untangle


def reportQuery(question, query):
    print(question)

    request = requests.get("https://query.wikidata.org/sparql?query=" + query)
    results = untangle.parse(request.text)

    for result in results.sparql.results.children:
        print(result.binding.literal.cdata)

id = sys.argv[1]

if id == "1":
    reportQuery(
        "What is the capital of Poland?",
        '''
        SELECT ?capitalLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?country wdt:P36 ?capital;
                       rdfs:label "Poland"@en.
        }
        ''')

if id == "2":
    reportQuery(
        "Which countries have Alps?",
        '''
        SELECT ?countryLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?alps wdt:P31 wd:Q46831.
              ?alps rdfs:label "Alps"@en;
                    wdt:P17 ?country.
        }
        ''')

if id == "3":
    reportQuery(
        "Which rivers flow through both Belgium and Germany?",
        '''
        SELECT ?riverLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?river wdt:P31 [rdfs:label "river"@en].

              ?river wdt:P17 [rdfs:label "Germany"@en].
              ?river wdt:P17 [rdfs:label "Belgium"@en].
        }
        ''')

if id == "4":
    reportQuery(
        "Is Turkey part of Europe?",
        '''
        SELECT ?answer WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              OPTIONAL {
                    ?country wdt:P31 [rdfs:label "country"@en];
                             wdt:P30 [rdfs:label "Europe"@en];
                             rdfs:label "Turkey"@en.
                    }
              BIND(IF(BOUND(?country),"Yes","No") as ?answer).
        }
        ''')

if id == "5":
    reportQuery(
        "What is the area of Germany?",
        '''
        SELECT ?area WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?country wdt:P31 [rdfs:label "country"@en];
                       wdt:P2046 ?area;
                       rdfs:label "Germany"@en.
        }
        ''')

if id == "6":
    reportQuery(
        "What are the national anthems of the countries that border Germany and Norway?",
        '''
        SELECT ?anthemLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?country1 wdt:P31 [rdfs:label "country"@en].
              ?country2 wdt:P31 [rdfs:label "country"@en].
              ?country3 wdt:P47 ?country1.
              ?country3 wdt:P47 ?country2.
              ?country3 wdt:P85 ?anthem.
              ?country1 rdfs:label "Germany"@en.
              ?country2 rdfs:label "Norway"@en.
        }
        ''')

if id == "7":
    reportQuery(
        "What was the population of Brazil in 1977?",
        '''
        SELECT ?population WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?country wdt:P31 [rdfs:label "country"@en].
              ?country rdfs:label "Brazil"@en.
              ?country p:P1082 [pq:P585 ?date; ps:P1082 ?population].

              filter(YEAR(?date) = 1977).
        }
        ''')

if id == "8":
    reportQuery(
        "What country is Crimea in?",
        '''
        SELECT ?countryLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?crimea wdt:P17 ?country.
              ?crimea skos:altLabel "Crimea"@en .
        }
        ''')

if id == "9":
    reportQuery(
        "What is the highest mountain in Canada?",
        '''
        SELECT ?pointLabel {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?country wdt:P31 [rdfs:label "country"@en].
              ?country wdt:P610 ?point.
              ?country rdfs:label "Canada"@en.
              ?point wdt:P31 [rdfs:label "mountain"@en].
        }
        ''')

if id == "10":
    reportQuery(
        "Which countries does the river Po flow through?",
        '''
        SELECT ?countryLabel WHERE {
              SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
              ?river wdt:P31 [rdfs:label "river"@en].
              ?river rdfs:label "Po"@en.
              ?river wdt:P17 ?country.
        }
        ''')