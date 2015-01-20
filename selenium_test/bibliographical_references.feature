Feature: bibliographical references in the text.
  As an author
  I want to be able to add and remove bibliographical references
  and have them show meaningful information.

# This was created to catch a bug that caused expanding all rows to
# navigate out of the page.
Scenario: expanding all rows in the bibliographical references dialog
  Given a document with a single sense
  When the user opens the modal dialog to insert a reference
  And the user opens all rows
  Then the editor is present

# This was created to catch a bug that caused closing all rows to
# navigate out of the page.
Scenario: closing all rows in the bibliographical references dialog
  Given a document with a single sense
  When the user opens the modal dialog to insert a reference
  And the user closes all rows
  Then the editor is present

Scenario: adding a reference that has a reference title
  Given a document with a single sense
  When the user adds a reference to an item with a reference title
  Then the new reference contains the reference title.

Scenario: adding a reference that does not have a reference title
  Given a document with a single sense
  When the user adds a reference to an item without a reference title
  Then the new reference contains the first author's last name and the date.

Scenario: adding custom text to a reference
  Given a document with a single sense
  When the user adds a reference to an item
  Then a new reference is inserted
  When the user adds custom text to the new reference
  Then the new reference contains a placeholder

Scenario: adding custom text to a reference when there is already text
  Given a document with a single sense
  When the user adds a reference to an item
  Then a new reference is inserted
  When the user adds custom text to the new reference
  Then the new reference contains a placeholder
  When the user types "blah"
  And the user brings up the context menu
  Then there is no context menu option "Add custom text to reference"

Scenario: deleting a reference
  Given a document with a non-Pāli example
  When the user adds a reference to an item to the first example
  Then the new reference contains the reference title
  When the user deletes a reference
  Then the element that contained the reference no longer contains the space that was added for the reference
