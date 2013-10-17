Feature: the user wants to be able to transform the document.

Background: a new document
  Given the user has logged in
  And a new document
  And a context menu is not visible

Scenario: using the navigation context menu to insert a sense before another sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  Then sense A becomes sense B
  And a new sense A is created

Scenario: using the navigation context menu to insert a sense after another sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense after this one"
  Then sense A remains the same
  And a new sense B is created

Scenario: undoing a sense insertion
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  And the user undoes
  Then the senses are the same as originally
