Feature: the user wants to be able to navigate the site

Scenario Outline: the navigation bar shows which page is active
  Given the user has logged in
  When the user navigates to page "<page>"
  Then the menu for "<page>" is marked active
  Examples: pages
    | page                        |
    | Home                        |
    | Lexicography/Search         |
# We do not do this one because Django CMS does not allow a clean way
# to make it work. Besides, it does not really matter.
# | Lexicography/New Article |
    | Bibliography/General Search |
    | Bibliography/Manage         |
