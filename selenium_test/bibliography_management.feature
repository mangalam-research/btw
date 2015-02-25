Feature: managing bibliographical items.

Background: the user is on the page for managing bibliographical items
  Given the user has logged in
  And that the user is on the page for managing bibliographical items

Scenario: the user refreshes the bibliography
  When the user clicks the button for refreshing the bibliography
  Then the bibliography is refreshed
