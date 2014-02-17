Feature: editing the reference titles of the bibliographical items cannot happen without permission.

Scenario: a user cannot enter a title for reference without permission.
  Given a user without permission to edit titles has logged in
  And that the user is on the page for editing titles
  And that the items are sorted by ascending creators
  When the user clicks on the title for reference of row 0
  And the user types "AAAA"
  And the user types ENTER
  Then the title for reference of row 0 is "[No title assigned.]"
