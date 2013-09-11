from django.db.models import Q
from django.utils.timezone import utc

import re
import operator
import datetime
import tempfile
import os
import subprocess


class WithTmpFiles(object):
    def __init__(self, input_data=None):
        self._input_data = input_data
        self._tmpinput_path = None
        self._tmpoutput_path = None

    def __enter__(self):
        (tmpinput_file, tmpinput_path) = tempfile.mkstemp(prefix='btwtmp')
        if self._input_data is not None:
            with os.fdopen(tmpinput_file, 'w') as f:
                f.write(self._input_data.encode("utf-8"))

        (tmpoutput_file, tmpoutput_path) = tempfile.mkstemp(prefix='btwtmp')

        self._tmpinput_path = tmpinput_path
        self._tmpoutput_path = tmpoutput_path

        return (tmpinput_file, tmpinput_path, tmpoutput_file, tmpoutput_path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.unlink(self._tmpinput_path)
        os.unlink(self._tmpoutput_path)


def run_saxon(xsl_path, input_data):
    with WithTmpFiles(input_data) as (_, tmpinput_path,
                                      tmpoutput_file, tmpoutput_path):
        subprocess.check_call(["saxon", "-s:" + tmpinput_path, "-xsl:" +
                               xsl_path, "-o:" + tmpoutput_path])
        out = os.fdopen(tmpoutput_file, 'r')
        ret = out.read().decode('utf-8')
        out.close()
        return ret


def run_xsltproc(xsl_path, input_data):
    with WithTmpFiles(input_data) as (_, tmpinput_path,
                                      tmpoutput_file, tmpoutput_path):
        subprocess.check_call(["xsltproc", "-o", tmpoutput_path, xsl_path,
                               tmpinput_path])

        out = os.fdopen(tmpoutput_file, 'r')
        ret = out.read().decode('utf-8')
        out.close()
        return ret


def utcnow():
    """
:returns: The date and time now with the timezone information set
          to UTC. This avoids warnings about naive times.

:rtype: :class:`datetime.datetime`
"""
    return datetime.datetime.utcnow().replace(tzinfo=utc)


# normalize_query and get_query adapted from code on Julien Phalip's
# site.
def normalize_query(query_string,
                    findterms=re.compile(r'"(?:[^"]+)"|(?:\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    '''
Splits the query string in invidual keywords, getting rid of
unecessary spaces and grouping quoted words together.  Example:

>>> normalize_query('  some random  words "with   quotes  " and   spaces')
['some', 'random', 'words', 'with quotes', 'and', 'spaces']
'''
    return [normspace(' ', t.strip()) for t in findterms(query_string)]


def get_query(query_string, search_fields):
    '''
Returns a query, that is a combination of Q objects. That
combination aims to search keywords within a model by testing the
given search fields.
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
