Feature: editing primary sources of the bibliographical items.

Background: the user is on the page for editing primary sources
  Given the user has logged in
  Then the user has the "Bibliography/Manage" navigation option
  Given that the user is on the page for editing primary sources

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

Scenario: the user can add a primary source
  Given that the items are sorted by ascending creators
  When the user clicks on the button to add a primary source of row 0
  When the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  And row 0 shows there is 1 primary source
  And row 0 shows a primary source in subtable row 0 with reference title of "AAAA" and a genre of "Literary Text"

Scenario: the user can edit a primary source
  Given that the items are sorted by ascending creators
  When the user clicks on the button to add a primary source of row 0
  When the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  And row 0 shows there is 1 primary source
  And row 0 shows a primary source in subtable row 0 with reference title of "AAAA" and a genre of "Literary Text"
  When the user clicks on the button to edit the first primary source of row 0
  And the user submits the dialog with reference title of "BBBB" and a genre of "Sūtra"
  Then the modal dialog to add a primary source disappears
  And row 0 shows there is 1 primary source
  And row 0 shows a primary source in subtable row 0 with reference title of "BBBB" and a genre of "Sūtra"

Scenario: the user cannot submit a primary source with duplicate reference title
  Given that the items are sorted by ascending creators
  When the user clicks on the button to add a primary source of row 0
  When the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then row 0 shows there is 1 primary source
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source is visible
  And the modal dialog shows the error "Primary source with this Reference title already exists." for the reference title field
  When the user types ESCAPE
  Then row 0 shows there is 1 primary source

Scenario: the user cannot submit a primary source without a reference title
  Given that the items are sorted by ascending creators
  When the user clicks on the button to add a primary source of row 0
  When the user submits the dialog with reference title of "" and a genre of "Literary Text"
  Then the modal dialog to add a primary source is visible
  And the modal dialog shows the error "This field is required." for the reference title field
  When the user types ESCAPE
  Then row 0 shows there is 0 primary source

Scenario: the user filters the items
  Given all rows are loaded
  When the user clicks on the filtering field
  And the user types "Title 1"
  Then there is 1 row

Scenario: the user filters on a reference title
  Given all rows are loaded
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "BBBB" and a genre of "Sūtra"
  Then the modal dialog to add a primary source disappears
  And row 0 shows there are 2 primary sources
  When the user clicks on the button to add a primary source of row 1
  And the user submits the dialog with reference title of "AAAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  And row 1 shows there is 1 primary source
  When the user clicks on the filtering field
  And the user types "AAAA"
  Then there are 2 rows
  When the user opens row 0
  Then row 0 shows a primary source in subtable row 0 with reference title of "AAAA" and a genre of "Literary Text"
  And row 0 shows a subtable that has 1 row
  When the user opens row 1
  Then row 1 shows a primary source in subtable row 0 with reference title of "AAAAA" and a genre of "Literary Text"
  And row 1 shows a subtable that has 1 row

Scenario: the user can open and close all rows
  Given all rows are loaded
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  When the user clicks on the button to add a primary source of row 1
  And the user submits the dialog with reference title of "AAAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  When the user opens all rows
  Then row 0 is open
  Then row 1 is open
  When the user closes all rows
  Then row 0 is closed
  Then row 1 is closed

Scenario: the system remembers which rows are opened
  Given all rows are loaded
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  When the user opens row 0
  Then row 0 is open
  When the user clicks on the filtering field
  And the user types "QQQQ"
  Then there are 0 rows
  When the user empties the filtering field
  Then row 0 is open

Scenario: the user can correct an error in the form
  Given that the items are sorted by ascending creators
  When the user clicks on the button to add a primary source of row 0
  When the user submits the dialog with reference title of "" and a genre of "Literary Text"
  Then the modal dialog to add a primary source is visible
  And the modal dialog shows the error "This field is required." for the reference title field
  When the user submits the dialog with reference title of "ZZZ" and a genre of "Literary Text"
  Then row 0 shows there is 1 primary source
