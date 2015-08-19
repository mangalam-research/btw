import os

# This enables loading the code generated from field.ebnf as if it
# were right here.
dirname = os.path.abspath(os.path.dirname(__file__))
__path__.append(os.path.join(dirname, "../build/python/semantic_fields"))
