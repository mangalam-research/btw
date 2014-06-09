Feature: the user wants to be able to hyperlink to senses and subsenses.

Scenario: inserting a hyperlink to a sense inserts a properly labeled link
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  Then the hyperlinkig modal dialog comes up
  And the hyperlinking choices are
    | choice        |
    | [a] sense a   |
    | [a1] sense a1 |
    | [a2] sense a2 |
    | [b] sense b   |
    | [b1] sense b1 |
  When the user clicks the hyperlinking choice for "sense a"
  Then a new hyperlink with the label "[a]" is inserted.

Scenario: inserting a hyperlink to a subsense inserts a properly labeled link
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a2"
  Then a new hyperlink with the label "[a2]" is inserted.

Scenario: deleting a sense that has hyperlinks deletes the hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a"
  Then a new hyperlink with the label "[a]" is inserted
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Delete this element"
  Then there is no hyperlink with the label "[a]".

Scenario: deleting a sense whose subsense has hyperlinks deletes the hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a2"
  Then a new hyperlink with the label "[a2]" is inserted
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Delete this element"
  Then there is no hyperlink with the label "[a2]".

Scenario: deleting a subsense that has a hyperlink deletes the hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a2"
  Then a new hyperlink with the label "[a2]" is inserted
  When the user brings up a context menu on navigation item "[brief explanation of sense a2]"
  And the user clicks the context menu option "Delete this element"
  Then there is no hyperlink with the label "[a2]".

Scenario: hyperlinks are saved
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a"
  Then a new hyperlink with the label "[a]" is inserted.
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a2"
  Then a new hyperlink with the label "[a2]" is inserted.
  When the user saves the file
  And the user reloads the file
  Then there are hyperlinks with labels "[a]" and "[a2]"
  And the hyperlink with label "[a]" points to "sense a"
  And the hyperlink with label "[a2]" points to "sense a2"

Scenario: deleting a sense renumbers the subsense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense b1"
  Then the hyperlink with label "[b1]" points to "sense b1"
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Delete this element"
  Then the hyperlink with label "[a1]" points to "sense b1"

Scenario: deleting a sense renumbers the sense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense b"
  Then the hyperlink with label "[b]" points to "sense b"
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Delete this element"
  Then the hyperlink with label "[a]" points to "sense b"

Scenario: deleting a subsense renumbers the subsense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense a2"
  Then the hyperlink with label "[a2]" points to "sense a2"
  When the user brings up a context menu on navigation item "[brief explanation of sense a1]"
  And the user clicks the context menu option "Delete this element"
  Then the hyperlink with label "[a1]" points to "sense a2"

Scenario: creating a sense renumbers the subsense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense b1"
  Then the hyperlink with label "[b1]" points to "sense b1"
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  Then the hyperlink with label "[c1]" points to "sense b1"

Scenario: creating a sense renumbers the sense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense b"
  Then the hyperlink with label "[b]" points to "sense b"
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  Then the hyperlink with label "[c]" points to "sense b"

Scenario: creating a subsense renumbers the subsense hyperlinks
  Given a document with senses and subsenses
  When the user brings up a context menu in the text in the definition
  And the user clicks the context menu option "Insert a new hyperlink to a sense"
  When the user clicks the hyperlinking choice for "sense b1"
  Then the hyperlink with label "[b1]" points to "sense b1"
  When the user brings up a context menu on navigation item "[brief explanation of sense b1]"
  And the user clicks the context menu option "Create new btw:subsense before this one"
  Then the hyperlink with label "[b2]" points to "sense b1"
