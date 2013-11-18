Feature: Searching through articles.

Scenario: Basic searching.
Given that the user has loaded the top page of the lexicography app
When the user searches for "foo"
Then the search results show one entry for "foo".
