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
  Then the chosen semantic fields are "Travel and travelling (03.10n)", "Animals (01.05n)", "code of laws (03.05.01|02n)"
  When the user clicks on the "Commit" button in the modal dialog
  Then the document contains the fields "Travel and travelling (03.10n)", "Animals (01.05n)", "code of laws (03.05.01|02n)"
