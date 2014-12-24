Feature: Articles are properly structured for viewing.
  As a regular user, I want articles that reflect the actual structure of
  the document when I view them.

Scenario: viewing senses and subsenses
  Given a document with senses and subsenses
  And the view has finished rendering
  Then the senses and subsenses are properly numbered

Scenario: sense hyperlinks are correct
  Given a document with senses, subsenses and hyperlinks
  And the view has finished rendering
  And the hyperlink with label "[a1]" points to "sense a1"
  And the hyperlink with label "[a]" points to "sense a"

Scenario: example hyperlinks are correct
  Given a document with a non-Pāli example with a bibliographical reference and a link to the example
  And the view has finished rendering
  Then the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3 quoted above in A." points to the example with the citation that starts with "foo"

Scenario: a valid document has a correct structure
  Given a valid document
  And the view has finished rendering
  Then the english renditions are reformatted in the correct structure
  And the antonyms are reformatted in the correct structure
  And the cognates are reformatted in the correct structure
  And the conceptual proximates are reformatted in the correct structure
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, foo." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake Vimalakīrti 116 quoted below in B, aprasanna." points to the example with the citation that starts with "aprasannānāṃ"
