Feature: the user wants the user interface to show relevant information about the document.

Scenario: subsense numbering decoration
  Given a document with a single sense that has a subsense
  Then the btw:explanation for the btw:subsense has numbering

Scenario: sense numbering decoration
  Given a document with a sense with explanation
  Then the btw:explanation for the btw:sense has no numbering
