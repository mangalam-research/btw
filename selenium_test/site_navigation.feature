Feature: the user wants to be able to navigate the site

Scenario Outline: the navigation bar shows which page is active
  Given the user has logged in
  When the user navigates to page "<page>"
  Then the menu for "<page>" is marked active
  Examples: pages
    | page                        |
    | Home                        |
    | Lexicography/Search         |
    | Lexicography/New Article    |
    | Bibliography/General Search |
    | Bibliography/Manage         |
