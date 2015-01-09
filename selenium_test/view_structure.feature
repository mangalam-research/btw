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
  And the bibliography hyperlink with label "Zeno (Name 1 for Title 3), Date 3" points to "https://www.foo3.com"
  And the first collapsible section titled "all semantic fields in the citations of this sense" contains
    """
    01.02.11; 01.04.04; 01.04.08; 01.05.05.09.01; 01.06.07.03; 02.02.18; 02.02.19; 03.05.01
    """
  And the cognate "saṃprasāda" has the semantic fields
    """
    01.02.11; 01.04.04; 01.04.08; 01.05.05.09.01; 01.06.07.03; 02.02.11; 02.02.18; 02.02.19; 03.05.01
    """
  And the article has the semantic fields
    """
    01.02.11; 01.04.04; 01.04.08; 01.05.05; 01.06.07; 02.01.13; 02.01.14; 02.01.17; 02.02.12; 02.02.13; 02.02.14; 02.02.18; 02.02.19; 02.02.22; 03.05.01; 03.07; 03.07.00; 03.07.03
    """

Scenario: clicking the expand all button expands all sections
  Given a valid document
  And the view has finished rendering
  Then all collapsible sections are collapsed
  When the user clicks the expand all button
  Then all collapsible sections are expanded

Scenario: clicking the collapse all button collapses all sections
  Given a valid document
  And the view has finished rendering
  Then all collapsible sections are collapsed
  When the user clicks the expand all button
  Then all collapsible sections are expanded
  When the user clicks the collapse all button
  Then all collapsible sections are collapsed

Scenario: clicking a hyperlink expands the sections that contain it
  Given a valid document
  And the view has finished rendering
  Then the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  When the user makes the hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." visible
  Then the citation that starts with "adhyātmasaṃprasādo" is in a collapsed section
  When the user clicks the hyperlink
  Then the citation that starts with "adhyātmasaṃprasādo" is not in a collapsed section

Scenario: reloading a page that points to a target in a section that would be collapsed expands the section
  Given a valid document
  And the view has finished rendering
  Then the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  When the user makes the hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." visible
  Then the citation that starts with "adhyātmasaṃprasādo" is in a collapsed section
  When the user clicks the hyperlink
  And the user reloads the page
  Given the view has finished rendering
  Then the citation that starts with "adhyātmasaṃprasādo" is not in a collapsed section
