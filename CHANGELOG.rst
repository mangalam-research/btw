* 2.1.0:

  + Upgrade from Django 1.10 to Django 1.11. This entailed upgrading
    also a series of packages we use with Django.

* 2.0.0:

  + Upgrade from Django 1.8 to Django 1.10. Django 1.10 has features
    that were needed by BTW.

  + Upgrade from Django CMS 3.2.3 to 3.4.1. This was required by the
    move to Django 1.10.

  + New features:

    - It is possible to create new BTW-specific custom fields.

    - BTW now has a site-wide error catcher which a) prevent software
      errors from going undetected, b) will help in diagnosing
      problems.

    - Added eXist-db ("eXist", for short) to BTW to allow for a
      full-featured full text search facility and to support searches
      that are aware of the structure of XML documents.

    - Search in lexicographical articles now uses eXist, can make
      use of the Lucene search syntax and provide context with the
      hits.

    - Semantic fields in displayed articles are now buttons which
      bring up a popover of links to other articles when clicked.

    - English renditions no longer accept semantic fields when
      editing. For displaying articles, the fields are added to
      English renditions by software.

    - Semantic field editing in articles is now done with a modal
      dialog rather than by typing field numbers directly in the
      article.

    - BTW now performs automatic cleaning of old records.

* 1.4.1:

  + Upgrade from Django 1.7 to Django 1.8. This could no longer be
    delayed because earlier versions of Django are no longer
    supported.

  + Upgrade to Django CMS 3.2.3. This brings some important security
    fixes.

  + Upgrade to wed 0.26.2: this fixes an issue with Chrome 50.

* 1.4.0:

  + This the "interim HTE integration" release.

  + Browser support:

    - Chrome, on all platforms, is the browser of choice for accessing
      BTW. IE11 is also supported.

    - Support for Firefox on all platforms has been temporarily
      suspended. Selenium is no longer able to accurately simulate
      real user interaction with Firefox browsers. The problem is most
      likely fixable, but we do not have the resources to fix
      Selenium.

    - IE11 support has been significantly improved.

    - IE10 is no longer supported, as Microsoft itself has pulled
      support for it.

    - Edge is not yet supported because the service we use to test
      browsers (Sauce Labs) does not yet fully support it.

  + BTW now incorporates the HTE database of semantic fields into its
    own database.

  + BTW now shows semantic field names when displaying articles to users.

  + The separator between semantic fields is now a double semi-colon
    rather than a single semi-colon.

  + BTW also now has facilities for searching semantic fields but
    these facilities are not yet available for general use.

  + Upgrades:

    - Wed 0.26.1: brings many improvements to IE11 support, and bug
      fixes.

    - Salve 2.0.0: supports a greater part of Relax NG than previous
      versions.

    - Over a dozen upgrades to the third-party libaries used by BTW
      (Bootstrap, DataTables, Kombu, etc.)

  + Bug fix: when viewing articles, the button for editing articles
    was always shown whether editing was possible or not. This bug was
    purely a **cosmetic** issue, and never permitted editing articles
    in cases where editing should have been prevented. For instance,
    if editing was not allowed because a user did not have
    permissions, then clicking the spurious button would have caused
    the browser to try to access a non-existent page.

  + Bug fix: a CSS file was missing from the administration interface
    that shows ``ChangeRecord`` objects. This caused the notification
    that is shown for revert operations to appear incorrectly on the
    screen. This has been fixed. (This problem was visible only to
    site administrators. At the time of writing, there is only one
    administrator.)

* 1.3.1:

  + Bug fix: Fix in the permission checks for accessing the general search in
    the bibliography part of BTW.

  + Infrastructure feature: new administrative command to generate a
    monit file that can be used to cleanly start/stop and restart BTW.

  + Infrastructure bug fix: purge previously scheduled Celery tasks
    when starting the workers.

* 1.3.0:

  + Change in nomenclature:

   - Previous versions of BTW and its documentation referred to people
     who could edit articles as "authors". With the addition of the
     capability to record credits, we've decided that saying "author"
     to refer to the capability to edit articles could lead to
     confusion because people who can edit articles are not all
     strictly speaking "authors" of the articles. (For instance, I can
     edit all articles on BTW but I did not author any of them.)

     From now on, we use the generic term "scribe" to refer to those
     people who are allowed by BTW to edit articles on BTW,
     irrespective of what their specific role is. They can be authors,
     proofreaders, typists, site administrators, etc.

  + New features:

   - BTW now has a Django CMS plugin that provide the BTW-as-a-whole
     citation functionality.

   - Articles now have the means to record credits (authors, editors).

   - Unpublishing an article now gives a warning. With the addition of
     the permalink and citation functionality, it is likely that some
     readers of BTW will incorporate in their own work links to
     versions of articles that may be later superseded by newer
     versions. Unpublishing would break those links. So a warning is
     presented reminding that unpublishing should be done only in
     exceptional circumstances.

   - Scribes now see the schema version of an article in the search
     table. There is also a visual warning if an article is stored in
     an earlier version of the schema.

   - The lemma of an article is now included in the HTML title shown
     when viewing the page. (This is the HTML title, which becomes the
     title of the browser window or tab. Articles have always had the
     lemma prominently displayed at the top of the article itself.)

   - When displaying an article, BTW now includes:

     - An "Article History" button which allows the user to see the
       article's publishing history.

     - A "Link to this article" button which allows the user to get
       the permalinks of the article: a non-version-specific permalink
       which always points to the latest published version of the
       article, and a version-specific permalink which points to the
       specific version being viewed.

     - A "Cite this article" button which presents the user with two
       bibliographical entries for this article preformatted according
       to the Chicago Manual of Style and the MLA standards. It also
       allows downloading the bibliographical information of the
       article in the MODS format, which can then be loaded in
       bibliographical management software.

     - When viewing:

       ~ For everyone: if someone is viewing a published version of an
       article but there is a newer published version, they get a
       warning and a link to the newest published version.

       ~ For scribes: the warning they get when they look at an
       unpublished version now includes a link to the latest published
       version. (This warning already existed in previous versions of
       BTW but did not include the link.)

       ~ For scribes: they get a warning if there is a newer
       unpublished version of an article, and the warning contains a
       link to this newer version.

  + Upgrades:

    - Upgrade to wed 0.24.3. This introduces some bug fixes with how
      wed handles validation errors.

    - Manu upgrades to the software libraries that BTW uses.

* 1.2.1:

  + Bug fixes:

    The introduction of Django CMS introduced language prefixes in
    URLs. This caused some hyperlinking code in btw_view to fail recognizing
    links between articles and creating hyperlinks. This fixes the problem.

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
