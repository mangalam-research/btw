Feature: editing primary sources cannot happen without permission.

Scenario: a user cannot add a primary source without permission.
  Given a user without permission to edit primary sources has logged in
  Then the user does not have the "Bibliography/Manage" navigation option

Scenario: a user cannot edit primary sources in the general search page
  Given the user has logged in
  And that the user is on the page for editing primary sources
  And all rows are loaded
  When the user clicks on the button to add a primary source of row 0
  And the user submits the dialog with reference title of "AAAA" and a genre of "Literary Text"
  Then the modal dialog to add a primary source disappears
  Given a user without permission to edit primary sources has logged in
  And that the user is on the page for performing a general bibliographical search
  And all rows are loaded
  Then there are no buttons for adding primary sources
  When the user opens row 0
  Then there are no buttons for editing primary sources
