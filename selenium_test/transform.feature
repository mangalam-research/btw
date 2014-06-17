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

Scenario: undoing a sense deletion
  Given a document with a single sense
  When the user brings up a context menu on navigation item "[SENSE A]"
  And the user clicks the context menu option "Delete this element"
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
  And there is a visible absence for btw:citations

Scenario: inserting a subsense by using a visible absence
  Given a document that has no btw:subsense
  When the user clicks on the visible absence for btw:subsense
  Then a new btw:subsense is created
  And there is no visible absence for btw:explanation
  And there is no visible absence for btw:subsense

Scenario: inserting citations in a sense by using a visible absence
  Given a document that has no btw:explanation
  When the user clicks on the visible absence for btw:explanation
  Then a new btw:explanation is created
  And there is a visible absence for btw:citations
  When the user clicks on the visible absence for btw:citations
  Then a new btw:citations is created
  And there is no visible absence for btw:citations

Scenario: creating a btw:example in a sense by using a visible absence
  Given a document that has no btw:explanation
  When the user clicks on the visible absence for btw:explanation
  Then a new btw:explanation is created
  When the user clicks on the visible absence for btw:citations
  Then a new btw:citations is created
  And there is a visible absence for btw:example
  When the user clicks on the visible absence for btw:example
  Then a new btw:example is created
  And there is no ref

Scenario: creating a btw:example in a subsense by using a visible absence
  Given a document that has no btw:subsense
  When the user clicks on the visible absence for btw:subsense
  Then a new btw:subsense is created
  When the user clicks on the visible absence for btw:example in btw:subsense
  Then a new btw:example is created in btw:subsense
  And there is no ref

Scenario: a Pāli example gets a Wheel of Dharma
  Given a document with a Pāli example
  Then the btw:example has a Wheel of Dharma

Scenario: the user changes an example from Pāli to no language
  Given a document with a Pāli example
  Then the btw:example has a Wheel of Dharma
  When the user removes the language from the btw:example
  Then the btw:example does not have a Wheel of Dharma

Scenario: the user changes an example from no language to Pāli
  Given a document with a non-Pāli example
  Then the btw:example does not have a Wheel of Dharma
  When the user adds the Pāli language to the btw:example
  Then the btw:example has a Wheel of Dharma

Scenario: a Pāli explained example gets a Wheel of Dharma
  Given a document with a Pāli example, explained
  Then the btw:example-explained has a Wheel of Dharma
  And the btw:explanation in btw:example-explained has a Wheel of Dharma

Scenario: the user changes an explained example from Pāli to no language
  Given a document with a Pāli example, explained
  Then the btw:example-explained has a Wheel of Dharma
  And the btw:explanation in btw:example-explained has a Wheel of Dharma
  When the user removes the language from the btw:example-explained
  Then the btw:example-explained does not have a Wheel of Dharma
  And the btw:explanation in btw:example-explained does not have a Wheel of Dharma

Scenario: the user changes an explained example from no language to Pāli
  Given a document with a non-Pāli example, explained
  Then the btw:example-explained does not have a Wheel of Dharma
  And the btw:explanation in btw:example-explained does not have a Wheel of Dharma
  When the user adds the Pāli language to the btw:example-explained
  Then the btw:example-explained has a Wheel of Dharma
  And the btw:explanation in btw:example-explained has a Wheel of Dharma

Scenario: marking text as Pāli
  Given a document with a definition that has been filled
  And the btw:definition does not contain foreign text
  When the user marks the text "prasāda" as Pāli in btw:definition
  Then the text "prasāda" is marked as Pāli in btw:definition

Scenario: marking text as Sanskrit
  Given a document with a definition that has been filled
  And the btw:definition does not contain foreign text
  When the user marks the text "prasāda" as Sanskrit in btw:definition
  Then the text "prasāda" is marked as Sanskrit in btw:definition

Scenario: marking text as Latin
  Given a document with a definition that has been filled
  And the btw:definition does not contain foreign text
  When the user marks the text "prasāda" as Latin in btw:definition
  Then the text "prasāda" is marked as Latin in btw:definition

Scenario: using the Pāli button when there is no selection
  Given a document with a definition that has been filled
  When the user clicks the Pāli button
  And the user clicks in the first semantic field

Scenario: using the Sanskrit button when there is no selection
  Given a document with a definition that has been filled
  When the user clicks the Sanskrit button
  And the user clicks in the first semantic field

Scenario: using the Latin button when there is no selection
  Given a document with a definition that has been filled
  When the user clicks the Latin button
  And the user clicks in the first semantic field

Scenario: clearing formatting from text
  Given a document with a definition with formatted text
  Then the first paragraph in btw:defintion contains formatted text
  When the user clears formatting from the first paragraph in btw:definition
  Then the first paragraph in btw:defintion does not contain formatted text

Scenario: clearing formatting from text, when the selection straddles.
  Given a document with a definition with formatted text
  When the user clears formatting from the first paragraph and second paragraph in btw:definition
  Then the user gets a dialog saying that the selection is straddling

Scenario: creating a paragraph
  Given a document with a definition that has been filled
  And the definition contains 2 paragraphs
  When the user clicks in the first paragraph of the definition
  And the user types ENTER
  Then the definition contains 3 paragraphs

Scenario: removing a paragraph with backspace
  Given a document with a definition that has been filled
  And the definition contains 2 paragraphs
  When the user clicks at the start of the second paragraph of the definition
  And the user types BACKSPACE
  Then the definition contains 1 paragraph

Scenario: removing a paragraph with delete
  Given a document with a definition that has been filled
  And the definition contains 2 paragraphs
  When the user clicks at the start of the second paragraph of the definition
  And the user hits the left arrow
  And the user types DELETE
  Then the definition contains 1 paragraph

Scenario: splitting a semantic field
  Given a document with some semantic fields
  And the document contains 2 semantic fields
  When the user clicks in the first semantic field
  And the user types ";"
  Then the document contains 3 semantic fields

Scenario: removing a semantic field with backspace
  Given a document with some semantic fields
  And the document contains 2 semantic fields
  When the user clicks at the start of the second semantic field
  And the user types BACKSPACE
  Then the document contains 1 semantic field

Scenario: removing a semantic field with delete
  Given a document with some semantic fields
  And the document contains 2 semantic fields
  When the user clicks at the start of the second semantic field
  And the user hits the left arrow
  And the user types DELETE
  Then the document contains 1 semantic field

Scenario: creating a sense emphasis
  Given a document with a definition that has been filled
  When the user wraps the text "clarity" in a btw:sense-emphasis in btw:definition
  Then the text "clarity" is wrapped in a btw:sense-emphasis

Scenario: creating a lemma-instance in a citation
  Given a document with a non-Pāli example
  And the document has no btw:lemma-instance
  When the user adds a reference to an item to the first example
  And the user wraps the text "foo" in a btw:lemma-instance in btw:cit
  Then the text "foo" is wrapped in a btw:lemma-instance

Scenario: creating a lemma-instance in a translation
  Given a document with a non-Pāli example
  And the document has no btw:lemma-instance
  When the user adds the text "blip" in btw:tr
  And the user wraps the text "blip" in a btw:lemma-instance in btw:tr
  Then the text "blip" is wrapped in a btw:lemma-instance

Scenario: creating an antonym-instance in a citation
  Given a document with an antonym with citations
  And the document has no btw:antonym-instance
  When the user adds a reference to an item to the first example
  And the user wraps the text "citation" in a btw:antonym-instance in btw:cit
  Then the text "citation" is wrapped in a btw:antonym-instance

Scenario: creating an antonym-instance in a translation
  Given a document with an antonym with citations
  And the document has no btw:antonym-instance
  When the user wraps the text "translation" in a btw:antonym-instance in btw:tr
  Then the text "translation" is wrapped in a btw:antonym-instance

Scenario: creating an cognate-instance in a citation
  Given a document with a cognate with citations
  And the document has no btw:cognate-instance
  When the user adds a reference to an item to the first example
  And the user wraps the text "citation" in a btw:cognate-instance in btw:cit
  Then the text "citation" is wrapped in a btw:cognate-instance

Scenario: creating an cognate-instance in a translation
  Given a document with a cognate with citations
  And the document has no btw:cognate-instance
  When the user wraps the text "translation" in a btw:cognate-instance in btw:tr
  Then the text "translation" is wrapped in a btw:cognate-instance
