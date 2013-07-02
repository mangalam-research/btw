;; Macros used for the prasāda conversion.

(fset 'btw-split-semantic-fields
   [?\C-s ?\; left ?\C-d ?\C-d return tab])

(fset 'btw-insert-sf-elements
   [tab ?< ?b ?t ?w ?: ?s ?f ?> ?\C-e ?< ?/ escape tab down ?\C-a])
