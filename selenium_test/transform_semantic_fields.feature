Feature: the user wants to be able to edit semantic fields in articles.

Scenario: cancelling an edit
  Given a document with some semantic fields
  And the document contains the fields "Travel and travelling (03.10n)", "Animals (01.05n)"
  When the user brings up the semantic field editing dialog
  And the user cancels the dialog
  Then the document contains the fields "Travel and travelling (03.10n)", "Animals (01.05n)"

Scenario: making an edit
  Given a document with some semantic fields
  And the document contains the fields "Travel and travelling (03.10n)", "Animals (01.05n)"
  When the user brings up the semantic field editing dialog
  Then the chosen semantic fields are "Travel and travelling (03.10n)", "Animals (01.05n)"
  When the user searches for "Law"
  Then there are 3 results
  When the user clicks on "code of laws (Noun)" in the first result
  Then there is one detail pane
  When the user clicks on the add button in the first detail pane
  Then the chosen semantic fields are "Travel and travelling (03.10n)", "Animals (01.05n)", "Written laws :: code of laws (03.05.01|02n)"
  When the user clicks on the "Commit" button in the modal dialog
  Then the document contains the fields "Travel and travelling (03.10n)", "Animals (01.05n)", "Written laws :: code of laws (03.05.01|02n)"

Scenario: adding semantic fields to a document that has none
  Given a document with an antonym with citations
  And the document does not contain any semantic fields
  When the user clicks on the visible absence for btw:semantic-fields
  And the user brings up the semantic field editing dialog
  When the user searches for "Law"
  Then there are 3 results
  When the user clicks on "code of laws (Noun)" in the first result
  Then there is one detail pane
  When the user clicks on the add button in the first detail pane
  Then the chosen semantic fields are "Written laws :: code of laws (03.05.01|02n)"
  When the user clicks on the "Commit" button in the modal dialog
  Then the document contains the fields "Written laws :: code of laws (03.05.01|02n)"

Scenario: dismissing the dialog using the top close button
  Given a document with an antonym with citations
  And the document does not contain any semantic fields
  When the user clicks on the visible absence for btw:semantic-fields
  And the user brings up the semantic field editing dialog
  When the user searches for "Law"
  Then there are 3 results
  When the user clicks on "code of laws (Noun)" in the first result
  Then there is one detail pane
  When the user clicks on the add button in the first detail pane
  Then the chosen semantic fields are "Written laws :: code of laws (03.05.01|02n)"
  When the user dismisses the modal by using the close button in the modal header
  Then the document does not contain any semantic fields
