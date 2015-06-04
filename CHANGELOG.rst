* 1.2.0:

  + New features:

   - Upgraded to Django 1.7.x.

   - Added of Django CMS 3.1 for managing the informational pages.

* 1.1.0:

  + New features:

   - The insertion of bibliographical references is now done with a
     typeahead field rather than a modal dialog.

   - The buttons for creating new elements ("Create new btw:...") in
     the body of the article are now present in more locations.

   - When viewing an unpublished article there is an alert box at the
     top indicating that the article is unpublished.

   - Updated the links on the front page. Added the link to the video
     and the HTE logo.

   - The management page for the bibliography now has a "refresh"
     button. BTW checks the Zotero database about every 30 minutes to
     check for changes. In a case where someone is fixing a problem in
     the Zotero database and wants the change to appear immediately on
     BTW, they can use the refresh button to force BTW to check the
     Zotero database.

   - Upgraded to the Zotero API version 3, which is the latest version
     at the time of writing. (Version 2 was previously used.)

   - Infrastructure: the way BTW keeps its database of bibliographical
     information in sync with the Zotero database has been redesigned
     to help interactivity. The old implementation could sometimes
     cause a slowdown in the delivery of pages to users. The new
     implementation avoids this problem.

   - Infrastructure: BTW instances no longer share the Redis cache.

   - Upgrade to wed 0.24.2. The salient changes are:

     * Upgrade to Font Awesome 4.3.0.

     * The icon for an element's documentation is now
       fa-question-circle rather than fa-book.

     * Support for typahead popups.

* 1.0.4:

  + Bug fixes:

   - Prevents the "Terms in this section:" heading from appearing in
     the table of contents of articles.

  + New features:

   - Filter the text that is entered in articles so as to remove
     zero-width spaces and convert non-breaking spaces to normal
     spaces.

  + Miscellaneous:

   - Upgrade to Bootstrap 3.3.2.

* 1.0.3:

  + Bug fixes:

    - Display: prevent the navigation menu in article display from
      popping out of place if the display is resized too small. When
      the display is resized beyond a certain limit, the navigation
      menu collapses on the right of the screen and has to be expanded
      for use.

  + New features:

    - Display: better demarcation between the list of contrastive
      terms that appear in the sections for each kind of contrastive
      term (antonyms, cognates, conceptual proximates). The list is
      now introduced by a heading ("Terms in this section:") and
      separated from the terms by a horizontal rule.

* 1.0.2:

  + Bug fixes:

    - Display: prevent the navigation menu in article display from
      popping out of its place. This is a temporary measure. A fuller
      solution is upcoming.

* 1.0.0:

  + New features:

    - Hyperlinking between articles. BTW now automatically creates
      hyperlinks to other articles. Hyperlinks are created for
      antonyms, cognates and conceptual proximates or for sanskrit
      terms that appear in the overview of the article.

* 0.8.0:

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
