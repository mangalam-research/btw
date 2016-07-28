Feature: the user wants to be able to edit semantic fields with a UI.

# The tests in this file use the sf_editor_test page directly for
# speed rather than start an editor.

Background:
Given the user has logged in
And the sf_editor_test page is loaded

# Some of the scenarios here are repated from the
# semantic_fiels.feature file due to the similarity of interfaces.

Scenario: the user can get the help popups
Then no popovers are visible
When the user clicks on the help for the search field
Then the help for the search field is visible
When the user closes the open popover
Then no popovers are visible
When the user clicks on the help for the aspect combo box
Then the help for the aspect combo box is visible
When the user closes the open popover
Then no popovers are visible
When the user clicks on the help for the scope combo box
Then the help for the scope combo box is visible

Scenario: the user can search
When the user searches for "clarity"
Then there is one result
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)

Scenario: the user can perform a literal search
When the user searches for "Law"
Then there are 3 results
When the user searches literally for "Law"
Then there is one result

Scenario: the user can search in lexemes
When the user searches for "epicurism"
Then there are no results
When the user changes the search to search for lexemes
Then there is one result

Scenario: the user can search in custom fields
When the user searches for "CUSTOM"
Then there is one result
When the user changes the search to search for HTE fields
Then there are no results
When the user changes the search to search for BTW fields
Then there is one result
When the user changes the search to search for all fields
Then there is one result

Scenario: the user can open field details
When the user searches for "clarity"
Then there is one result
And there are no detail panes
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then there is one detail pane
And the first detail pane shows: The mind (Noun)

Scenario: the user can navigate the results
When the user searches for "clarity"
Then there is one result
And there are no detail panes
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then there is one detail pane
And the first detail pane shows: The mind (Noun)
When the user clicks on "Emotion" in the first detail pane
Then there is one detail pane
And the first detail pane shows: The mind > Emotion (Noun)
When the user clicks on "Passion" in the first detail pane
Then there is one detail pane
And the first detail pane shows: The mind > Emotion > Passion (Noun)
When the user clicks on the first pane's navigation button to go to the first page
Then there is one detail pane
And the first detail pane shows: The mind (Noun)
When the user clicks on the first pane's navigation button to go to the last page
Then there is one detail pane
And the first detail pane shows: The mind > Emotion > Passion (Noun)
When the user clicks on the first pane's navigation button to go to the previous page
Then there is one detail pane
And the first detail pane shows: The mind > Emotion (Noun)
When the user clicks on the first pane's navigation button to go to the next page
Then there is one detail pane
And the first detail pane shows: The mind > Emotion > Passion (Noun)

Scenario: the user can close panes
When the user searches for "Law"
Then there are 3 results
When the user clicks on "code of laws (Noun)" in the first result
Then there is one detail pane
And the first detail pane shows: Society > Law > Written laws :: code of laws (Noun)
When the user clicks on "Written laws (Noun)" in the second result
Then there are 2 detail panes
And the first detail pane shows: Society > Law > Written laws (Noun)
When the user clicks on the first pane's button to close the pane
Then there is one detail pane
And the first detail pane shows: Society > Law > Written laws :: code of laws (Noun)

Scenario: the user can close all panes
When the user searches for "Law"
Then there are 3 results
When the user clicks on "code of laws (Noun)" in the first result
Then there is one detail pane
And the first detail pane shows: Society > Law > Written laws :: code of laws (Noun)
When the user clicks on "Written laws (Noun)" in the second result
Then there are 2 detail panes
And the first detail pane shows: Society > Law > Written laws (Noun)
When the user clicks on the first pane's button to close all panes
Then there are no detail panes

# There's no editing test because we cannot edit semantic fields here.

Scenario: the user can delete fields from the chosen semantic fields
Given there are 3 fields in the chosen semantic fields
When the user deletes a field in the chosen semantic fields
Then there are 2 fields in the chosen semantic fields

Scenario: the user can add fields to the chosen semantic fields from search results
Given there are 3 fields in the chosen semantic fields
When the user searches for "Law"
Then there are 3 results
When the user clicks on the add button in the first result
Then there are 4 fields in the chosen semantic fields

Scenario: the user can combine fields from search results
Given there are no fields in the combinator elements
When the user searches for "Law"
Then there are 3 results
When the user clicks on the combine button in the first result
Then there is one field in the combinator elements

Scenario: the user can add fields to the chosen semantic fields from a navigator
Given there are 3 fields in the chosen semantic fields
When the user searches for "Law"
Then there are 3 results
When the user clicks on "code of laws (Noun)" in the first result
Then there is one detail pane
When the user clicks on the add button in the first detail pane
Then there are 4 fields in the chosen semantic fields

Scenario: the user can combine fields from a navigator
Given there are no fields in the combinator elements
When the user searches for "Law"
Then there are 3 results
When the user clicks on "code of laws (Noun)" in the first result
Then there is one detail pane
When the user clicks on the combine button in the first detail pane
Then there is one field in the combinator elements

Scenario: the user can delete fields from combinator elements
Given there are no fields in the combinator elements
When the user searches for "Law"
Then there are 3 results
When the user clicks on the combine button in the first result
Then there is one field in the combinator elements
When the user deletes a field in the combinator elements
Then there are no fields in the combinator elements

Scenario: the user can add fields from the combinator
Given there are 3 fields in the chosen semantic fields
And there are no fields in the combinator elements
When the user searches for "Law"
Then there are 3 results
When the user clicks on the combine button in the first result
Then there is one field in the combinator elements
When the user clicks on the add button in the combinator
Then there are 4 fields in the chosen semantic fields

#
# Getting dragula to respond to a drag and drop through Selenium was
# too difficult. So this is not tested. Note that:
#
# * dragula itself is tested by its developer(s)
#
# * The drag and drop logic is tested in BTW's Karma tests.
#
# Scenario: the user can reorder the chosen fields
# Given the chosen semantic fields are "Person (01.04.04n)", "Beautification (02.02.18n)", "Lack of beauty (02.02.19n)"
# When the user swaps the first and second chosen semantic fields by drag and drop
# Then the chosen semantic fields are "Beautification (02.02.18n)", "Person (01.04.04n)", "Lack of beauty (02.02.19n)"
