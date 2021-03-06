Feature: Articles are properly structured for viewing.
  As a regular user, I want articles that reflect the actual structure of
  the document when I view them.

Scenario: viewing senses and subsenses
  Given a document with senses and subsenses
  And the view has finished rendering
  Then the senses and subsenses are properly numbered
  And there is no button for editing the article

Scenario: viewing an unpublished article
  Given the user has logged in
  And an unpublished document
  Then there is an alert indicating the document is unpublished

Scenario: viewing an published article
  Given a published document
  Then there is no alert indicating the document is unpublished

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
  Then the table of contents is non-expandable
  And the english renditions are reformatted in the correct structure
  And the antonyms are reformatted in the correct structure
  And the cognates are reformatted in the correct structure
  And the conceptual proximates are reformatted in the correct structure
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, saṃprasāda." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake AkośBh ad VIII,9, 440 4-12 quoted above in A, foo." points to the example with the citation that starts with "adhyātmasaṃprasādo"
  And the example hyperlink with label "See Zeno (Name 1 for Title 3), Date 3, XXX fake Vimalakīrti 116 quoted below in B, aprasanna." points to the example with the citation that starts with "aprasannānāṃ"
  And the bibliography hyperlink with label "Zeno (Name 1 for Title 3), Date 3" points to "https://www.foo3.com"
  And the bibliography hyperlink with label "Foo" points to "https://www.foo3.com"
  And the first collapsible section titled "all semantic fields in the citations of this sense" contains
    """
    01.02.11n Person (01.04.04n) 01.04.08n 01.05.05.09.01n 01.06.07.03n Beautification (02.02.18n) Lack of beauty (02.02.19n) Written laws (03.05.01n)
    """
  And the cognate "saṃprasāda" has the semantic fields
    """
    01.02.11n Person (01.04.04n) 01.04.08n 01.05.05.09.01n 01.06.07.03n Aesthetics (02.02.11n) Beautification (02.02.18n) Lack of beauty (02.02.19n) Written laws (03.05.01n)
    """
  And the article has the semantic fields
    """
    01.02.11n Person (01.04.04n) 01.04.08n By eating habits (01.05.05n) 01.06.07n Belief (02.01.13n) Expectation (02.01.14n) 02.01.17n Good taste (02.02.12n) Bad taste (02.02.13n) Fashionableness (02.02.14n) Beautification (02.02.18n) Lack of beauty (02.02.19n) 02.02.22n Written laws (03.05.01n) Education (03.07n) 03.07.00n Learning (03.07.03n)
    """
  And the navigation link "2. absolute confidence derived from understanding, typically compounded with avetya or abhedya" points to the fourth subsense
  And the table of contents contains
"""
OVERVIEW
SENSE DISCRIMINATION
>A. clarity, serenity
>>1. often explicitely associated to the water metaphor
>>2. in the sense of pleasurable emotion, serenity.
>B. confidence, trust, faith
>>1. faith, a form of trust not necessarily related to intellectual understanding
>>2. absolute confidence derived from understanding, typically compounded with avetya or abhedya
>C. favor
>D. devotion
HISTORICO-SEMANTICAL DATA
>etymology
CREDITS
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

Scenario: a document that fails to load
  Given that the next document will be loaded by a failing AJAX call
  And a valid document
  And the view has finished rendering
  Then the loading error message is visible

Scenario: a document that times out
  Given that the next document will be loaded by a timing-out AJAX call
  And a valid document
  And the view has finished rendering
  Then the time out error message is visible

Scenario: the user can expand the table of contents
  Given a valid document
  And the view has finished rendering
  And the window is sized so that the table of contents is expandable
  Then the table of contents is collapsed
  When the user clicks on the button to toggle the table of contents
  Then the table of contents is expanded

Scenario: the user can collapse the table of contents
  Given a valid document
  And the view has finished rendering
  And the window is sized so that the table of contents is expandable
  Then the table of contents is collapsed
  When the user clicks on the button to toggle the table of contents
  Then the table of contents is expanded
  When the user clicks on the button to toggle the table of contents
  Then the table of contents is collapsed

Scenario: clicking a link in the table of contents collapses it
  Given a valid document
  And the view has finished rendering
  And the window is sized so that the table of contents is expandable
  Then the table of contents is collapsed
  When the user clicks on the button to toggle the table of contents
  Then the table of contents is expanded
  When the user clicks a link in the table of contents
  Then the table of contents is collapsed

Scenario: inter-article hyperlinking
  Given a valid document
  And the view has finished rendering
  Then there is a hyperlink with label "abcd" that points to the article for the same lemma

Scenario: there is an article history modal available
  Given a valid document
  And the view has finished rendering
  When the user clicks the button named "Article history"
  Then there is a modal dialog titled "Article History" visible

Scenario: there is a permalink modal available
  Given a valid document
  And the view has finished rendering
  When the user clicks the button named "Link to this article"
  Then there is a modal dialog titled "Links" visible

Scenario: the user can set the access date of the citations produced by the citation dialog
  Given a valid document
  And the view has finished rendering
  When the button named "Cite this article" is enabled
  And the user clicks the button named "Cite this article"
  Then there is a modal dialog titled "Cite" visible
  And the citations show the date from the access date field
  When the user clicks in the access date field
  Then there is a date picker visible
  When the user changes the date
  Then the citations show the date from the access date field
  And the MODS data has the correct access date field

Scenario: the user can choose the type of url of the citations produced by the citation dialog
  Given a valid document
  And the view has finished rendering
  When the button named "Cite this article" is enabled
  And the user clicks the button named "Cite this article"
  Then there is a modal dialog titled "Cite" visible
  And the citations show the url specified by the version-specific checkbox
  And the MODS data has the correct url
  When the user clicks the version-specific checkbox
  Then the citations show the url specified by the version-specific checkbox
  And the MODS data has the correct url
  When the user clicks the version-specific checkbox
  Then the citations show the url specified by the version-specific checkbox
  And the MODS data has the correct url

# In IE we get a prompt when we download a file. This prompt cannot be
# manipulated by Selenium, nor does there seem to be a way to prevent
# it.
@not.with_browser=ie
Scenario: the user can download the MODS record
  Given a valid document
  And the view has finished rendering
  When the button named "Cite this article" is enabled
  And the user clicks the button named "Cite this article"
  Then there is a modal dialog titled "Cite" visible
  When the user clicks the button named "Get the MODS Record"
  Then the MODS data is downloaded

Scenario Outline: the user can get citation records with correct authors
  Given a valid article, with <authors>
  And the view has finished rendering
  When the button named "Cite this article" is enabled
  And the user clicks the button named "Cite this article"
  Then there is a modal dialog titled "Cite" visible
  And the Chicago author names are "<chicago_authors>"
  And the MLA author names are "<mla_authors>"

  Examples:
  | authors       | chicago_authors        | mla_authors             |
  | one author    | Jane Doe               | Doe, Jane               |
  | two authors   | Jane Doe and John Doeh | Doe, Jane and John Doeh |
  | three authors | Jane Doe, John Doeh and Forename 3 Surname 3, GenName 3 | Doe, Jane, John Doeh and Forename 3 Surname 3, GenName 3  |
  | four authors  | Jane Doe, John Doeh, Forename 3 Surname 3, GenName 3 and Forename 4 Surname 4, GenName 4 | Doe, Jane, et al. |

Scenario Outline: the user can get citation records with correct editors
  Given a valid article, with <editors>
  And the view has finished rendering
  When the button named "Cite this article" is enabled
  And the user clicks the button named "Cite this article"
  Then there is a modal dialog titled "Cite" visible
  And the editor names are "<mla_editors>"

  Examples:
  | editors       | mla_editors            |
  | one editor    | Ed. Lovelace, Ada      |
  | two editors   | Eds. Lovelace, Ada and Forename 2 Surname 2, GenName 2 |
  | three editors | Eds. Lovelace, Ada, Forename 2 Surname 2, GenName 2 and Forename 3 Surname 3, GenName 3 |
  | four editors  | Eds. Lovelace, Ada, et al.  |

Scenario: the user can show and hide a semantic field popover by clicking on a semantic field button
  Given a valid document
  And the view has finished rendering
  When the user clicks the expand all button
  Then all collapsible sections are expanded
  When the user clicks the first semantic field button
  Then a semantic field popover is visible
  When the user clicks the first semantic field button
  Then a semantic field popover is not visible

Scenario: the user can hide a semantic field popover by clicking outside the popover
  Given a valid document
  And the view has finished rendering
  When the user clicks the expand all button
  Then all collapsible sections are expanded
  When wait 1 seconds
  When the user clicks the first semantic field button
  Then a semantic field popover is visible
  When the user clicks outside the semantic field popover
  Then a semantic field popover is not visible

Scenario: specified semantic fields are properly shown
  Given the user has logged in
  And a document with a specified semantic field
  And the view has finished rendering
  Then the cognate "one" has the semantic fields
    """
    Animals @ Written laws :: code of laws (01.05n@03.05.01|02n)
    """
