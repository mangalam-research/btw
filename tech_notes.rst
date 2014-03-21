======
 TODO
======

* A module to assign genres to texts.

* When BTW has been used to produce articles for a bit, evaluate how
  to detect near-synonyms. See "Semantic fields for
  BTW2013_ldd_Reply".

* Support for Paul Hackett's AIBS API. See email from Jack circa
2013-06-09.

* Determine how to use X-Zotero-Write-Token. What constitutes a *same*
  transaction?

============
 Deployment
============

.. warning:: If you use uwsgi, use a version later than 1.2.6. See the
             warning on this page for the reason why:
             https://docs.djangoproject.com/en/1.5/howto/deployment/wsgi/uwsgi/

.. warning:: Using the sqlite3 backend with Django 1.5 and earlier can
             result in database problems because Django does not issue
             "BEGIN" commands to the database to explicitly begin
             transactions. BTW relies on transactions to ensure data
             integrity. Use Django 1.6 or use a backend other than
             sqlite3.

Server Setup
============

This documentation is based on installing BTW on Debian Wheezy. Later
versions of Debian or other distributions need these instructions
adapted to their specific case.

This documentation uses a virtual environment to allow for different
projects running different versions of libraries. This is not,
strictly speaking, necessary. If you do not want it, then you have to
adapt the instructions so as to not use virtualenv.

1. Install necessary packages::

    $ apt-get install uwsgi postgresql-9.1 postgresqlgit python-pip python-dev libffi-dev libxml2-dev libxslt1-dev make unzip libxml2-utils trang jing xsltproc

   We need the following packages from backports::

    $ apt-get -t wheezy-backports install nginx

2. Install ``/etc/apt/sources.list.d/tei.list`` from the config
   tree. Or add the following source to your apt sources::

    deb http://tei.oucs.ox.ac.uk/teideb/binary ./

3. Install uwsgi with pip::

    $ sudo pip install uwsgi

   This is needed because Debian Wheezy ships an outdated version of
   uwsgi. We are **also** installing the version shipped with Debian
   so that we get the whole service infrastructure, etc. However, we
   do this so that the infrastructure provided by the Debian package
   actually runs the version provided by pip::

    $ cd /usr/bin
    $ rm uwsgi
    $ ln -s ../local/bin/uwsgi .

   And we do this to prevent our links getting overwritten::

    $ apt-mark hold uwsgi

   It is **strongly** sugested to have apticron installed so that you
   get a warning once a new version of uwsgi is installed.

4. Add this key to the list of keys recognized by ``apt`` so that you
   don't get security issues with installing tei::

    pub   1024D/86A9A497 2001-11-27
    uid                  Sebastian Rahtz <sebastian.rahtz@oucs.ox.ac.uk>
    sub   1024g/BFABA9D0 2001-11-27

5. You can try connecting to the server on port 80 to see that nginx
   is running. Then stop nginx and::

    $ rm /etc/nginx/sites-enabled/default

6. Create a top directory for the site::

    $ mkdir /srv/www/<site>
    $ cd /srv/www/<site>

The above is just a suggestion. If you are doing this for Mangalam,
then you **must** consult the documentation on how to install a server
and check the section named "FS Structure" to use the proper
structure.

7. Create the virtual environment for BTW::

    $ cd /srv/www/<site>
    $ pip install virtualenv
    $ virtualenv btw_env

The Django Project
==================

Deploying Experimental Code
---------------------------

If you are deploying some sort of experimental version and you do not
want to push to a public server you can do the following::

1. ::

    $ cd /srv/www/<site>
    $ mkdir btw_repo
    $ cd btw_repo
    $ git init --bare

2. Add your public key into the ``~/.ssh/authorized_keys`` of the project
   account.

3. In your own personal repository, add the remote::

    $ git remote add [name] uid@site:/srv/www/<site>/btw_repo

4. In your own personal repository, push::

    $ git push [name]

5. On the server, clone::

    $ git clone btw_repo btw

Now you have a local copy of the code.

Deploying Published Code
------------------------

Execute::

    $ cd /srv/www/<site>
    $ git clone https://github.com/mangalam-research/btw.git

Installing
----------

1. Go into the top directory of the Django project you cloned (see above). Issue::

    $ ../btw_env/bin/pip install -r requirements.txt

2. Install some Node dependencies::

    $ npm install wed less

3. Use the virtual environment::

    $ source ../btw_env/bin/activate

4. Create a BTW environment for BTW. (This is the "environment" which
   determines which Django settings apply to BTW. See `Environment and
   Settings`_.) The database details will be determined after the
   database is created.

Database
--------

BTW needs to have its own database. We do not use MySQL/MariaDB due to
`complications with using UTF8
<https://docs.djangoproject.com/en/1.6/ref/databases/#collation-settings>`__.
The following instructions are for Postgresql 9.1, 9.3.

1. Create a user for it::

    $ sudo -u postgres createuser -P btw

Answer all questions negatively. Create a database::

    $ sudo -u postgres createdb -O btw btw

2. Optionally optimize the [connection](https://docs.djangoproject.com/en/1.6/ref/databases/#optimizing-postgresql-s-configuration).

.. note:: With the default configuration of postgres, you must connect either:

  * As a local user with the same name as a postgres user. In this
    case, postgres will takes authentication to the OS as
    authentication to the database. This is what happens when we do
    "sudo -u postgres createdb" for instance. No password is required
    by postgres.

  * Or as a network user using a password.

  Since we do not create a btw user on the machine, we must use the
  2nd option. Therefore all connections must be done by specifying
  ``localhost`` as the host.

3. Create a ``default`` database entry in the configuration::

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'btw',
            'USER': 'btw',
            'PASSWORD': 'whatever password',
            'HOST': '127.0.0.1'
        }
    }

  You probably want to put this inside a file local to your
  installation. See `Environment and Settings`_.

4. Run::

    ./manage.py syncdb

5. Run::

    ./manage.py migrate

6. Run::

    ./manage.py createcachetable bibliography_cache

7. Make sure that there is a site with id equal to the `SITE_ID` value
   from the settings, and a correct domain name and display name. In
   SQL, the command to do this would be something like::

    => update django_site set domain = '<name>', name='BTW' where id=<id>;

8. When deploying make sure the following Django settings are set as
   follows::

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

9. Make sure that the ``DEFAULT_FROM_EMAIL`` Django setting is set to
   the value you want to use as the ``From:`` field of emails sent for
   invitations to register to the site. Same with the ``SERVER_EMAIL``
   field. Note that they are probably not going to be the same value.

10. Make sure that the ``ADMINS`` Django setting is set properly.

11. Make sure that the ``BTW_WED_LOGGING_PATH`` and that any custom
    logging is done in ``/var/log/`` rather than in ``/srv``.

12. The file structure is::

    btw_env      The virtualenv environment created earlier.
    btw_repo     Possible repository you use if you are deploying experimental code.
    btw          Where you checked out btw.
    static       Where the static files are collected.
    media        Where media files are stored.

   So you must ensure that ``STATIC_ROOT`` and ``MEDIA_ROOT`` are set
   to point to these directories which are **above** ``TOPDIR``.

13. Run::

    $ ./manage.py collectstatic

14. Make sure the following environment variables are set as follows::

    HTTPS=on
    wsgi.url_scheme=https

Finalizing
----------

This needs to be done last because the ``Makefile`` may use
``manage.py``, which may require a complete configuration.

Run make::

    $ make

Upgrades
--------

Generally:

1. Run::

    $ ../btw_env/bin/activate
    $ ./manage.py syncdb
    $ ./manage.py migrate
    $ make

Nginx
-----

If needed, create some new server keys::

    $ cd /srv/www/<site>
    $ openssl genrsa -out ssl.key 2048
    $ openssl req -new -key ssl.key -out ssl.csr
    [Answer the questions to identify the machine. Leave the password blank.]
    $ openssl x509 -req -days 365 -in ssl.csr -signkey ssl.key -out ssl.crt

Install a proper configuration in
``/etc/nginx/sites-available/<site>``, and link it to the
``/etc/nginx/sites-enabled/`` directory. For Mangalam, the config tree
contains the file that has been used so far.

Uwsgi
-----

Install a proper configuration in
``/etc/uwsgi/apps-available/btw.ini``, and link it to the
``/etc/uwsgi/apps-enabled/`` directory. For Mangalam, the config tree
contains the file that has been used so far.

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

Zotero Tests
------------

The ``bibliography`` application communicates with the Zotero server
at ``api.zotero.org``. To avoid being dependent on a network
connection, on that server being up, on the account that was used to
create the tests being available, the test suite uses ``mitmdump``
(from the mitmproxy package) to record and replay interactions with
the server. The infrastructure needed for this is in
``bibliography.tests.util``.

.. warning:: Version 0.10 of mitmproxy **cannot** be used to *record*
             interactions with the Zotero server. It suffers from an
             `SSL bug
             <https://github.com/mitmproxy/netlib/issues/28>`__ which
             will presumably be fixed in netlib 0.11. (The versions of
             netlib and mitmproxy are in lockstep.) However, 0.10 can
             be used to *replay* them. So if you are not concerned
             with creating or modifying the tests you can ignore this
             problem.

Version 0.10 of ``mitmdump`` also suffers from a bug that makes
replaying fail unless we use the ``--no-pop`` option. However, when we
use ``--no-pop``, mitmproxy does not remove used match
request/response pairs. So if we issue two requests that are
considered *same* by ``mitmdump`` but we expect a *different*
response, replaying will fail because the first response will be
replayed twice. We work around this issue this way:

* At recording time, rewrite the saved requests to add a
``X-BTW-Sequence`` header field which is incremented with each
request.

* At replaying time, filter the requests made by the code being tested
  so that they gain a ``X-BTW-Sequence`` field which is incremented
  with each request.

* At replaying time, add ``--rheader X-BTW-Sequence`` so that request
  matching is performed on this field.

We can probably remove this workaround by the time mitmproxy 0.11 is
released.

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

Everything that follows is specific to BTW. You need to have `selenic
<http://github.com/mangalam-research/selenic>`_ installed and
available on your ``PYTHONPATH``. Read its documentation. Then you
need to create a `<local_config/selenium_local_config.py>`_ file. Use
one of the example files provided with selenic. Add the following
variable to your `<local_config/selenium_local_config.py>`_ file::

    # Location of the BTW server.
    SERVER = "http://localhost:8080"

You also need to have `wedutil
<http://github.com/mangalam-research/wedutil>`_ installed and
available on your ``PYTHONPATH``.

To run the Selenium-based tests, the tests must be able to communicate
with a live server. Tests that can pass locally can quite easily fail
when run from a remote service, *unless* a real web server is
used. Therefore, the test suite starts an nginx server because, let's
face it, **Django is not a web server.** Some issues that Django may
mask can become evident when using a real web server. This has
happened during the development of BTW.

.. note:: A "real web server" is one which understands the ins and
          outs of the HTTP protocol, can negotiate contents, can
          compress contents, understands caching on the basis of
          modification times, etc.

The configuration environment used for the selenium tests is named
``selenium``. See `Environment and Settings`_.

Nginx
-----

Internally, the test suite starts nginx by issuing::

    $ utils/start_nginx <fifo>

The fifo is a communication channel created by the test suite to
control the server.  The command above will launch an nginx server
listening on localhost:8080. It will handle all the requests to static
resources itself but will forward all other requests to an instance of
the Django live server (which is started by the ``start_nginx`` script
to listen on localhost:7777). This server puts all of the things that
would go in ``/var`` if it was started by the OS in the `<var>`_
directory that sits at the top of the code tree. Look there for
logs. This nginx instance uses the configuration built at
`<build/config/nginx.conf>`_ from `<config/nginx.conf>`_. Remember
that if you want to override the configuration, the proper way to do
it is to copy the configuration file into `<local_config>`_ and edit
it there. Run make again after you made modifications. The only
processing done on nginx's file is to change all instances of
``@PWD@`` with the top of the code tree.

The Django server started by `start_nginx` is based on
`LiveServerTestCase` and consequently organises its run time
environment in the same way. The test suite sends a signal to the
server so that with each new feature, the server resets itself. This
means that database changes do not propagate from feature to
feature. This mirrors the way the Django tests normally run. A test
will not see the database changes performed by another test.

Running the Suite
-----------------

To run the suite issue::

    $ make selenium-test

To run the suite while using the SauceLab servers, run::

    $ make SELENIUM_SAUCELABS=1 selenium-test

Behind the scenes, this will launch behave. See `<Makefile>`_ to see
how behave is run.

How to Modify Fixtures
----------------------

There is no direct way to modify the fixtures used by the Django tests
(this includes the live server tests which is used to run the Selenium
tests). The procedure to follow is::

    $ mv btw.sqlite3 btw.sqlite3.real

    $ ./manage.py syncdb

    $ ./manage.py migrate

    $ ./manage.py runserver

Repeat the following command for all fixtures you want to load or pass all fixtures together on the same command line::

    $ ./manage.py loaddata [fixture]

At this point you can edit your database. When you are done kill the
server, and dump the data as needed::

    $ ./manage.py dumpdata --indent=2 --natural [application] > [file]

Use git to make sure that the changes you wanted are there. Among
other things, you might want to prevent locking records and handles
from being added to the new fixture.  When this is done, you can
restore your database::

    $ mv btw.sqlite3.real btw.sqlite3

Before doing anything more, it is wise to run the Django tests and the
Selenium tests to make sure that the new fixture does not break
anything. It is also wise to immediately commit the new fixture to
git once the tests are passing.

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

* ``settings/settings.py``  BTW-wide settings

* ``settings/_env.py``      environment management

* ``settings/<app>.py``     settings specific to the application named <app>

The ``settings.py`` file inspects INSTALLED_APPS searching for local
applications and passes to ``exec`` all the corresponding ``<app>.py``
files it finds. Note that because these files are executed in
``settings.py``'s context, they can read and set variable that
``settings.py`` sets.

To allow for changing configurations easily BTW gets an environment
name from the following sources:

* the ``BTW_ENV`` environment variable

* ``~/.config/btw/env``

* ``/etc/btw/env``

This environment value is then used by ``_env.find_config(name)`` to find
configuration files:

* ``~/.config/btw/<name>_<env>.py``

* ``/etc/btw/<name>_<env>.py``

The **first** file found among the ones in the previous list is the
one used. By convention ``_env.find_config`` should be used by the files
under the settings directory to find overrides to their default
values. The ``<name>`` parameter should be "btw" for global settings or
the name of an application for application-specific settings. Again by
convention the caller to find_config should exec the value returned by
``find_config`` **after** having done its local processing.

The order of execution of the various files is::

    settings/__init__.py
    <conf>/btw_<env>.py
    settings/<app1>.py
    <conf>/<app1>_<env>.py
    settings/<app2>.py
    <conf>/<app2>_<env>.py

where ``<env>`` is the value of the environment set as described
earlier, and ``<conf>`` is whatever path happens to contain the
configuration file.

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
