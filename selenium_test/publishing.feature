Feature: Publishing and unpublishing articles.

Scenario: An author publishes an invalid version of an article
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for headword "foo"
Then the search results show one entry for "foo"
When the user clicks the button to publish "foo"
Then there is a message indicating failure to publish

# Since the schema changes from time to time, keeping a valid version
# of an article in the database is expensive. We use a step that marks
# the article as valid, this lie will be undone for the next scenario
# so there's no leak here.
Scenario: An author publishes a valid version of an article
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the article with headword "foo" can be published
And the user searches for headword "foo"
Then the search results show one entry for "foo"
When the user clicks the button to publish "foo"
Then there is a message indicating that the article was published
