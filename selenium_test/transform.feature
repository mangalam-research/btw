Feature: the user wants to be able to transform the document.

Scenario: using the navigation context menu to insert a sense before another sense
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  Then sense A becomes sense B
  And a new sense A is created

Scenario: using the navigation context menu to insert a sense after another sense
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense after this one"
  Then sense A remains the same
  And a new sense B is created

Scenario: undoing a sense insertion
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:sense before this one"
  And the user undoes
  Then the senses are the same as originally

Scenario: using the navigation context menu to insert an english rendition before another english rendition
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[English rendition]" under "[SENSE A]"
  And the user clicks the context menu option "Create new btw:english-rendition before this one"
  Then the first english rendition becomes second
  And a new first english rendition is created

Scenario: using the navigation context menu to insert an english rendition after another english rendition
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[English rendition]" under "[SENSE A]"
  And the user clicks the context menu option "Create new btw:english-rendition after this one"
  Then the first english rendition remains the same
  And a new english rendition is created after the first

Scenario: using the navigation context menu to insert a subsense in a sense that does not already have one
  Given a document with a single sense that does not have a subsense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Create new btw:subsense"
  Then the single sense contains a single subsense

Scenario: using the navigation context menu to insert a subsense after a subsense
  Given a document with a single sense that has a subsense
  When the user brings up a context menu on navigation item "[brief explanation of sense a1]"
  And the user clicks the context menu option "Create new btw:subsense after this one"
  Then the single sense contains an additional subsense after the one that was already there

Scenario: using the navigation context menu to insert a subsense before a subsense
  Given a document with a single sense that has a subsense
  When the user brings up a context menu on navigation item "[brief explanation of sense a1]"
  And the user clicks the context menu option "Create new btw:subsense before this one"
  Then the single sense contains an additional subsense before the one that was already there

Scenario: inserting an antonym
  Given a document that has no btw:antonym
  When the user clicks on the btw:none element of btw:antonyms
  And the user brings up the context menu
  And the user clicks the context menu option "Create new btw:antonym"
  Then a new btw:antonym is created

Scenario: inserting a cognate
  Given a document that has no btw:cognate
  When the user clicks on the btw:none element of btw:cognates
  And the user brings up the context menu
  And the user clicks the context menu option "Create new btw:cognate"
  Then a new btw:cognate is created

Scenario: inserting a conceptual proximate
  Given a document that has no btw:conceptual-proximate
  When the user clicks on the btw:none element of btw:conceptual-proximates
  And the user brings up the context menu
  And the user clicks the context menu option "Create new btw:conceptual-proximate"
  Then a new btw:conceptual-proximate is created

Scenario: inserting an explanation by using a visible absence
  Given a document that has no btw:explanation
  When the user clicks on the visible absence for btw:explanation
  Then a new btw:explanation is created
  And there is no visible absence for btw:explanation
  And there is no visible absence for btw:subsense

Scenario: inserting a subsense by using a visible absence
  Given a document that has no btw:subsense
  When the user clicks on the visible absence for btw:subsense
  Then a new btw:subsense is created
  And there is no visible absence for btw:explanation
  And there is no visible absence for btw:subsense
