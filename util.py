import re
import operator
from django.db.models import Q

# normalize_query and get_query adapted from code on Julien Phalip's
# site.
def normalize_query(query_string,
                    findterms=re.compile(r'"(?:[^"]+)"|(?:\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of
    unecessary spaces and grouping quoted words together.  Example:
        
    >>> normalize_query('  some random  words "with   quotes  " and   spaces')
    ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    
    '''
    return [normspace(' ', t.strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That
        combination aims to search keywords within a model by testing
        the given search fields.
    '''
    terms = normalize_query(query_string)
    # What this does is create a field_icontains query for each field.
    # Each of these queries are ORed together so that a given term
    # will generate a hit if it appears in ANY of the fields. Then
    # these ORed queries are ANDed together so that ALL terms must be
    # present somewhere.
    return reduce(operator.and_,
                  [reduce(operator.or_, 
                          [Q(**{"%s__icontains" % field_name: term}) 
                           for field_name in search_fields]
                          ) 
                   for term in terms]
                  )

