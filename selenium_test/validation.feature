Feature: BTW-specific validation.

Scenario: a valid document has no errors
Given a valid document
And the document is completely validated
Then there are no errors

Scenario: senses without semantic fields are reported
Given a document with a single sense that has a subsense
And the document is completely validated
Then there is an error reporting that sense A is without semantic fields

Scenario: senses without semantic fields are reported
Given a document with one btw:cognates with one btw:cognate and no btw:none
And the document is completely validated
Then there is an error reporting that a cognate is without semantic fields

Scenario: invalid semantic fields are reported
Given a document with bad semantic fields
And the document is completely validated
Then there are errors reporting the bad semantic fields
