import re
from nltk.stem.porter import *
import sys
import math
import os

def find_query(query_str,index,stopwords):
    ''' Given an individual word, extracts alphanumeric, drops stopwords, stems and returns set of postings or empty set'''
    stemmer = PorterStemmer()
    resultwords  = [word for word in re.findall("[a-z0-9]+",query_str.lower()) if word not in stopwords]
    if len(resultwords) == 1:
        query = stemmer.stem(resultwords[0])
        if query in index.keys():
            return index[query][1].keys()
        else:
            return set([])
    else:
        return set([])

def boolean_queries(boolq,index,stopwords):
    ''' Transcribes a user input boolean query into a set expression '''
    boolq = boolq.replace("(", "( ")
    boolq = boolq.replace(")", " )")
    boolq = boolq.split()
    new = []
    for i in boolq:
        if (i == "(") or (i == ")"):
            new.append(i)
        elif (i == "AND"):
            new.append("&")
        elif (i == "OR"):
            new.append("|")
        else:
            new.append("find_query('" + i + "', index, stopwords)")
    return sorted(eval(" ".join(new)), key=int)


def form_condition(phrases):
    ''' Helper function for phrase queries - writes a condition for the loop to find subsequent words '''
    new = []
    for num in range(1,len(phrases)):
        new.append('(val + ' + str(num) + ' in index[phrases[' + str(num) + ']][1][i][1])')
    return "(" + " & ".join(new) + ")"

def phrase_queries(phrase_query,index,stopwords):
    ''' Extracts alphanumeric, removes stopwords and stems and then uses set operations and condition loop to find answers '''
    stemmer = PorterStemmer()
    phrases = phrase_query[1:-1]
    resultwords  = [word for word in re.findall("[a-z0-9]+",phrases.lower()) if word not in stopwords]
    phrases = [stemmer.stem(word) for word in resultwords]
    long_query = " & ".join([ "find_query('" +  phrase + "', index,stopwords)" for phrase in phrases])
    results = []
    set_dict = eval(long_query)
    for i in set_dict:
        for val in index[phrases[0]][1][i][1]:
            if eval(form_condition(phrases)):
                if i not in results:
                    results.append(i)
    return sorted(results, key=int)

def freetext_queries(freetext_query,index,stopwords):
    ''' Rewrites free text query as set operations '''
    stemmer = PorterStemmer()
    resultwords  = [word for word in re.findall("[a-z0-9]+",freetext_query.lower()) if word not in stopwords]
    qs = [stemmer.stem(word) for word in resultwords]
    long_query = " | ".join([ "find_query('" +  query + "', index, stopwords)" for query in qs])
    return sorted(eval(long_query), key=int)

def eval_query(q,index,stopwords):
    ''' Distinguishes query type and calls appropriate function '''
    if len(q.split(" ")) == 1:
        return " ".join(sorted(find_query(q,index,stopwords), key=int))
    if len(q.split(" ")) >  1:
        if (("AND" in q) or ("OR" in q)):
            return " ".join(boolean_queries(q,index,stopwords))
        elif (q[0] == '"' and q[-1] == '"'):
            return " ".join(phrase_queries(q,index,stopwords))
        else:
            return " ".join(freetext_queries(q,index,stopwords))

def scorer(q,index,stopwords):
    stemmer = PorterStemmer()
    resultwords  = [word for word in re.findall("[a-z0-9]+",q.lower()) if word not in stopwords]
    query = [stemmer.stem(word) for word in resultwords]
    if query == []:
        return set([])
    elif (len(query) == 1):
        scores = []
        word = query[0]
        if word in index.keys():
            for doc in eval_query(q, index, stopwords).split(" "):
                scores.append([doc, index[word][0]*index[word][1][doc][0]])
            scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    else:
        vec_query = []
        for word in query:
            if word in index.keys():
                vec_query.append(index[word][0])
            else: vec_query.append(0)
        scores = []
        for doc in eval_query(q, index, stopwords).split(" "):
            vec_doc = []
            for word in query:
                if word in index.keys():
                    if doc in index[word][1].keys():
                        vec_doc.append(index[word][1][doc][0])
                    else:
                        vec_doc.append(0)
                else:
                    vec_doc.append(0)
            scores.append([doc, sum([a*b for (a, b) in zip(vec_query, vec_doc)])
                  /(math.sqrt(sum([a*b for (a, b) in zip(vec_query, vec_query)]))
                    * math.sqrt(sum([a*b for (a, b) in zip(vec_doc, vec_doc)])))])
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

def error_catcher(q,stopwords):
    stemmer = PorterStemmer()
    resultwords = [word for word in re.findall("[a-z0-9]+", q.lower()) if word not in stopwords]
    query_stopwords = [word for word in re.findall("[a-z0-9]+", q.lower()) if word in stopwords]
    query = [stemmer.stem(word) for word in resultwords]
    if query == []:
        if query_stopwords != []:
            return ("ERROR: you entered one or more stopwords! Try again without: " + ", ".join(query_stopwords))
        elif q == "":
            return ("ERROR: your query was empty! Try again.")
        elif '"' in q:
            return ("ERROR: your phrase query was empty! Try again.")
        elif '(' in q or ')' in q:
            return ("ERROR: your boolean query was empty! Try again.")
        else:
            return ("ERROR: your query is NOT well formed! Try again.")
    else:
        return False

def print_sorted(q,index,stopwords):
    if error_catcher(q,stopwords) == False:
        return " ".join([doc[0] for doc in scorer(q,index,stopwords)])
    else:
        return error_catcher(q,stopwords)

def print_titles(q,title_index,index,stopwords):
    if error_catcher(q,stopwords) == False:
        return " ".join([('"' + str(title_index[doc[0]]) + '"') for doc in scorer(q,index,stopwords)])
    else:
        return error_catcher(q,stopwords)

def print_titles_and_scores(q,title_index,index,stopwords):
    if error_catcher(q,stopwords) == False:
        return [('"' + str(title_index[doc[0]]) + '" ' + str(doc[1])) for doc in scorer(q,index,stopwords)]
    else:
        return error_catcher(q,stopwords)

def print_sorted_pr(q,index,stopwords, scores):
    if error_catcher(q,stopwords) == False:
        sortedPageRank = [score for score in scores if score[0] in eval_query(q, index, stopwords).split()]
        return " ".join([doc[0] for doc in sortedPageRank])
    else:
        return error_catcher(q,stopwords)

def print_titles_pr(q,title_index,index,stopwords, scores):
    if error_catcher(q,stopwords) == False:
        sortedPageRank = [score for score in scores if score[0] in eval_query(q, index, stopwords).split()]
        return " ".join([('"' + str(title_index[doc[0]]) + '"') for doc in sortedPageRank])
    else:
        return error_catcher(q,stopwords)

def print_titles_and_scores_pr(q,title_index,index,stopwords, scores):
    if error_catcher(q,stopwords) == False:
        sortedPageRank = [score for score in scores if score[0] in eval_query(q, index, stopwords).split()]
        return [('"' + str(title_index[doc[0]]) + '" ' + str(doc[1])) for doc in sortedPageRank]
    else:
        return error_catcher(q,stopwords)

def main():
    if 'rank' in sys.argv[1]:
        stopwordsFile = sys.argv[2]
        indexFolder = sys.argv[3]
    else:
        stopwordsFile = sys.argv[1]
        indexFolder = sys.argv[2]

    if os.path.isdir(indexFolder) == False:
        print('Error: The option to specify index files was removed in version 3a, please input an index directory instead.')
        sys.exit(1)

    indexFile = indexFolder + 'index.txt'
    titlesFile = indexFolder + 'titles.txt'
    scoresFile = indexFolder + 'scores.dat'

    with open(stopwordsFile) as f:
        content = f.readlines()
    stopwords = [x.strip() for x in content]

    with open(indexFile,"r") as f:
        index = eval(f.read())

    with open(titlesFile,"rb") as f:
        title_index = eval(f.read().decode('utf-8', 'ignore').encode('ascii', 'ignore'))

    with open(scoresFile) as f:
        content = f.readlines()
    scores = [x.strip().split('|') for x in content]

    if '--rank=pagerank' in sys.argv:
        if '-t' in sys.argv:
            while True:
                try:
                    query = input()
                    print(print_titles_pr(query,title_index,index,stopwords,scores))
                except EOFError:
                    break
        elif '-v' in sys.argv:
            while True:
                try:
                    query = input()
                    for line in print_titles_and_scores_pr(query,title_index,index,stopwords,scores):
                        print(line)
                except EOFError:
                    break
        else:
            while True:
                try:
                    query = input()
                    print(print_sorted_pr(query,index,stopwords,scores))
                except EOFError:
                    break
    else:
        if '-t' in sys.argv:
            while True:
                try:
                    query = input()
                    print(print_titles(query,title_index,index,stopwords))
                except EOFError:
                    break
        elif '-v' in sys.argv:
            while True:
                try:
                    query = input()
                    for line in print_titles_and_scores(query,title_index,index,stopwords):
                        print(line)
                except EOFError:
                    break
        else:
            while True:
                try:
                    query = input()
                    print(print_sorted(query,index,stopwords))
                except EOFError:
                    break


if __name__ == '__main__':
    main()