======
 TODO
======

* A module to assign genres to texts.

* When BTW has been used to produce articles for a bit, evaluate how to detect near-synonyms. See "Semantic fields for BTW2013_ldd_Reply".

* Support for Paul Hackett's AIBS API. See email from Jack circa
2013-06-09.

* Determine how to use X-Zotero-Write-Token. What constitutes a *same* transaction?

==============
 Installation
==============

.. warning:: If you use uwsgi, use a version later than 1.2.6. See the
             warning on this page for the reason why:
             https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/uwsgi/

.. warning:: Using the sqlite3 backend with Django 1.5 and earlier can
             result in database problems because Django does not issue
             "BEGIN" commands to the database to explicitly begin
             transactions. BTW relies on transactions to ensure data
             integrity. Use Django 1.6 or use a backend other than
             sqlite3.

=========
 Testing
=========

Note that due to the asynchronous nature the JavaScript environments
used to run the tests, if the test suites are run on a system
experiencing heavy load or if the OS has to swap a lot of memory from
the hard disk, they may fail some or all tests. I've witnessed this
happen, for instance, due to RequireJS timing out on a ``require()``
call because the OS was busy loading things into memory from
swap. The solution is to run the test suites again.

Another issue with running the tests is that wed uses ``setTimeout``
to do the validation work in a parallel fashion. (This actually
simulates parallelism.) Now, browsers clamp timeouts to at most once a
second for tests that are in background tabs (i.e. tabs whose content
is not currently visible). Some tests want the first validation to be
finished before starting. The upshot is that if the test tab is pushed
to the background some tests will fail due to timeouts. The solution
for now is don't push the tab in which tests are run to the
background. Web workers would solve this problem but would create
other complications so it is unclear whether they are a viable
solution.

Tests are of three types:

* Django tests, which run outside the browser.

* In-browser tests, which run *in* the browser.

* Selenium-based tests, which run *outside* the browser but use Selenium
  to control a browser.

Django Tests
============

::
    $ ./manage.py test

.. warning:: Running this command does not rebuild the software. So if
             you make changes that must propagate to your live version
             of the server then you must run ``make`` first.

In-Browser Tests
================

::
    $ ./manage.py runserver

Then run a QUnit test by pointing your broswer to
http://localhost:8000/search/tests/

.. warning:: Running this command does not rebuild the software. So if
             you make changes that must propagate to your live version
             of the server then you must run ``make`` first.

Selenium-Based Tests
====================

The following information is not specific to BTW but can be useful if
you've never used Selenium before. Generally speaking, you need the
Selenium Server, but if you only want to run tests in Chrome, you only
need chromedriver. Selenium Server can be found on `this page
<http://code.google.com/p/selenium/downloads/list>`__. It has a name
like ``selenium-server-standalone-<version>.jar``. Chromedriver is
`here <https://code.google.com/p/chromedriver/downloads/list>`__. The
documentation for its use is `here
<http://code.google.com/p/selenium/wiki/ChromeDriver>`__.

Everything that follows is specific to BTW. The first thing you need
to do is copy `<config/selenium_local_config.py>`_ to
`<local_config/selenium_local_config.py>`_ and edit it. If you want to
use SauceLab's servers, set ``SAUCELABS_CREDENTIALS`` to your
credentials on SauceLab. (Of course, you must have a SauceLab
account.) If you use chromedriver you want to set
``CHROMEDRIVER_PATH`` to the path where it resides.

To run the Selenium-based tests, you must use a Django live server set
up for testing. This server can work in standalone mode *or* behind an
nginx server. The latter option is highly recommended, especially if
you run your browser on a provisioning service like SauceLabs. Tests
that can pass locally can quite easily fail when run from a remote
service, *unless* a real web server is used. The nginx setup is
recommended in any case because, let's face it, **Django is not a web
server.** Some issues that Django may mask can become evident when
using a real web server. This has happened during the development of
BTW.

.. note:: A "real web server" is one which understands the ins and
          outs of the HTTP protocol, can negotiate contents, can
          compress contents, understands caching on the basis of
          modification times, etc.

Standalone
----------

Running ``./manage.py runserver`` would run the tests on the database
which you use for development. Not a good deal. So instead you should
run::

    $ ./manage.py test utils/liveserver_test.py

This will create a live server and wait until it dies. Yes, that's a
quick and dirty hack. At any rate the server will be ready to handle
the test suite.

Nginx
-----

To run nginx, just issue::

    $ utils/start_nginx

This will launch an nginx server listening on localhost:8080. It will
handle all the requests to static resources itself but will forward
all Ajax stuff to an instance of the Django live server (which is
started by the ``start_nginx`` script to listen on
localhost:7777). This server puts all of the things that would go in
``/var`` if it was started by the OS in the `<var>`_ directory that
sits at the top of the code tree. Look there for logs. This nginx
instance uses the configuration built at `<build/config/nginx.conf>`_
from `<config/nginx.conf>`_. Remember that if you want to override the
configuration, the proper way to do it is to copy the configuration
file into `<local_config>`_ and edit it there. Run make again after
you made modifications. The only processing done on nginx's file is to
change all instances of ``@PWD@`` with the top of the code tree.

Running the Suite
-----------------

Finally, to run the suite issue::

    $ make selenium-test

To run the suite while using the SauceLab servers, run::

    $ make SELENIUM_SAUCELABS=1 selenium-test

Behind the scenes, this will launch behave. See `<Makefile>`_ to see
how behave is run.

==============
 User Stories
==============

US1 As an author, when I want to insert a reference to a secondary
source, I want to be :

* US1.1 able to select a secondary source I've already referred to in
  my article, either by the abbreviation I've assigned to it or by
  bibliographical data.

* US1.2 able to search among the secondary sources that BTW already
  uses for other articles.

* US1.3 able to search in my own personal bibliographical database.

* US1.4 able to assign an abbreviation to a secondary source I've
  selected.

US2 As an author, when I want to insert a reference to a primary
source, I want to be:

* US2.1 able to select a primary source I've already referred to in my
  article, either by the abbreviation I've assigned to it or by
  bibliographical data.

* US2.2 able to search among the primary sources that BTW already uses
  for other articles.

* US2.3 able to search in my own personal bibliographical database.

* US2.4 able to assign an abbreviation to a primary source I've
  selected.

US3 As an author, I want to be unable to assign the same abbreviation
to two different entities.

US4 As an author, I want to be able to undefine an abbreviation I've
created by mistake.

US5 As an author, I want to be able to rename an abbreviation I've
created by mistake.

US6 As an author, I want to be able to assign a string expansion to an
abbreviation.

US7 As an author, I want to be unable to assign the *same* string
expansion to two *different* abbreviations.

US8 As an author, I want to be unable to create duplicate entries with
the same headword.

US9 As an author, when editing I want to:

* US9.1 be able to mark words as Sanskrit, Tibetan, etc.

* US9.2 be able to unmark works as Sanskrit, Tibetan, etc.

* US9.3 have the editor automatically mark words I've already marked elsewhere in the text.

* US9.4 have the editor flag words that should probably be marked.

* US9.5 have the editor automatically create links to terms for which we have articles.

US10 As an author, when editing I want to:

* US10.1 be able to undo operations.

* US10.2 be able to redo operations.

* US10.3 have undo and redo steps make sense from my perspective. For instance, if I search and replace the word "potato" with "tomato", there are 10 instances, and I replaced these instances in one click, I should be able to undo this with one undo, not 10.

* US10.4 be able to revert my edits to a previous version of the article.

* US10.5 be able to go back and forth among versions of the article.

* US10.6 be able to know who is responsible for committing a version of an article.

* US10.7 be able to see differences between versions of an article.

* US10.8 be able to know who is responsible for what changes in an article.

US11. As an author I want to be unable to accidentally delete uneditable text.

US12. As an author, I want to be unable to accidentally move text generated by the editing environment but that should remain anchored. (For instance, if a structure has an automatically generated label at the beginning of it, I should not be able to move that label.)

U13. As an author, I want to see opening and closing labels for elements that are not clearly represented through styling.

U14. As an author, I want to:

U14.1 to unwrap an element (delete the start and end tag, while preserving the contents).

U14.2 delete an element (delete start, end tags and contents).

U14.3 wrap a selection into an element.

As a visitor, I want to be able to search through article headwords.

As a visitor, I want to be able to search through article text. (Full-text search.)

As a visitor, I want to be able to click on a search result and see the article.

As a visitor, I want to be able to have the referent of an abbreviation be displayed.

As a visitor, I want to be able to follow hyperlinks to other resources or articles.


==========================
 Environment and Settings
==========================

Structure of the settings tree in BTW:

settings/__init__.py  BTW-wide settings
settings/_env.py      environment management
settings/<app>.py     settings specific to the application named <app>

The __init__.py file inspects INSTALLED_APPS searching for local
applications and **exec**s all the corresponding <app>.py files it
finds. Note that because these files are execed in __init__.py's
context, they can read and set variable that __init__.py sets.

To allow for changing configurations easily BTW gets an environment
name from the following sources:

* the BTW_ENV environment variable

* ~/.config/btw/env

* /etc/btw/env

This environment value is then used by _env.find_config(name) to find
configuration files:

* ~/.config/btw/<name>.<env>.py

* /etc/btw/<name>.<env>.py

The **first** file found among the ones in the previous list is the
one used. By convention _env.find_config should be used by the files
under the settings directory to find overrides to their default
values. The <name> parameter should be "btw" for global settings or
the name of an application for application-specific settings. Again by
convention the caller to find_config should exec the value returned by
find_config **after** having done its local processing.

The order of execution of the various files is:

settings/__init__.py
<conf>/btw.<env>.py
settings/<app1>.py
<conf>/<app1>.<env>.py
settings/<app2>.py
<conf>/<app2>.<env>.py

where <env> is the value of the environment set as described earlier,
and <conf> is whatever path happens to contain the configuration file.

=======
 Roles
=======

+-----------+-------------------+--------------------------+
|BTW Role   |Django group(s)    |Notes                     |
+-----------+-------------------+--------------------------+
|visitor    |-                  |                          |
+-----------+-------------------+--------------------------+
|user       |-                  |This is an abstract       |
|           |                   |role. So no group.        |
+-----------+-------------------+--------------------------+
|author     |author             |                          |
+-----------+-------------------+--------------------------+
|editor     |editor             |                          |
+-----------+-------------------+--------------------------+
|superuser  |                   |Django superuser flag on. |
+-----------+-------------------+--------------------------+

**FUTURE** Initial versions of BTW will only allow the superuser(s) to
create new users. Later version should have an interface to streamline
this.


========
 Zotero
========

Zotero's current search facilities are extremely primitive:

* The q parameter has no functionality for AND and OR operators. If the parameter is repeated, the query passed to the backend will just be mangled.

Zotero's use by BTW
===================

We will create at zotero.org an account for BTW in which we will
create a BTW group that will contain all the entries that BTW wants to
use.

A BTW contributor will have to:

1. Have a Zotero library accessible on Zotero.org.

2. Create a key for BTW to access that library.

3. Record in BTW their Zotero.org user ID and the key they want BTW to use.

Then they will log into BTW and:

1. Search their Zotero library for their entry.

2. Tell BTW to use this entry.

At this point BTW will copy the entry from the user's library to BTW's own library and assign a unique identifier to the entry (with user prompt; perhaps semi-automated; or put into a queue for an editor to vouch for the identifier).


=================
 Version Control
=================

Must keep in sync:

* Article contents.

* Items the article points to:

 * Abbreviations.

 * Bibliographical records.

 * Textual sources.


==========
 Database
==========

auth_user
=========

abbreviations
=============

..  LocalWords:  uwsgi sqlite backend Django init py env config btw
..  LocalWords:  Zotero Zotero's zotero BTW's auth
