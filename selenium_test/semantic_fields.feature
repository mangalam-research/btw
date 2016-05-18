Feature: semantic fields search

Background: a user without permission to create or edit custom semantic fields is on the main page of the semantic field application
Given a user without permission to create or edit custom semantic fields has loaded the main page of the semantic field application
And the search table is loaded

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

Scenario: the user cannot edit a custom field
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
Then the first detail pane shows: The world > CUSTOM (Noun)
And there is no edit button in the first detail pane

Scenario: the user cannot create fields
Then there is no "Create Field" button under the table
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then the first detail pane shows: The mind (Noun)
And there is no "Create Child" button in the first detail pane
