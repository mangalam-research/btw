Feature: Publishing and unpublishing articles.

Scenario: An author publishes an invalid version of an article
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for lemma "foo"
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
When the article with lemma "foo" can be published
And the user searches for lemma "foo"
Then the search results show one entry for "foo"
When the user clicks the button to publish "foo"
Then there is a message indicating that the article was published

Scenario: An author unpublishes an article, but cancels
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the article with lemma "foo" can be published
And the user searches for lemma "foo"
Then the search results show one entry for "foo"
When the user clicks the button to publish "foo"
Then there is a message indicating that the article was published
When the user dismisses the message
And the user clicks the button to unpublish "foo"
Then there is a warning dialog about unpublishing
When the user cancels the dialog
# This would fail if the unpublishing went through.
And the user clicks the button to unpublish "foo"

Scenario: An author unpublishes an article
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the article with lemma "foo" can be published
And the user searches for lemma "foo"
Then the search results show one entry for "foo"
When the user clicks the button to publish "foo"
Then there is a message indicating that the article was published
When the user dismisses the message
And the user clicks the button to unpublish "foo"
Then there is a warning dialog about unpublishing
When the user clicks the dialog button that performs the unpublishing
Then there is a message indicating that the article was unpublished
