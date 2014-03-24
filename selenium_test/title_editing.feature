Feature: editing the reference titles of the bibliographical items.

Background: the user is on the page for editing titles
  Given the user has logged in
  And that the user is on the page for editing titles

Scenario: the user sees the items
  Then the items are sorted by ascending creators.

Scenario: the user sorts the creators
  Given that the items are sorted by ascending creators
  When the user clicks on the icon for sorting creators
  Then the items are sorted by descending creators
  When the user clicks on the icon for sorting creators
  Then the items are sorted by ascending creators.

Scenario: the user sorts the dates
  Given that the items are sorted by ascending creators
  When the user clicks on the icon for sorting dates
  Then the items are sorted by ascending dates
  When the user clicks on the icon for sorting dates
  Then the items are sorted by descending dates.

Scenario: the user sorts the original titles
  Given that the items are sorted by ascending creators
  When the user clicks on the icon for sorting original titles
  Then the items are sorted by ascending original titles
  When the user clicks on the icon for sorting original titles
  Then the items are sorted by descending original titles.

Scenario: the user can enter a title for reference
  Given that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 0 is "AAAA"

Scenario: the user sorts the titles for reference
  Given that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "BBBB"
  And the user types ENTER
  Then the title for reference of row 0 is "BBBB"
  When the user clicks on the title for reference of row 1
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 1 is "AAAA"
  When the user clicks on the icon for sorting titles for reference
  Then the items are sorted by ascending titles for reference
  When the user clicks on the icon for sorting titles for reference
  Then the items are sorted by descending titles for reference

Scenario: the user's editing is saved
  Given that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "BBBB"
  And the user types ENTER
  Then the title for reference of row 0 is "BBBB"
  When the user clicks on the title for reference of row 1
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 1 is "AAAA"
  When the user reloads the page for editing titles
  Then the items are sorted by ascending creators
  And the title for reference of row 0 is "BBBB"
  And the title for reference of row 1 is "AAAA"

Scenario: the user filters the items
  Given all rows are loaded
  When the user clicks on the filtering field
  And the user types "Title 1"
  Then there is 1 row

Scenario: the user cannot enter duplicate titles
  Given that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 0 is "AAAA"
  When the user clicks on the title for reference of row 1
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 1 has an error message.
  When the user reloads the page for editing titles
  Then the title for reference of row 1 is "[No title assigned.]"

Scenario: the user can delete titles
  Given that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "BBBB"
  And the user types ENTER
  Then the title for reference of row 0 is "BBBB"
  When the user clicks on the title for reference of row 1
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 1 is "AAAA"
  When the user clicks on the title for reference of row 0
  And the user clicks the clear button
  And the user types ENTER
  Then the title for reference of row 0 is "[No title assigned.]"
  When the user clicks on the title for reference of row 1
  And the user clicks the clear button
  And the user types ENTER
  Then the title for reference of row 1 is "[No title assigned.]"
