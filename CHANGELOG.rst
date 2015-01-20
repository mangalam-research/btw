* ?.?.?:

  + New features:

    - Display/Editing: use the purple to color
      btw:antonym-instance.

    - Display: foreign words are no longer italicized when displaying
      articles.

    - Display: Added a vertical space between a citation and its
      translation.

    - Display: removed the "SENSE" labels from the sense
      headings. Added a period after the letter.

    - Display: semantic fields sections are now collapsible.

    - Display: the contrastive sections are now collapsible. Same
      for their immediate subsections.

    - Display: clicking a hyperlink that happens to target a
      destination inside a collapsed section will automatically
      expand the section.

    - Display: reloading an article while a specific element is
      targeted will automatically expand the sections necessary to
      view the article.

    - Display: added a toolbar that contains the edit button (which
      appears only for authors), plus a button to expand all sections
      and a button to collapse all sections.

    - Display: bibliographical references are now hyperlinked.

    - Display: the semantic fields that are combined to form the list
      of all semantic fields for a section are now headed with "all
      semantic fields in this sense".

    - Display: headings that are not otherwise decorated now get
      bullets.

    - Display: the "other citations" section now appear in sections
      named "more citations".

    - Display: the semantic fields are now combined according to
      specifications.

    - Editing/Bibliography: previously, the filtering of
      bibliographical entries would perform a match on secondary
      sources and primary sources independently. So it was possible to
      have a match on a secondary source and have none of its
      associated primary sources match. Showing the primary sources of
      such a secondary source, after filtering, would show no primary
      source. It turns out this does not mesh well with the way the
      authors work, so the search is now changed so that if a
      secondary source matches, then all of its primary sources are
      also considered to match.

  + Bug fixes:

    - Display: a bug that prevented the display of primary source
      references has been fixed.

    - Infrastructure: When the Zotero server is not accessible at all
      due to a complete network outage, handle this situation
      gracefully by fetching the bibliographical entries from cache.

    - Editing: in the modal dialog created to insert bibliographical
      references, clicking the buttons to show or hide all primary
      sources would take the user out of editing. This has been fixed.
