Feature: semantic fields creation

Background: a user with permission to create custom semantic fields is on the main page of the semantic field application
Given a user with permission to create custom semantic fields has loaded the main page of the semantic field application
And the search table is loaded

Scenario: the user can cancel the button for creating custom fields
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user cancels the form for creating a custom field in the first detail pane
Then there is no form for creating a custom field in the first detail pane

Scenario: the user can click the button for creating custom fields, even after canceling
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

@dirty
Scenario: the user can create a custom field as a child of another field
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Create" button in the first form
Then there is no form for creating a custom field in the first detail pane
And the first detail pane shows the child "FOO"

Scenario: the user gets a useful error if they make a mistake when creating a field
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create Child" button is not visible
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner

Scenario: a spinner shows up in the "Create" button when the user tries to create a child and there is a network slowdown
When the user searches for "clarity"
Then the first result shows: The mind > Mental capacity > Understanding > Intelligence, cleverness > Sharpness, shrewdness, insight :: clarity (Noun)
When the user clicks on "The mind" in the first result
And the user clicks on the "Create Child" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
And the "Create" button does not show a spinner
Given there is a network slowdown
When the user clicks the "Create" button in the first form
Then the "Create" button shows a spinner
And the first form's heading field has an error

@dirty
Scenario: the user can create a custom field at the root
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
When the user types "FOO" in the "Heading" field in the first form
And the user clicks the "Create" button in the first form
Then there is no form for creating a custom field under the table
When the user searches for "FOO"
Then there is one result

Scenario: the user gets a useful error if they make a mistake when creating a field
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner

Scenario: a spinner shows up in the "Create" button when the user tries to create a field and there is a network slowdown
When the user clicks on the "Create Field" button under the table
Then there is a form for creating a custom field under the table
And the "Create" button does not show a spinner
Given there is a network slowdown
When the user clicks the "Create" button in the first form
Then the "Create" button shows a spinner
And the first form's heading field has an error

Scenario: a spinner shows up in the button when the user clicks the "Create Field" button when there is a network slowdown
Given there is a network slowdown
When the user clicks on the "Create Field" button under the table
Then the "Create Field" button shows a spinner
And there is a form for creating a custom field under the table
And the "Create Field" button does not show a spinner
And the "Create Field" button is not visible

@dirty
Scenario: the user can create a field related by pos for a custom field
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
When the user searches for "CUSTOM"
And the user clicks on "CUSTOM (Noun)" in the first result
And the user clicks on the "Create New POS" button in the first detail pane
Then there is a form for creating a custom field in the first detail pane
When the user clicks the "Create" button in the first form
Then the first form's heading field has an error
And the "Create" button does not show a spinner
