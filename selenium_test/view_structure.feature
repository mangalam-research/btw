Feature: Articles are properly structured for viewing.
  As a regular user, I want articles that reflect the actual structure of
  the document when I view them.

Scenario: viewing senses and subsenses
  Given a document with senses and subsenses
  Then the senses and subsenses are properly numbered

Scenario: sense hyperlinks are correct
  Given a document with senses, subsenses and hyperlinks
  And the hyperlink with label "[a1]" points to "sense a1"
  And the hyperlink with label "[a]" points to "sense a"

Scenario: example hyperlinks are correct
  Given a document with a non-Pāli example with a bibliographical reference and a link to the example
  Then the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3 quoted above in [citations for sense a]." points to the first example.
