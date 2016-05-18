Feature: semantic fields editing

Background: a user with permission to edit custom semantic fields is on the main page of the semantic field application
Given a user with permission to edit custom semantic fields has loaded the main page of the semantic field application
And the search table is loaded

@dirty
Scenario: the user can edit a custom field
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the edit button in the first detail pane
Then there is a form for editing a custom field in the first detail pane
And the edit button is not visible
And the "Heading" field in the first form contains the text "CUSTOM"
And the "Submit" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Submit" button in the first form
Then there is no form for editing a custom field in the first detail pane
And the first detail pane shows: The world > CUSTOMFOO (Noun)

Scenario: the user can cancel an edit to a custom field
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the edit button in the first detail pane
Then there is a form for editing a custom field in the first detail pane
When the user cancels the form for editing a custom field in the first detail pane
Then there is no form for editing a custom field in the first detail pane
And the first detail pane shows: The world > CUSTOM (Noun)
And the edit button is visible
And the edit button does not show a spinner

Scenario: the user gets a useful error if they make a mistake when editing a field
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the edit button in the first detail pane
Then there is a form for editing a custom field in the first detail pane
And the "Heading" field in the first form contains the text "CUSTOM"
And the "Submit" button does not show a spinner
When the user clears the "Heading" field in the first form
And the user clicks the "Submit" button in the first form
Then the first form's heading field has an error
And the "Submit" button does not show a spinner
And the first detail pane shows: The world > CUSTOM (Noun)

Scenario: the user cannot edit an HTE field
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
And there is no edit button in the first detail pane

Scenario: a spinner shows up in the button when the user clicks the edit button and there is a network slowdown
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
Given there is a network slowdown
When the user clicks on the edit button in the first detail pane
Then the edit button shows a spinner

Scenario: a spinner shows up in the button when the user clicks the "Submit" button and there is a network slowdown
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the edit button in the first detail pane
Then there is a form for editing a custom field in the first detail pane
And the edit button is not visible
And the "Heading" field in the first form contains the text "CUSTOM"
Given there is a network slowdown
When the user clicks the "Submit" button in the first form
Then the "Submit" button shows a spinner
