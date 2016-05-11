Feature: semantic fields application

Scenario: the user can get the help popups
Given the user has loaded the main page of the semantic field application
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
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then there is one result
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)

Scenario: the user can perform a literal search
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "Law"
Then there are 3 results
When the user searches literally for "Law"
Then there is one result

Scenario: the user can search in lexemes
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "epicurism"
Then there are no results
When the user changes the search to search for lexemes
Then there is one result

Scenario: the user can search in custom fields
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "CUSTOM"
Then there is one result
When the user changes the search to search for HTE fields
Then there are no results
When the user changes the search to search for BTW fields
Then there is one result
When the user changes the search to search for all fields
Then there is one result

Scenario: the user can open field details
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then there is one result
And there are no detail panes
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then there is one detail pane
And the first detail pane shows: The mind (Noun)

Scenario: the user can navigate the results
Given the user has loaded the main page of the semantic field application
And the search table is loaded
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
Given the user has loaded the main page of the semantic field application
And the search table is loaded
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
Given the user has loaded the main page of the semantic field application
And the search table is loaded
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

Scenario: the user can click the button for creating custom fields
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner

Scenario: the user can cancel the button for creating custom fields
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user cancels the form for creating a custom field in the first detail pane
Then there is no form for creating a custom field in the first detail pane

Scenario: the user can click the button for creating custom fields, even after canceling
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user cancels the form for creating a custom field in the first detail pane
Then there is no form for creating a custom field in the first detail pane
When the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner

Scenario: the user can create a custom field as a child of another field
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then there is one result
And there are no detail panes
And the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Create" button in the first form
Then there is no form for creating a custom field in the first detail pane
And the first detail pane shows the child "FOO"

Scenario: the user gets a useful error if they make a mistake when creating a field
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then the first detail pane shows: The mind (Noun)
When the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create Child" button is not visible
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner

Scenario: a spinner shows up in the "Create" button when the user tries to create a child and there is a network slowdown
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
Then the first detail pane shows: The mind (Noun)
When the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
Given there is a network slowdown
When the user clicks the "Create" button in the first form
Then the "Create" button shows a spinner
And the first form's heading field has an error

Scenario: the user can create a custom field at the root
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Create" button in the first form
Then there is no form for creating a custom field under the table
When the user searches for "FOO"
Then there is one result

Scenario: the user gets a useful error if they make a mistake when creating a field
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner

Scenario: a spinner shows up in the "Create" button when the user tries to create a field and there is a network slowdown
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
Given there is a network slowdown
When the user clicks the "Create" button in the first form
Then the "Create" button shows a spinner
And the first form's heading field has an error

Scenario: a spinner shows up in the button when the user clicks the "Create Field" button when there is a network slowdown
Given the user has loaded the main page of the semantic field application
And the search table is loaded
And there is a network slowdown
When the user clicks on the "Create Field" button under the table
Then the "Create Field" button shows a spinner
And there is a form for creating a custom field under the table
And the "Create Field" button does not show a spinner
And the "Create Field" button is not visible

Scenario: the user can create a field related by pos for a custom field
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the "Create New POS" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Create" button in the first form
Then there is no form for creating a custom field in the first detail pane
And the first detail pane shows the other part of speech "FOO (None)"

Scenario: the user gets a useful error if they make a mistake when creating a field related by pos
Given the user has loaded the main page of the semantic field application
And the search table is loaded
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the "Create New POS" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner
