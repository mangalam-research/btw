Feature: the user wants to be able to transform the document.

Background: a new document
  Given the user has logged in
  And a new document
  And a context menu is not visible

@wip
Scenario: using the navigation context menu to insert a sense before another sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  Then sense A becomes sense B
  And a new sense A is created
