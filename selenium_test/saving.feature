Feature: the user wants to be able to save

Background: a document
  Given a document with a definition with formatted text

Scenario: saving using the keyboard
  # The transform is a bit random. We just need something to
  # save.
  Then the first paragraph in btw:defintion contains formatted text
  When the user clears formatting from the first paragraph in btw:definition
  Then the first paragraph in btw:defintion does not contain formatted text
  When the user saves the file using the keyboard
  And the user reloads the file
  # It was saved...
  Then the first paragraph in btw:defintion does not contain formatted text

Scenario: saving using the mouse
  # The transform is a bit random. We just need something to
  # save.
  Then the first paragraph in btw:defintion contains formatted text
  When the user clears formatting from the first paragraph in btw:definition
  Then the first paragraph in btw:defintion does not contain formatted text
  When the user saves the file using the toolbar
  And the user reloads the file
  # It was saved...
  Then the first paragraph in btw:defintion does not contain formatted text