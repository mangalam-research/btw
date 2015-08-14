Feature: Citing all of BTW.
  As a regular user, I want to be able to cite BTW as a whole.

Scenario: the user can set an access date
  Given the user goes to the page for citing BTW as a whole
  Then the citations show the date from the access date field
  When the user clicks in the access date field
  Then there is a date picker visible
  When the user changes the date
  Then the citations show the date from the access date field
  And the MODS data has the correct access date field

Scenario: the user can download the MODS record
  Given the user goes to the page for citing BTW as a whole
  Then the citations show the date from the access date field
  When the user clicks the button named "Get the MODS Record"
  Then the MODS data is downloaded
