Feature: Searching through articles.

Scenario: Author performs a basic headword search.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for headword "foo"
Then the search results show one entry for "foo".

Scenario: When an author loads the main page the default search shows published and unpublished entries.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
And the search table is loaded
Then the search results show published and unpublished entries

Scenario: An author can switch the search to unpublished articles.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
And the search table is loaded
When the user switches the search to unpublished articles
Then the search results show unpublished entries

Scenario: An author can switch the search to published articles.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
And the search table is loaded
When the user switches the search to published articles
Then the search results show published entries

Scenario: An author can switch the search to search all records.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for headword "old and new records"
Then the search results show one entry for "old and new records".
When the user sets the search to search all records
Then the search results show 3 entries for "old and new records".
