checks = {
    "pre-commit": ["no_before_commit", "no_non_ascii_filenames",
                   "no_trailing_whitespace",
                   {
                       "name": "python_pep8",
                       "params": {
                           "verbose": True
                       }
                   }
                   ]
}
