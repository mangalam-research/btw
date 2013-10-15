Feature: navigation context menus

# By "context menu" here we understand only "wed context menu", not
# the default browser context menu.

Background: a new document
  Given the user has logged in
  And a new document
  And a context menu is not visible

@wip
Scenario: bringing up a context menu over a navigation element
  When the user resizes the window so that the editor pane has a vertical scrollbar
  And the user scrolls the editor pane down
  And the user brings up a context menu on navigation item "[SENSE A]"
  Then a context menu is visible close to where the user clicked
