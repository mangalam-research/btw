Feature: Searching through articles.

#
# The main aim of these tests is to check that the **mechanics of the
# GUI are working properly.** This does not attempt to test every
# possible combinations of returned data. Such testing is performed in
# the Django unit tests.
#

Scenario: Author performs a basic lemma search.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for lemma "foo"
Then the search results show one entry for "foo".
And there is a "Published" column visible
And there is a "Deleted" column visible

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
When the user searches for lemma "old and new records"
Then the search results show one entry for "old and new records".
When the user sets the search to search all records
Then the search results show 3 entries for "old and new records".

Scenario: A user that cannot author cannot see the publication status
Given that the user has loaded the top page of the lexicography app
Then there is no "Published" column visible

Scenario: A user that cannot author cannot see the deletion status
Given that the user has loaded the top page of the lexicography app
Then there is no "Deleted" column visible

Scenario: When the user reloads the page, the filter and lemma settings remains the same.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for lemma "foo"
Then the search results show one entry for "foo"
Given that the user has loaded the top page of the lexicography app
And the search table is loaded
Then the search results show one entry for "foo"

Scenario: When the user reloads the page, the all records settings remain the same.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for lemma "old and new records"
And the user sets the search to search all records
Then the search results show 3 entries for "old and new records".
Given that the user has loaded the top page of the lexicography app
And the search table is loaded
Then the search results show 3 entries for "old and new records".

Scenario: When the user reloads the page, the all records settings remain the same.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
And the search table is loaded
When the user switches the search to unpublished articles
Then the search results show unpublished entries
Given that the user has loaded the top page of the lexicography app
And the search table is loaded
Then the search results show unpublished entries

Scenario: When the user logs out, the column display is changed.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
And the search table is loaded
Then there is a "Published" column visible
When the user logs out
Given that the user has loaded the top page of the lexicography app
And the search table is loaded
Then there is no "Published" column visible

Scenario: When the user logs out, the search info is cleared.
Given the user has logged in
And that the user has loaded the top page of the lexicography app
When the user searches for lemma "foo"
When the user logs out
Given that the user has loaded the top page of the lexicography app
And the search table is loaded
Then the search box is empty and the lemmata only box is unchecked
