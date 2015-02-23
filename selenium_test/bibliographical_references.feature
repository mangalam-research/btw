Feature: bibliographical references in the text.
  As an author
  I want to be able to add and remove bibliographical references
  and have them show meaningful information.

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

Scenario: replacing a selection with a reference
  Given a document with a single sense
  When the user replaces a selection with reference to an item with a reference title
  Then the new reference contains the reference title.
