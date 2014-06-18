Feature: tooltips

Scenario: the tooltip for a hyperlink to a sense has the sense's term in it
  Given a document with senses, subsenses and hyperlinks
  And the hyperlink with label "[a]" points to "sense a"
  Then the sense hyperlink with label "[a]" has a tooltip that says "sense a"

Scenario: the tooltip for a hyperlink to a subsense has the sense's explanation in it
  Given a document with senses, subsenses and hyperlinks
  And the hyperlink with label "[a1]" points to "sense a1"
  Then the sense hyperlink with label "[a1]" has a tooltip that says "sense a1"
