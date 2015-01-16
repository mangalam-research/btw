======
 TODO
======

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

.. warning:: BTW works only with Postgresql. SQLite is too
             primitive. MySQL could probably work, but see `the
             complications with using UTF8
             <https://docs.djangoproject.com/en/1.6/ref/databases/#collation-settings>`__. See
             also `this discussion
             <https://news.ycombinator.com/item?id=7317519>`__ for
             just how likely MySQL is to bite you in the ass if you
             try to do anything serious with Unicode. Unicode support
             is straightforward with Postgresql, so we settled on
             Postgresql. The following instructions are for Postgresql
             9.1, 9.3. If you deploy on MySQL and it breaks, you've
             been warned.

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
   get a warning once a new version of uwsgi is available.

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

The above directory is just a suggestion. If you are doing this for
Mangalam, then you **must** consult the documentation on how to
install a server and check the section named "FS Structure" to use the
proper structure.

7. Create the virtual environment for BTW::

    $ cd /srv/www/<site>
    $ pip install virtualenv
    $ virtualenv btw_env

.. warning:: As of 07292014 the server over at ``tilaa.nl`` requires
             that there be a file named ``/srv/www/btw.tilaa.nl``
             which is a symlink to the ``/srv/www/<site>`` directory
             above. This is because the address for BTW changed from
             ``btw.tilaa.nl`` to ``btw.mangalamresearch.org`` (on
             07292014). A virtual environment is not movable so the
             symlink is there to keep the virtual environment
             happy. One day, when a new environment is created, the
             link can be removed.

The Django Project
==================

Deploying Experimental Code
---------------------------

If you are deploying some sort of experimental version and you do not
want to push to a public server you can do the following::

1. Create a repository on the site. You need this repository because
   when you push to it it will be populated with repository files
   rather than a working tree::

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

5. On the server, clone (this will create the working tree)::

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

    $ npm install wed less lodash argparse

3. Use the virtual environment::

    $ source ../btw_env/bin/activate

4. Create a BTW environment for BTW. (This is the "environment" which
   determines which Django settings apply to BTW. See `Environment and
   Settings`_.) The database details will be determined after the
   database is created.

Database
--------

BTW needs to have its own database.

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

13. Make sure the following environment variables are set as follows
    in the uwsgi configuration::

    HTTPS=on
    wsgi.url_scheme=https

Finalizing
----------

This needs to be done last because the ``Makefile`` may use
``manage.py``, which may require a complete configuration.

Run make::

  $ make

Demo Site
---------

Make sure that the site name in the sites table is properly set. Make
sure that anything that depends on the location of STATIC_URL is
properly set.

If you are going to move over users then:

1. Go to the regular site and run::

     $ ./manage.py dumpdata --natural auth allauth > [dump]

2. Go to the demo site and run::

     $ ./manage.py loaddata [dump]

If you are going to move over articles from the dev site the
bibliographical data must be moved over first:

1. Go to the dev site and run::

     $ ./manage.py dumpdata --natural bibliography > [dump]

2. Go to the demo site and run::

     $ ./manage.py loaddata [dump]

Upgrades
--------

Dealing with Logged-in Users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before upgrading, consider the impact on currently logged in
users. The following cases are possible:

1. No database change: there is no need to put the server in
   maintenance mode. Just upgrade the Python and Javascript code. If a
   new version of the wed editor is needed, the users will get a
   message asking to reload.

2. Database change:

   a. Establish a time at which the server will go into
   maintenance mode, tell the users.

   b. At the appointed time, set the nginx server configuration for
   BTW to be in maintenance mode.

   c. Use the ``logout`` management command to log all users out.

   d. Perform the code upgrade as needed.

   e. Get nginx out of maintenance mode.

Upgrade Proper
~~~~~~~~~~~~~~

Generally:

1. Make sure all your changes are pushed to the repository.

2. Make sure you have tagged the current release with ``git tag
   v... -a`` The ``-a`` is important to create an annotated tag.

3. Make sure you have a current backup of the database.

4. Run::

    $ git fetch origin --tags
    $ git pull origin
    $ git describe
    [Make sure the description shows what you expect.]
    $ ../btw_env/bin/activate
    $ ./manage.py syncdb
    $ ./manage.py migrate
    $ npm outdated
    [Upgrade anything that needs upgrading.]
    $ make

5. Reload uwsgi::

     $ sudo service uwsgi reload

See below for specific upgrade cases.

0.7.1 to 0.8.0(???)
-------------------

1. Issue the management command:

   $ ./manage.py btwdb mark_all_bibliographical_items_stale

0.0.2 to 0.1.0
--------------

1. Delete the database table ``biblliography_item``. This is okay
   because the BTW software has not yet been used in production.

2. Perform the general steps.

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

Create the Test Database
------------------------

To speed up testing, we set things up so that the test database is not
recreated with each run of the test suite. This means that you must
create the database yourself and maintain it. First you must create a
database::

  $ sudo -u postgres createdb -O btw_develop test_btw_develop

[Verify in your own configuration the name of the user and the name of
the database you should create. ``test_settings`` adds ``test_`` to
whatever name you use for the development database.]

Create the tables::

  $ ./manage syncdb --settings=btw.test_settings
  $ ./manage migrate --settings=btw.test_settings
  $ ./manage.py createcachetable bibliography_cache --settings=btw.test_settings


Running the Tests
-----------------

You should be using ``make`` to run the tests rather than
``./manage.py test`` because some of the tests are dependent on files
that are generated with ``make``::

    $ make test

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

    $ make selenium-test TEST_BROWSER='OS,BROWSER,VERSION'

where ``OS,BROWSER,VERSION`` is a combination of
``OS,BROWSER,VERSION`` present in ``config/browser.txt``.

Behind the scenes, this will launch behave. See `<Makefile>`_ to see
how behave is run.

How to Modify Fixtures
----------------------

There is no direct way to modify the fixtures used by the Django tests
(this includes the live server tests which is used to run the Selenium
tests). The procedure to follow is::

1. Move your development database to a different location
   temporariy. **Or** modify the development environment so that the
   development server connects to a temporary, different database.

2. Issue::

    $ ./manage.py syncdb

    $ ./manage.py migrate

    $ ./manage.py runserver

3. Repeat the following command for all fixtures you want to load or
   pass all fixtures together on the same command line::

    $ ./manage.py loaddata [fixture]

4. At this point you can edit your database.

5. Run a garbage collection to remove old chunks that are no longer
   referred.

6. When you are done kill the server, and dump the data as needed::

    $ ./manage.py dumpdata --indent=2 --natural [application] > [file]

Use git to make sure that the changes you wanted are there. Among
other things, you might want to prevent locking records and handles
from being added to the new fixture.  When this is done, you can
restore your database to what it was.

Before doing anything more, it is wise to run the Django tests and the
Selenium tests to make sure that the new fixture does not break
anything. It is also wise to immediately commit the new fixture to
git once the tests are passing.

Utility for Extractig Documents from Fixtures
---------------------------------------------

The ``html_from_json`` utility can be used to extract the latest XHTML
representing the data of an entry that has been saved into a ``.json``
file. This can then be used with the raw editing capability to import
this entry into the development database. Make sure to check the box
``Data entered in the editable format (XHTML) rather than the
btw-storage format (XML)`` before submitting the raw edit, or the edit
will fail.

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

* An ``env`` file at the top of the Django project hierarchy.

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
BTW Mode
========

Visible Absence
---------------

A "visible absence" is an absence of an element which is represented
as a *presence* in the edited document. If ``<foo>`` might contain
``<bar>`` but ``<bar>`` is absent, the usual means to represent this
would be a ``<foo>`` that does not contain a ``<bar>``. With a visible
absence, ``<foo>`` would contain a GUI element showing that ``<bar>``
is absent.

A "visible absence instantiator" is a visible absence which is also a
control able to instantiate the absent element.

IDs
---

For hyperlinking purposes, elements have to be assigned unique
IDs. There are two types of IDs:

* The "wed ID", a.k.a. the "GUI ID". This is an ``id`` attribute that
  exists only in the GUI tree, which is assigned to all elements that
  need labeling through a reference manager. Or it may be assigned for
  other reasons that have to do with presentation in the editor.

* The "data ID". This is an ``id`` attribute that exists only in the
  data tree. This is what preserves hyperlinking between editing
  sessions.

The wed ID is derived from the data ID as follows:

* If there is a data ID, then the wed ID is "BTW-" + the value of the
  data ID.

* If there is no data ID, then the wed ID is "BTW-" + a unique number.

A data ID is assigned only if an element is hyperlinked.

===================
Management Commands
===================

transform
=========

This ``lexicography`` command is used to perform a batch
transformation on all articles. This is a very powerfull tool but can
severely damage your database if misused. It would be used, for
instance, if there is a need to change the schema under which articles
are stored and here is no plan for backward compatibility.

.. warning:: This command has not been thorougly tested yet.

The procedure to use it is:

1. Kick all users out of the system and prevent them from logging in.

2. Back up the database.

3. Create a directory in which you'll put:

  a. A ``before.rng`` file that contains the schema to which articles
     must conform before the transformation.

  b. An ``after.rng`` file that contains the schema to which articles
     must conform after the transformation.

  c. A ``transform.xsl`` file that contains the transformation to
     apply. (XSLT version 2, please.)

4. Test your transformation on some representative XML first.

5. Run in ``noop`` mode::

        $ ./manage.py transform --noop <path>

   where ``<path>`` is the directory that contains the files above.

6. Inspect the files in the ``log`` subdirectory created under
   ``<path>``. Files under it are of this form:

        - ``<hash>/before.xml``: XML before transformation.

        - ``<hash>/after.xml``: XML after transformation.

        - ``<hash>/BECAME_INVALID``: Indicates the chunk became
          invalid after the transformation.

   where ``<hash>`` is a chunk's original hash. In particular, search
   for ``BECAME_INVALID`` files, which indicate that a chunk that was
   valid *before* the transformation became invalid *after*, which
   means your transformation was incorrect.

7. You may also wish to perform ``diff`` between the ``before.xml``
   and ``after.xml`` of the chunks to check for proper operation.

8. Once you are satisfied, move your old logs somewhere else and
   reissue the same command you did earlier but without
   ``--noop``. **This will actually modify the database and can only
   be reversed by restoring from a database backup.**

.. warning:: There is no attempt to make the overall operation atomic
             because it would be quite costly. If an invocation of
             ``./manage.py transform`` without ``--noop`` fails, then
             the database is left in an intermediary state. Recover by
             performing a database restore.

btwdb
=====

This is used to perform miscellaneous administrative operations on the
database. Rather than spread the commands among multiple applications,
they are grouped under this ``core`` command.

* mark_all_bibliographical_items_stale: marks all bibliographical
  items (``bibliography.models.Item``) as stale.

=================
Various Internals
=================

This section discusses some of the internals of BTW and why they are
the way they are.

Some principles:

* Don't spread the object manipulation logic to the database
  code. This also means avoiding the use of triggers, views, etc. Why?
  This obviates the need for maintainers to possess substantial
  database-specific knowledge. If they know Django, they can follow
  the code. Sure, triggers might make some of the Python code nicer,
  but there's the maintenance cost to consider.

Version Control
===============

The ``lexicography`` app performs its own version control: an article
has one ``Entry`` object and a series of ``ChangeRecord`` objects that
represent its history. Why not use something like
``django-reversion``? At the time of writing, the following problems
come to mind:

* ``django-reversion`` stores the revisions as JSON data. So it seems
  these versions are not first-class citizens of the database. BTW
  needs to be able to have the recorded changes be first-class
  citizens so as to be able to search through them (for instance).

* The fact is that BTW has some very specific semantics regarding how
  various versions are created and used, and it is not clear that
  ``django-reversion`` would be able to handle these semantics
  neatly. (Note that it is *possible* ``django-reversion`` could do
  it, but it would take a significant time investment to find out.)

Denormalized Data
=================

At the time of writing (20140927), the ``Entry`` model contains a
``latest`` field that appears redundant. After all, this field is
computable from searching through ``ChangeRecord`` objects, no?

Yes. For any given ``Entry`` object ``latest`` is::

    Entry.objects.get(id=2).changerecord_set.latest('datetime');

(The ``id`` 2 is just for the sake of example.) So we could have::

    @property
    def latest(self):
        return self.changerecord_set.latest('datetime')

However, queries like this
``active_entries.filter(latest__c_hash=chunks)`` are not possible with
a property because ``latest`` is not a field. There are ways to work
around this but they involve having to handle the "non-fieldness" of
``latest`` in each location.

Moreover, getting the list of all the latest change records cannot be
done through Django without multiple queries and in a cross-platform
way. This SQL query gets all the latest change records::

    select cr1 from lexicography_changerecord cr1
      join (select entry_id, max(datetime) as datetime
            from lexicography_changerecord group by entry_id) as cr2
           on cr1.entry_id = cr2.entry_id and cr1.datetime = cr2.datetime;

In Django 1.6, with Postgresql we can do::

    ChangeRecord.objects.order_by('entry', 'datetime').distinct('entry')

This gives us the list of latest change records and so is equivalent
to the previous SQL query. (Order is irrelevant to what we are trying
to achieve here, but is required by our use of ``distinct``.) The
``distinct`` call with a parameter is Postgresql-specific.

The subquery in the SQL query can be generated with::

    ChangeRecord.objects.values('entry').annotate(datetime=Max('datetime'))

However, there does not seem to be a way to join on multiple fields in
Django 1.6. Ultimately, there does not seem to be cross-platform
method to get Django to generate **in one query** something
functionally equivalent to the SQL query shown above.

Some attempts were made to avoid having a ``latest`` field but they
ran into the issues mentioned above or ran smack dab into Django
bugs. (Like `this one
<https://code.djangoproject.com/ticket/20600>`__.)

Why not pyzotero?
=================

There is a library called pyzotero which would give access to the
Zotero v3 API "for free". Why are we not using it? Because it is under
GPL 3.0. BTW would have to be released under this license to be
compatible. We've selected the MPL 2.0 a long time ago and have no
intention to change.

(pyzotero was investigated early in the BTW project but it was at a
very early stage of development then and did not seem to be worth it,
at that time.)

Zotero and Caching
==================

To avoid hitting the Zotero server with frequent requests, and to
allow BTW to perform its work with relative ease, the bibliographical
data is laid out as follows:

* ``Item`` objects in Django's ORM. These are the objects which which
  the rest of BTW interacts. These objects have a MINIMUM_FRESHNESS
  (currently 30 minutes). Objects that are not within this freshness
  specification are refreshed by querying the cache discussed next.

  Note that this table is a cache of sorts. **However, it must be
  saved with the rest of the BTW database when backing up the
  database.** There is no (easy and) reliable way to recreate this
  data if it is ever lost. **This table is not designed to allow for
  modifications of the bibliographical data.**

* A cache named ``bibliography``, which is used by ``zotero.py``. This
  is a cache of responses from the Zotero database. There is no expiry
  on this cache. Whenever a request is made to the cache, it fetches
  the item from the Zotero server only if necessary. **Each request to
  this cache entails a query to the server**, because (at a minimum)
  the cache checks with the server whether the item has changed.

  This cache can be destroyed safely.

..  LocalWords: uwsgi sqlite backend Django init py env config btw
..  LocalWords:  Zotero Zotero's zotero BTW's auth
