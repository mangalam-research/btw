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

This documentation is based on installing BTW on Debian Stretch. Later versions
of Debian or other distributions need these instructions adapted to their
specific case.

This documentation uses a virtual environment to allow for different projects
running different versions of libraries. This is not, strictly speaking,
necessary. If you do not want it, then you have to adapt the instructions so as
to not use virtualenv.

1. Install necessary packages::

    $ apt-get install uwsgi postgresql git python-pip python-dev libffi-dev libxml2-dev libxslt1-dev make unzip libxml2-utils trang jing xsltproc redis-server libpq-dev

   Install the version of ``postgresql-server-dev-...`` that is
   appropriate for the version of postgresql installed on the
   server. This will be needed when ``pip`` installs the Python
   packages.

2. Install ``/etc/apt/sources.list.d/tei.list`` from the config
   tree. Or add the following source to your apt sources::

     # The official server is down for a while. Their home page mentions the de site below:
     # deb https://packages.tei-c.org/deb/binary ./
     deb https://packages.tei-c.de/deb/binary ./


3. Install::

    $ apt-get install tei-xsl tei-p5-source

4. Create ``/etc/apt/sources.list.d/nodesource.list``::

     deb https://deb.nodesource.com/node_12.x stretch main
     deb-src https://deb.nodesource.com/node_12.x stretch main

5. Install::

    $ apt-get install nodejs

6. Install packages from Buster::

     libdom4j-java_2.1.1-2_all.deb
     libsaxonhe-java_9.9.0.2+dfsg-1_all.deb

   You need to grab them manually, and install them with ``dpkg -i`` and then
   run ``apt-get install -f`` to fix the issues.

   This is needed so as to get XSLT 3.0 support in Saxon HE. TEI requires it.

7. Install eXist-db 4.7.0::

   $ mkdir /usr/local/eXist-db
   $ mkdir -p /var/eXist-db/btw/data
   $ chown btw.btw /var/eXist-db/btw
   $ chown btw.btw /var/eXist-db/btw/data
   # You should save the installer somewhere else than the path above.
   $ wget [path to eXist-db installer.jar]
   $ cd !:$
   $ [Log in as the user "btw"]
   $ java -jar eXist-setup-[version]-revXXXXX.jar -console

  Responses:

    * Select target path: ``/usr/local/eXist-db``
    * Data path: ``/var/eXist-db/btw/data``
    * Enter password: [create a new password for admin]
    * Maximum memory in mb: 2048
    * Cache memory in mb: 600

8. Go into ``/usr/local/eXist-db/tools/jetty/etc``.

9. Copy ``jetty-http.xml`` and ``jetty-ssl.xml`` to file with ``.orig`` appended
   to them.

10. Edit both files so that the ``host`` parameter is set to 127.0.0.1,
    and the ``port`` parameter in ``jetty-http.xml`` is set to ``5000``
    and in ``jetty-ssl.xml`` is set to ``5443``.

    THIS RESTRICT CONNECTIONS TO ``jetty`` TO THOSE FROM ``localhost``.

11. Edit ``client.properties`` and ``backup.properties`` so that the uri setting
    uses the ``5000`` port we've set above.

12. You can try connecting to the server on port 80 to see that nginx
    is running. Then stop nginx and::

      $ rm /etc/nginx/sites-enabled/default

13. Create a top directory for the site::

     $ mkdir /srv/www/<site>
     $ chown btw.btw /srv/www/<site>

    The above directory is just a suggestion. If you are doing this for
    Mangalam, then you **must** consult the documentation on how to
    install a server and check the section named "FS Structure" to use
    the proper structure.

14. You need to install Python 3.7.3. Follow the instructions at
    https://superuser.com/questions/1412975/how-to-build-and-install-python-3-7-x-from-source-on-debian-9-8

    Install packages required for the build, including optional ones::

     apt-get install zlib1g-dev libffi-dev libssl-dev libbz2-dev libncursesw5-dev libgdbm-dev liblzma-dev libsqlite3-dev tk-dev uuid-dev libreadline-dev

    [On Debian 10, you also need ``libgdbm-compat-dev``.]

    Use this command for cloning::

     git clone https://github.com/python/cpython.git
     cd cpython
     git checkout v3.7.3

    Use this prefix::

     ./configure --prefix=/usr/local/python3.7.3

15. Create the virtual environment for BTW::

    $ cd /srv/www/<site>
    $ /usr/local/python3.7.3/bin/python3.7 -m venv btw_env

    [Currently, Python 3.7.3 is installed in /usr/local/python3.7.2 due to a
    typo. Since virturalenvs are not movable, etc. we have to live with it.]

The Django Project
==================

Deploying Experimental Code
---------------------------

If you are deploying some sort of experimental version and you do not
want to push to a public server you can do the following:

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

    $ ../btw_env/bin/pip install -r frozen_requirements.txt

2. Install some Node dependencies::

    $ npm install

3. Use the virtual environment::

    $ source ../btw_env/bin/activate

4. Create a BTW environment for BTW. (This is the "environment" which
   determines which Django settings apply to BTW. See `Environment and
   Settings`_.) The database details will be determined after the
   database is created.

Database
--------

.. warning:: The following setup completely ignores schemas and the
             schema search path. The fact is that the btw database is
             designed for one, and one user only. With a single user,
             there's no issue of one user messing up an other user's
             query by adding something to the public schema.

             If more users are added with access to the btw database,
             then a security review of security practices needs to be
             done, with special consideration given to using one of
             the usage patterns at
             `<https://www.postgresql.org/docs/9.6/static/ddl-schemas.html#DDL-SCHEMAS-PATTERNS>`_.

BTW needs to have its own database.

1. Create a user for it::

    $ sudo -u postgres createuser -P btw

   Answer all questions negatively. Create a database::

    $ sudo -u postgres createdb -O btw btw

   Give the new user the right to create databases::

    $ sudo -u postgres psql
    ALTER USER btw CREATEDB;

2. Optionally optimize the
   [connection](https://docs.djangoproject.com/en/2.2/ref/databases/#optimizing-postgresql-s-configuration). As
   of PostgreSQL 9.6 as installed on Debian Stretch, the default values are those
   that Django wants so there is nothing to do here.

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

3. If you do not already have a configuration file with the entry,
   create a ``default`` database entry in the configuration::

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

4. Start BTW's redis instance::

    ./manage.py btwredis start

5. Run::

    ./manage.py migrate

6. Run::

    ./manage.py btwdb set_site_name

   This sets the name of site 1 in the database to match the
   BTW_SITE_NAME setting.

7. Run::

     sudo mkdir -p /var/log/btw/wed_logs
     sudo chown -R btw.btw /var/log/btw

Settings
--------

1. When deploying make sure the following Django settings are set as
   follows::

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

2. Make sure that the ``DEFAULT_FROM_EMAIL`` Django setting is set to
   the value you want to use as the ``From:`` field of emails sent for
   invitations to register to the site. Same with the ``SERVER_EMAIL``
   field. Note that they are probably not going to be the same value.

3. Make sure that the ``ADMINS`` Django setting is set properly.

4. Make sure that the ``BTW_WED_LOGGING_PATH`` and that any custom
   logging is done in ``/var/log/`` rather than in ``/srv``.

5. The file structure is::

    btw_env      The virtualenv environment created earlier.
    btw_repo     Possible repository you use if you are deploying experimental code.
    btw          Where you checked out btw.
    static       Where the static files are collected.
    media        Where media files are stored.

   So you must ensure that ``STATIC_ROOT`` and ``MEDIA_ROOT`` are set
   to point to these directories which are **above** ``TOPDIR``.

6. Make sure the following environment variables are set as follows
   in the uwsgi configuration::

     HTTPS=on
     wsgi.url_scheme=https

Finalizing
----------

This needs to be done last because the ``Makefile`` may use
``manage.py``, which may require a complete configuration.

Run::

  $ make
  $ ./manage.py btwredis start
  $ mkdir -p var/run/btw var/log/btw
  $ ./manage.py btwexistdb start
  $ ./manage.py btwexistdb createuser
  $ ./manage.py btwexistdb createdb
  $ ./manage.py btwexistdb loadindex
  $ ./manage.py btwexistdb load
  $ ./manage.py btwworker start --all
  $ ./manage.py btwcheck
  $ make test-django
  [The Zotero tests will necessarily fail because the server is set
   to connect to the production Zotero database.]
  # We need to stop everything started manually so that systemd
  # takes over.
  $ ./manage.py btwredis stop
  $ ./manage.py btwexistdb stop
  $ sudo cp build/services/* /etc/systemd/system
  $ sudo systemctl daemon-reload
  $ sudo systemctl enable btw
  $ sudo systemctl start btw

If you have not yet done so, create the log directory for the nginx
process responsible for serving BTW::

  $ mkdir /var/log/nginx/btw.mangalamresearch.org/

Demo Site
---------

When creating a new demo site make sure that:

1. It contains a ``env`` file in the top level directory of the Django
   project that sets the ``env`` to a new value appropriate for the
   demo site. (This is what will make the site use a different
   database from the main site.)

2. Create a file named ``NOBACKUP-TAG`` in the top level directory of
   the demo site. (The deepest directory that encompasses all the
   files of this site but excludes any other site.) This prevents
   backing up this site in the fs backups.

Complete Copy
~~~~~~~~~~~~~

1. Dump the database on the "real" site.

2. Drop the old btw_demo database.

3. Create a new btw_demo database.

4. Issue::

    pg_restore -d btw_demo [path to dump]

5. Run the migrations, make sure redis is running and do::

    $ . ../btw_env/bin/activate
    $ ./manage.py migrate

6. Set the site name, make sure redis is running and do::

    $ . ../btw_env/bin/activate
    $ ./manage.py btwdb set_site_name

 This will set the site name in the database to what is recorded in
 the Django settings.

7. Copy the media directory from the regular site to the demo site.

Partial Copy
~~~~~~~~~~~~

Make sure that the site name in the sites table is properly set.

If you are going to move over users then:

1. Go to the regular site and run::

     $ ./manage.py dumpdata --natural --exclude=auth.Permission auth allauth account socialaccount invitation > [dump]

2. Go to the demo site and run::

     $ ./manage.py loaddata [dump]

If you are going to move over articles from the dev site the
bibliographical data must be moved over first. **The bibliography
worker must not have had a chance to populate the Item table yet!!!,
or you'll get double entries.** (If this happens, then you have to
clear bibliography_item and bibliography_primarysource in the
database.)

1. Go to the main site and run::

    $ ./manage.py dumpdata --natural bibliography > [dump]

2. Go to the demo site and run::

    $ ./manage.py loaddata [dump]

You may then load articles:

1. Go to the main site and run::

    $ ./manage.py dumpdata --natural lexicography > [dump]

2. Go to the demo site and run::

    $ ./manage.py loaddata [dump]


Upgrades
--------

Preparing the Source
~~~~~~~~~~~~~~~~~~~~

Before preforming an upgrade, make sure that the source is in shape:

1. You have run the tests from a clean build ``make clean``.

2. ``forzen_requirements.txt`` is up-to-date.

3. You have tagged the current release with ``git tag v... -a`` The
   ``-a`` is important to create an annotated tag.

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

1. **Squeeze in upgrades to the server's infrastructure here...**

2. Make sure all your changes are pushed to the repository.

3. Make sure you have a current backup of the database.

.. warning:: Do not run the following steps before you have read the
             version-specific information about upgrading. Some
             upgrades require that the following steps be partially
             performed or done in a different way, etc.

4. Run::

    $ . ../btw_env/bin/activate

    # The next command **must** be omitted if BTW is meant to continue
    # running. May be omitted if there is no change to how redis is
    # configured.
    $ systemctl stop btw

    $ git fetch origin --tags
    $ git pull origin
    $ git describe
    [Make sure the description shows what you expect.]
    $ pip install -r frozen_requirements.txt
    $ npm install
    $ make
    $ sudo cp build/services/* /etc/systemd/system
    $ sudo systemctl daemon-reload
    # Also check for services in /etc/systemd/system that may
    # be obsolete.

    $ ./manage.py btwredis start
    $ ./manage.py migrate

    # This is the perfect time to clean old records.
    $ ./manage.py btwdb collapse_change_records
    $ ./manage.py btwdb clean_old_versions

    # This is the perfect time to perform a full vacuum on the database.
    # Do this if you've locked the users out of the system already.
    # This command will lock tables while they are being vacuumed. We use
    # ``time`` to record how long it takes. This is useful information because
    # as the database grows, it will take more times. Eventually it could
    # take hours to run a vacuumdb full operation.
    $ time vacuumdb -fzv

    $ ./manage.py btwredis stop
    $ systemctl start btw

    $ ./manage.py btwcheck

    $ make test-django
    [The Zotero tests will necessarily fail because the server is set
     to connect to the production database.]

5. Run btw-smoketest::

     scrapy crawl btw -a btw_dev='<secret>'

6. Take the site out of maintenance mode.

See below for specific upgrade cases.

2.5.3 to 2.6.0
~~~~~~~~~~~~~~

- Modify the env for depolyment to use the new file structure. (e.g. istead of
  ``btw_linode.py`` you have ``linode/btw.py``.

2.4.0 to 2.5.0
~~~~~~~~~~~~~~

- ``apt-get install libpq-dev``

- ``apt-get install tei-xsl``

- Install packages from Buster::

    libdom4j-java_2.1.1-2_all.deb
    libsaxonhe-java_9.9.0.2+dfsg-1_all.deb

  You need to grab them manually, and install them with ``dpkg -i`` and then
  run ``apt-get install -f`` to fix the issues.

  This is needed so as to get XSLT 3.0 support in Saxon HE. TEI requires it.

- This release upgrade BTW to Python 3 so:

 * Remove old Python virtual env.

 * Create new Python 3 virtual env.

 * Activate it.

- Perform the usual upgrade steps up to the point where Python packages are
  installed.

- The release also upgrades eXist-db to 4.6.1

 * Go to the home of the eXist-db installation. Backup the eXist-db database
   with::

     java -jar start.jar org.exist.backup.ExportMain -x -z

   This will create a file in ``exports/`` called ``full<date>.zip``

 * Move the old stuff out of the way::

     $ mv /usr/local/eXist-db /usr/local/eXist-db-[version]
     $ mv /var/eXist-db/btw/data /var/eXist-db/btw/data-[version]

 * Install the new eXist-db installation. See the original installation
   instructions for answers to the questions it asks.

 * Go into ``/var/eXist-db/btw/data`` and ``rm *.dbx *.log *.lck``

 * Cd to the home of the new eXist-db installation.

 * The above deleted the whole database, so set the admin password again::

     $ ./bin/client.sh -s
     [Use the command: passwd admin]

 * Restore::

     $ ./bin/backup.sh -u admin -p PASSWORD -r [path to zipped backup]

 * Upgrade the Dashboard::

     $ ./bin/client.sh -s -u admin -P PASSWORD

   Use the command::

     find repo:install-and-deploy("http://exist-db.org/apps/shared", "http://demo.exist-db.org/exist/apps/public-repo/modules/find.xql")
     find repo:install-and-deploy("http://exist-db.org/apps/dashboard", "http://demo.exist-db.org/exist/apps/public-repo/modules/find.xql")

 * Run::

     $ manage.py btwexistdb loadutil

- Continue the common installation steps.

- The encoding of cache keys for the bibliography app has changed. So that cache
  needs to be zapped and rebuilt.

- The cmsplugin_filer stuff is deprecated and no longer maintained. It will bomb
  when Python 3.8 becomes current. I've tried migrating the data to the new
  suggested plugins but it did not work. So the solution for now is to remove
  these plugins and fix the CMS pages manually. (A quick inspection suggests
  that there's probably less fixing needed than I thought. I used the filer
  facilities extensively when I first setup the CMS but the assistants who took
  over all tossed that aside. I think there's only one remaining reference to
  the filer stuff.)

- Drop these tables:

 cmsplugin_filer_file_filerfile
 cmsplugin_filer_folder_filerfolder
 cmsplugin_filer_image_filerimage
 cmsplugin_filer_link_filerlinkplugin
 cmsplugin_filer_teaser_filerteaser
 cmsplugin_filer_video_filervideo
 cmsplugin_iframe_iframeplugin

- Run:

  ./manage.py cms delete-orphaned-plugins

- Run ``./manage.py cms fix-tree``

- Fix the CMS pages:

  - (Probably won't need fixing:) Front page: logo of Mangalam, NEH, HTE at
    bottom of page. Put back the images, and link to the respective
    organizations. Set correct alt text. (Note that the NEH and HTE logos are
    already broken.)

  - (Probably won't need fixing:) Front page: left video
    https://youtu.be/N2ZeTtIJVR0

  - Browserstack on the "Technologies" page.


2.0.0 to 2.1.0
~~~~~~~~~~~~~~

- Before restarting any parts of BTW, make sure all celery settings in
  the settings files used by the deployment have been updated to have
  the ``CELERY`` prefix.

1.4.1 to 2.0.0
~~~~~~~~~~~~~~

Before all:

- Install eXist.

After pulling the new code:

- Add the ``settings`` for eXist.

After ``pip install -r requirements.txt``:

- Force django-polymorphic to be at 1.0.2.

- Force django to be at 1.10.x.

- Run ``pip uninstall django-treebeard`` and then ``pip install git+https://github.com/tabo/django-treebeard#79bdb7c``.

After starting redis:

- Run ``./manage.py cms fix-tree``

- Clear the "article_display" and "page" caches.

After ``./manage.py migrate``:

- Run ``btwexistdb`` commands: ``createuser``, ``createdb``,
``loadindex``, ``load``.

After the install:

- Remove the "Login required" flag for the semantic fields page.

- Add the ``can_add_semantic_fields`` and
  ``can_change_semantic_fields`` to all users that need it.

1.4.0 to 1.4.1
~~~~~~~~~~~~~~

- At a minimum, execute::

    rm `find . -name menu.pyc`
    rm `find . -name cms_app.pyc`

  To be on the safe site, I actually recommend doing::

    rm `find . -name "*.pyc"`

  When running tests in buildbot some cases failed due to very old
  leftover ``.pyc`` files.

- After having done the database migrations, run ``manage.py cms
  fix-tree`` as recommended by Django CMS to fix possible issues with
  the tree of pages.

1.3.x to 1.4.0
~~~~~~~~~~~~~~

- You must load the HTE data somehow. It could be using the ``hte``
  command or by dumping some the ``semantic_field...`` tables in the
  development database and loading them in production. Remember to set
  the sequences used to set ids properly if you use a SQL
  dump/restore.

- It is necessary to flush the article display cache::

    $ ./manage.py clearcache article_display

- You must give the ``category.add_category`` right to whoever will be
  allowed to add categories.

- You will have to create a "Semantic Fields" page which will have for
  apphook semantic_fields. This pages should also have its permissions
  set so that "Login required" checked and "Menu visibility" is "for
  logged in users only".


1.2.x to 1.3.0
~~~~~~~~~~~~~~

You must add ``BTW_EDITORS`` to Django's settings.

The ``CitePlugin`` must be added to some page to allow site-wide
citations.

During migration Django will ask whether the content types for the
models userauthority, otherauthority and authority should be
removed. Answer yes.


1.1.x to 1.2.0
~~~~~~~~~~~~~~

1. Upgrade the nginx configuration to the new one so that developers
   can bypass maintenance mode.

2. **After stopping redis but before updating the source,** upgrade
   ``South`` to the latest in the 1.x series.

3. **After stopping redis but before updating the source,** upgrade
   ``django-allauth`` to the version required by BTW **1.2.0**.

4. **After stopping redis but before updating the source,** run
   ``./manage.py migrate socialaccount``. This will upgrade the tables
   for the ``socialaccount`` app (provied by ``django-allauth``) to the
   latest format.

5. Resume the installation with the source update, and so on...

Afterwards:

1. Create the pages managed by the CMS:

 a. On the development machine issue::

    ./manage.py dumpdata --indent=2 --natural-foreign cms cmsplugin_filer_file cmsplugin_filer_folder cmsplugin_filer_link cmsplugin_filer_link cmsplugin_filer_image cmsplugin_filer_teaser cmsplugin_filer_video  easy_thumbnails filer djangocms_text_ckeditor cmsplugin_iframe > dump.json

 b. Remove the record that has to do with cms.pageusergroup.

 c. On the deployment machine issue::

    ./manage loaddata dump.json

 d. Copy the ``media`` subdirectory from the dev machine to the
    deployment machine. **Make sure to move it into the right location**.

2. Duplicate the permission setup from the dev machine to the
   deployment machine. In particular:

 a. Add the permissions to the CMS plugins to the "CMS scribe" group.

3. Create an account for Bennett with the "scribe" and "CMS scribe"
   roles, and the right to manage bibliography.

1.0.x to 1.1.0
~~~~~~~~~~~~~~

1. Update the site configuration to add BTW_LOGGING_PATH,
   BTW_RUN_PATH, BTW_LOGGING_PATH_FOR_BTW, BTW_RUN_PATH_FOR_BTW. Make
   BTW_WED_LOGGING_PATH use BTW_LOGGING_PATH_FOR_BTW.

2. Perform the commands to create the log and run directories for
   BTW. For intance, it could be::

    mkdir -p var/log/btw
    mkdir -p var/run/btw

3. Convert the local configuration file to connect to redis through
   the local socket started by ``btwredis``.

4. Use ``lib.settings.join_prefix`` in the settings file and
   ``slugify.slugify``.

5. Modify your uwsgi init file so that it has::

     uid = btw
     buffer-size=32768

0.8.x to 1.0.0
~~~~~~~~~~~~~~

1. Update the site configuration to configure the caches named
   `session`, `page` and `article_display`.

2. Force an update of the documentation so that ``tei.css`` and
   ``tei-print.css`` are loaded from a local copy. You must::

      rm -rf utils/schemas/out/btw-storage-0.10/btw-storage-doc/

   A subsequent ``make`` should redo everything but check that the
   final files have the right contents.

0.7.x to 0.8.0
~~~~~~~~~~~~~~

1. Issue the management command::

     $ ./manage.py btwdb mark_all_bibliographical_items_stale

2. Convert your settings to use the ``s`` object. See `Setting the
   Settings`_.

3. Install django-redis in the virtualenv for btw.

4. Move to Redis for the session cache (the default cache normally set
   in the ``btw_<env>.py`` file and the Zotero cache (the cache named
   ``"bibliography"``, which is normally set in the
   ``bibliography_<env>.py`` settings file).

0.0.2 to 0.1.0
~~~~~~~~~~~~~~

1. Delete the database table ``biblliography_item``. This is okay
   because the BTW software has not yet been used in production.

2. Perform the general steps.

Notes from Actual Upgrades
~~~~~~~~~~~~~~~~~~~~~~~~~~

- 2.0.0 to 2.1.0: Upgrade scheduled for 2017/09/26 at 7:30-9:30
  EDT. The upgrade also included a Linode migration and updating the
  OS, both of which took about 12 minutes. The migration queue was
  empty and the migration itself took about 5 minutes. The BTW upgrade
  ran into an unexpected issue. We were getting an EINTR during a
  Kombu communication with a socket. Added some custom code to retry
  the communication. Seems to have fixed the issue.

- 1.4.0 to 1.4.1: Upgrade scheduled for 2016/04/30 at 8:00-9:00 EDT. I
  started a little before to prepare. The upgrade was done at about
  8:30 EDT.

- 1.3.1 to 1.4.0: The upgrade window was scheduled for 2016/04/06 at
  8:00-12:00 EDT. I actually got busy with something else and did not
  begin until 8:10. The upgrade was finished by about 10:28.

- 1.2.x to 1.3.0: The upgrade window was scheduled for 2015/08/19 at
  11:00-12:00 EDT. I began preparing at around 10:40 EDT so as to get
  a head start with the steps that could be performed before the
  upgrade. The issue with Tilaa crippling the performance of the swap
  probably added a good 15-20 minutes to the whole proceedings.

- 1.1.0 to 1.2.0: The upgrade window was scheduled for 2015/06/08 at
  8:00-10:00 EDT. I began preparing at around 7:30 EDT so as to get a
  head start with the steps that could be performed before the
  upgrade. At 8:05 EDT I put the server into maintenance mode. At
  about 9:05 EDT I took the server out of maintenance mode. I got a
  couple of task errors while running the Django tests. Probably due
  to how the logging is different on the server than on the dev
  system.

- 1.0.5 to 1.1.0: The upgrade window was scheduled for 2015/04/29 at
  8:00-10:00 EDT. I began preparing at around 7:30 EDT so as to get a
  head start with the steps that could be performed before the
  upgrade, and server maintenance not directly tied to the upgrade
  (e.g. shutting down the demo site). At 8:00 EDT I put the server
  into maintenance mode. At around 8:35 I put the server out of
  maintenance mode. The server initially failed to work because I
  forgot to make a couple changes to the btw.ini file (uwsgi
  configuration). Moreover I had to change ownership of the log files
  in /var/log/btw so that BTW could write there. Then it was smooth
  sailing.

- 0.7.1 to 0.8.0: The upgrade window was scheduled for 2015/01/21 at
  8:00-9:00 EST. I began preparing at around 7:30 EST because a few of
  the upgrade steps (installing new packages, updating the settings of
  the Django project) could be performed before putting the server
  down. At 8:00 EST, I put the server in maintenance mode. A little
  before 8:30EST, the server was out of maintenance mode. I tested the
  server with ``./manage.py test``, by going to ``Bibliography /
  Manage`` and by viewing some articles. The later test failed. It was
  due to ``build/static-build/config/requirejs-config-dev.js`` which
  was out of date. The contents of this file changed when Makefile is
  edited, which is not currently picked up by the way the make file is
  organized. Deleting the file and recreating it solved the issue.

- 0.8.0 to 1.0.1: The upgrade window was scheduled for 2015/02/01 at
  9:00-10:00 EST. I spent about 45 minutes before the upgrade window
  to perform changes to the server. This upgrade required a new monit
  configuration to send alarms. I had to modify monit for this, which
  entailed reading documentation. After performing the upgrade, I got
  some 500 status responses. This was due to the ``.log`` and ``.pid``
  files created by the worker. They caused the tree to be unclean and
  BTW dutifully raised an exception. While testing the site, there was
  an issue with viewing articles. It seemed that the communication
  between browser and system did not work. Clearing the caches and
  restarting the worker seems to have cleared it up. The site was back
  up and running at 10:15 EST.

Nginx
-----

The server key generation has been superseded by using Let's Encrypt
Certificate. Read certbot's documentation for how to get and install
certificates.

If needed for some reason, the manual menthod to create some new
server keys::

    $ cd /srv/www/<site>
    $ openssl genrsa -out ssl.key 2048
    $ openssl req -new -key ssl.key -out ssl.csr
    [Answer the questions to identify the machine. Leave the password blank.]
    $ openssl x509 -req -days 365 -in ssl.csr -signkey ssl.key -out ssl.crt

If there isn't a secure dhparam yet, you should create it with::

    $ openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048

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

In August 2015 we conducted some tests with a RAM-based PostgreSQL
cluster to see whether it would improve testing time. We found roughly
a 7% improvement on test times when running the Django tests but the
hoops we have to go through to setup the cluster and the problems this
could cause in the long run (more complex database setups would
require redesigning the code that creates and manages the cluster) are
not worth this small improvement. The time improvement is expected to
be even smaller when running the Selenium-based tests that need
running on Sauce Labs, as the bulk of the waiting time there is due to
communications between the test suite and the browser.

Django Tests
============

Running the Tests
-----------------

You should be using ``make`` to run the tests rather than ``./manage.py test``
because some of the tests are dependent on files that are generated with
``make``, and some of the tests need to be run in isolation::

    $ make test

Test Isolation
--------------

As of the time of writing, the Django tests need to be run in 3 isolated groups:

* The menu tests in ``./core/tests/test_menus.py``. Django CMS caches a fair
  amount of information. This includes menu information. Unfortunately, this
  causes (some of) the tests in ``test_menus.py`` to fail if they are run with
  the rest of the BTW test suite. Therefore, these tests must be run in a
  *separate* test run.

* The btwredis tests in ``./btw_management/tests/test_btwredis.py``. In order to
  test ``btwredis``, the test suite needs to stop the default redis instance
  started by the test runner, and restart it afterwards. The problem though is
  that this stop/start resets the connections that were open prior to running
  the ``btwredis`` tests and causes a failure in the rest of the suite. So these
  tests must be isolated.

* The other tests not covered in the two groups above.

An earlier version of BTW used the attrib plugin of nosetests to segregate the
tests (``@attr(isolation="menu")`` in a test file, and ``--attr='!isolation'``
in the build file, etc.). However, the attrib plugin does not skip a *whole
module* when all the tests in it are to be skipped, and this is a problem for
the ``btwredis`` tests because we need to skip the *module* setup and tear down
code *too*. So instead we use ``--ignore-files`` to skip the necessary files and
specify them by name where needed. See the targets ``test-django*`` in
``build.mk`` for the gory details.

Zotero Tests
------------

The ``bibliography`` application communicates with the Zotero server
at ``api.zotero.org``. To avoid being dependent a) on a network
connection, b) on that server being up, c) on the account that was used to
create the tests being available, the test suite uses ``mitmdump``
(from the mitmproxy package) to record and replay interactions with
the server. The infrastructure needed for this is in
``bibliography.tests.util``.

The only tests that should ever perform any kind of communication with
the server (either for real, or faked by ``mitmproxy``) are those in
the ``bibliography`` app. All other tests should be mocking the
``zotero`` module so as to return results immediately (no cache check,
no talking to the server). The module
``bibliography.tests.mock_zotero`` is used for this task.

Mitmproxy uses a self-signed certificate to serve data. Forwarding the
upstream certificate currently does not work. (See
`<https://github.com/mitmproxy/netlib/issues/32>`__ .) Moreover, we'd
rather have the suite be totally independent from a live Zotero server
so that we can run the suite even if the Zotero server happens to be
down or unreachable. In order to avoid certificate errors, the test
suite has to:

1. Run ``c_rehash`` on the ``~/.mitmproxy`` directory. Some of the
   files there are not proper certificates so there will be non-fatal
   errors.

2. Set the environment variable SSL_CERT_DIR to search
``~/.mitmproxy`` in addition to the OS directory.

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

Nginx
-----

Internally, the test suite starts nginx by issuing::

    $ utils/start_server <fifo>

The fifo is a communication channel created by the test suite to
control the server.  The command above will launch an nginx server
listening on localhost:8080. It will handle all the requests to static
resources itself but will forward all other requests to an instance of
the Django live server (which is started by the ``start_server`` script
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

The Django Server
-----------------

The Django server started by ``start_server`` is based on
``LiveServerTestCase`` and consequently organises its run time
environment in the same way.

Originally, we had the test suite send a signal to the server so that
with each test, the server would reset itself. The "reset" operation
meant that the ``LiveServerTestCase`` instance ended, which caused the
creation of a new instance. This entailed letting Django's test
framework perform the cleanup and setup operations on the
database. This way, a test would not see the database changes
performed by another test. The cleanup performed by Django's test
framework was extremely slow, however. So we modified the suite so
that some tests would be deemed "dirty" and would require a
reset. This helped speed up the suite quite a bit.

However, we eventually ran into more problems. Once we started using
``transaction.on_commit``, we found that Celery tasks launched at
commit time would not be able to find the ``Chunk`` objects they were
supposed to work on, because they had been deleted by the test
cleanup!! This is something which **by design** cannot happen in
production because ``Chunk`` objects are never deleted. (They may be
hidden, but not deleted.) All solutions which involved allowing the
suite to perform Django's generic cleanup were problematic:

* The Celery tasks could have failed silently. However, since in
  production a failure would be indicative of a fatal structural
  problem, we do not want to mask such problems but instead have them
  cause an alarm. (The project sends an email to the administrators.)
  Moreover, even in testing, ignoring the failure could mean ignoring
  a real problem (like a race condition).

* The Celery tasks could have run eagerly. This would actually mask
  problems that occur due to race conditions.

* The suite could have been modified to try to allow the Celery tasks
  to complete before deleting the data. This would have made the suite
  slower across the board and would have complicated the logic of the
  tests or the tasks quite a bit. And this would be only to take care
  of a problem that occurs in testing.

The solution we settled on is to turn off Django's generic cleanup by
running all the Behave tests inside of a single ``LiveServerTestCase``
instance. The "reset" message is no longer used but instead a
"newtest" message is sent from the Behave runner to the live
server. This causes the live server to run ad-hoc cleanup code. In
this way ``Chunk`` objects are never deleted, which mirrors exactly
what happens in production. The cleanup code currently performs a few
changes, like deleting some bibliographical records, some custom
semantic fields and reverting articles to the version they were when
the suite started. Beyond this, tests should try to depend as little
as possible on a specific state. They should as much as possible
figure what state existed when they started and then check how the
state was changed. (e.g. If I test the creation of a new X object in
the database, cound the number of X objects before the test, and check
that there are X + 1 objects after the operation that creates a new
object.)

A nice bonus is that this also makes the suite faster since it does
not perform the database churn that Django's generic database cleanup
and setup does.

Running the Suite
-----------------

To run the suite issue::

    $ make selenium-test BEHAVE_PARAMS="-D browser='OS,BROWSER,VERSION'"

where ``OS,BROWSER,VERSION`` is a combination of
``OS,BROWSER,VERSION`` present in ``config/browser.txt``.

Behind the scenes, this will launch behave. See `<Makefile>`_ to see
how behave is run.

Note that the Selenium-based tests currently need a special test runner to run
properly. They need to be run through `<selenium_test/btw-behave.py>`_

How to Modify Fixtures
----------------------

There is no direct way to modify the fixtures used by the Django tests
(this includes the live server tests which is used to run the Selenium
tests). The procedure to follow is:

1. Stop the development server.

2. Move your development database to a different location
   temporariy. **Or** modify the development environment so that the
   development server connects to a temporary, different database.

3. Issue::

    $ ./manage.py migrate

4. Then start your server again. You should start it with
   ``BTW_DIRECT_APP_MODE`` set to ``True``. Or you won't be able to
   access the lexicography and bibliography apps.

5. Repeat the following command for all fixtures you want to load or
   pass all fixtures together on the same command line::

    $ ./manage.py loaddata [fixture]

6. At this point you can edit your database.

7. Run a garbage collection to remove old chunks that are no longer
   referred.

8. When you are done kill the server, and dump the data as needed::

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

Setting the Settings
====================

The Django method of setting the various settings is to set a global
in ``settings.py``, which is then used by Django's machinery. However,
this method is very inflexible in an environment where settings can be
set from multiple different files. Instead of using this method as-is,
BTW sets its settings on a singleton named ``s`` that is created by
``lib.settings`` **every file that wants to modify settings must
import this singleton and modify the settings by setting attributes of
the appropriate names on this object**. Doing this allows more
flexibility in the order in which settings are set and how they may
depend on one another. For instance ``test_settings.py`` sets
``s.BTW_TESTING`` *first* and then loads ``settings.py``. This allows
other settings to be set differently depending on whether or not
``s.BTW_TESTING`` is true.

It would be possible have the desired behavior by using ``exec ... in
globals()`` but this method of doing things has downsides, like for
instance having the linter complain about unknown variables because
globals used in a file come from another file. It also prevents
keeping variables truly private. For instance ``test_settings``
currently has a ``__SILENT`` variable which would not be private if
``exec ... in globals()`` were used. The variable would be visible to
the executed file. It would be possible to write code to compensate
but each new private variable would require an exception.

Where Settings are Found
========================

Structure of the settings tree in BTW:

* ``settings/settings.py``  BTW-wide settings

* ``settings/_env.py``      environment management

* ``settings/<app>.py``     settings specific to the application named <app>

The ``settings.py`` file inspects INSTALLED_APPS searching for local
applications and passes to ``exec`` all the corresponding ``<app>.py``
files it finds.

To allow for changing configurations easily BTW gets an environment
name from the following sources:

* the ``BTW_ENV`` environment variable

* An ``env`` file at the top of the Django project hierarchy.

* ``~/.config/btw/env``

* ``/etc/btw/env``

This environment value is then used by ``_env.find_config(name)`` to find
configuration files:

* ``~/.config/btw/<env>/settings/<name>.py``

* ``/etc/btw/<env>/settings/<name>.py``

The **first** file found among the ones in the previous list is the
one used. By convention ``_env.find_config`` should be used by the files
under the settings directory to find overrides to their default
values. The ``<name>`` parameter should be "btw" for global settings or
the name of an application for application-specific settings. Again by
convention the caller to find_config should exec the value returned by
``find_config`` **after** having done its local processing.

The order of execution of the various files is::

    settings/__init__.py
    <conf>/<env>/settings/btw.py
    settings/<app1>.py
    <conf>/<env>/settings/<app1>.py
    settings/<app2>.py
    <conf>/<env>/settings/<app2>.py

where ``<env>`` is the value of the environment set as described
earlier, and ``<conf>`` is whatever path happens to contain the
configuration file.

Secrets
=======

It is advantageous for interoperability to have some settings use a simplified
syntax which allows them to be used outside Python. These settings are deemed to
be "secrets" (because most of them are in fact sensitive information). BTW
searches for secrets here:

* ``~/.config/btw/<env>/secrets/btw``

* ``/etc/btw/<env>/secrets/btw``

This file is sourced by the shell **SOMETIMES AS ROOT** as part of the Docker
build process or startup scripts. It is also sourced by the Python code of
Django. In either case the shell does the processing of the file so it accepts
shell syntax (quoting, etc.)

The secrets subdirectories are allowed to contain other secrets files for tools
related to BTW.

=======
 Roles
=======

An earlier version of BTW used the terms "author" for people who have
the capability to edit articles. This proved confusing in discussion
because people who can edit articles are not necessarily the authors
of the articles. They can be proofreaders, assistants, etc.

* "informational pages": Those pages that exist primarily to provide
  information *about* the BTW project but that are not application
  pages.  Examples: the home page of the site, a page about who is
  involved in the project, a page that describes methodology,
  documentation about the site, etc.

* "application pages": Those pages that primarily serve to provide a user
  interface to the applications that are part of BTW. All of the
  lexicographical and bibliographical pages are application pages. This
  includes the pages that show the lexicographical articles.

+---------------------+-------------------+--------------------------+
|BTW Role             |Django role(s)     |Notes                     |
+---------------------+-------------------+--------------------------+
|visitor              |-                  |People who visit the site |
|                     |                   |but do not have an        |
|                     |                   |account.                  |
+---------------------+-------------------+--------------------------+
|user                 |-                  |Users are able to log in  |
|                     |                   |but cannot edit           |
|                     |                   |anything. (As of 2015/5,  |
|                     |                   |this is a theoretical     |
|                     |                   |role. Not yet in use.)    |
+---------------------+-------------------+--------------------------+
|lexicographical      |scribe             |                          |
|article author       |                   |                          |
+---------------------+-------------------+--------------------------+
|assistant,           |scribe             |                          |
|proofreader, etc...  |                   |                          |
|                     |                   |                          |
+---------------------+-------------------+--------------------------+
|maintainer           |CMS scribe         |                          |
|for the              |                   |                          |
|informational        |                   |                          |
|pages                |                   |                          |
+---------------------+-------------------+--------------------------+
|superuser            |-                  |Django superuser flag on. |
+---------------------+-------------------+--------------------------+

A "Django role" corresponds to a Django group. The groups are defined
as follows:

* scribe: able to edit lexicographical articles.

* CMS scribe: able to edit the informational pages.

* editor: all privileges of scribes, but reserved for future use. (We
  may eventually limit publishing privileges to only people in the
  "editor" group.)

There is no group able to edit application pages as these must be
edited by developers.

========
BTW Mode
========

Visible Absence
===============

A "visible absence" is an absence of an element which is represented
as a *presence* in the edited document. If ``<foo>`` might contain
``<bar>`` but ``<bar>`` is absent, the usual means to represent this
would be a ``<foo>`` that does not contain a ``<bar>``. With a visible
absence, ``<foo>`` would contain a GUI element showing that ``<bar>``
is absent.

A "visible absence instantiator" is a visible absence which is also a
control able to instantiate the absent element.

IDs
===

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

* Django-CMS initially used django-reversion to maintain histories of page
  changes but in 3.4.0 they dropped support for it. It is not clear what the
  issues where but it does not look good.

Version Control in Caches
=========================

Django presents a system by which keys have a version number
associated with them. But BTW does not use it. Why?

The version system that Django provides does not lend itself to the
usage pattern of BTW. BTW typically wants to get **whatever version of
the data is available**. What Django provides does not do this simply
because there is no method for "give me a key with any version". You
have to first search for the key with the current version. If not
found, then search for older keys. This means multiple accesses to the
cache. BTW instead puts the version information in the data stored
with a key and gets whatever it is going to get in one operation and
then acts depending on the version found.

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

Celery Tasks and Django CMS
===========================

In a basic Django application the url patterns used for determining
which view will serve a request are static: they are set in ``.py``
files do not change until the application is upgraded, which is an
administrative act.

With Django CMS, the above principle no longer holds true. It is
possible to have a page load an app (using "apphooks"). Since CMS
pages can be created at run time, this means that the url patterns can
change at any time while the site is running. This is not a problem
for those processes which are launched by the WSGI app server. By the
use of the appropriate middleware, these processes periodically check
for changes and do what is necessary.

However, Celery tasks do not have the machinery necessary to detect
these changes. Right now, BTW dodges the issue by having the Celery
tasks be dependent only on "REST urls". These are stored in
``rest_url.py`` files and operate in the same way as the "basic Django
application" scenario described above: they don't change at run
time. Changes caused by the CMS do not affect how the tasks run.

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

Preparing and Caching ``Chunk`` Objects
=======================================

Chunks are cached in Redis and in eXist.

Cached Data of the "xml" Kind
-----------------------------

Before they are displayed, ``Chunk`` objects need to have their XML
"prepared" to sort and combine semantic fields and to provide human
readable names for those fields. This process needs the following
inputs:

* The XML data of the ``Chunk``, which is immutable.

* The names of the semantic fields, which are mutable.

The prepared XML is deemed to be display information of the kind "xml".

This data is created when a ``Chunk`` is saved: a task is launched to
create and save it. It is refreshed when any of the semantic field
names on which a ``Chunk`` depends are changed.

This is cached in Redis but expires there after 30 minutes. It is also
stored in eXist for searches. eXist is a cache *of sorts* in that
putting the chunk data in it allows us to perform XML-based searches
(with XQuery) and perform full-text searches.

If the data has expired from the cache but is still in eXist, it is
refreshed from eXist.

Cached Data of the "bibl" Kind
------------------------------

Moreover, this prepared XML needs the following adjuncts before it can
be displayed to the user:

* The links to other articles need to be created (this is currently
  done just before the XML is sent to the client).

* The names and URLs of the works referenced need to be provided. This
  information is passed to the client, which folds it into the
  structure shown to the user. This is deemed to be display
  information of the kind "bibl".

This "bibl" data is created "on demand" when it is needed to display
an article. It exists only in the cache and never expires. It is
recomputed when any of the bibliographical entries on which an article
depends are changed.

Performance Notes
-----------------

On 2016/07/06 loading the data dumped from BTW with ``btwexistdb
load`` takes about 6 minutes. The size of the chunk data is about
50mb. That's 1030 chunks.

On 2019/07/23 running ``load_backup.sh`` takes 21 minutes. (NOTE THIS IS NOT THE
SAME TEST AS ABOVE: ``load_backup.sh`` also starts postgresql, drops the old
database, etc.) There are 1139 chunks and 27mb of chunk data. (The 27mb of chunk
date is what Postgres reports about the lexicography_chunk table. It is unclear
why it is smaller than what reported on 2016/07/06 though we have more chunks. A
database can fragment over time. The documentation for VACUUM mentions that
space can be returned to the OS only if the freed space is at the end of the
database. So if the database is created from a backup, it will be smaller than a
database that has been long running because it is "defragmented" when restored.)

* I managed to reduce the time to about 11 minutes after performing
  optimizations to the code which prepares articles in ``article.py``

* I've further reduced the time to about 6 minutes by excluding the chunks which
  are hidden (i.e. which do not have a ChangeRecord which is not hidden pointing
  to them).

* I've further reduced the time to a little over 1 minute by only calling
  ``prepare`` on the chunks that are published. BTW scribes can access
  unpublished chunks for viewing but these will just be prepared "on demand".

Cleaning
========

BTW cleans old ``ChangeRecord`` objects from the database.

This cleaning process hides old intermediary versions of the articles
we have. BTW is very agressive in how frequently it saves data. This
is useful both to prevent data loss and to help in diagnosing eventual
problems. However, this means that BTW stores a lot of versions of an
article. So over time the data usage grows and this becomes
problematic in two major ways:

1. People who have access to the entire history of an article see a
   lot of versions that are not particularly useful.

2. Searches go through data that is not interesting. This makes
   full-text searches in particular slower than they should.

The cleanup algorithms go through the database and mark old records as
"hidden", which excludes them from the interface presented to users
and from searches. The administrative interface always shows all
records, hidden or not.

So two types of cleanup have been implemented:

* Collapsing versions: the principle here is that if there are
  multiple ``ChangeRecord`` objects pointing to the same ``Chunk``,
  the records are "collapsed", which mean that among all objects
  pointing to the same ``Chunk``, we keep one visible and hide the
  rest. This reduces the list of versions shown but does not make any
  ``Chunk`` invisible. This collapsing operation operates only on
  records that are older than 30 days.

* Cleaning old versions: this algorithm hides old records that were
  created for purposes of recovery (which happens when the editor has
  a fatal failure), or that were auto-saves. This operation can make
  some ``Chunk`` objects invisible. This operation is done only on records
  that are older than 90 days.

Important points:

* The algorithms are designed to never ever make a article completely
  invisible.

* Published versions are not hidden, ever.

* The latest ``Chunk`` of an article is never hidden. At most, *may* become
  accessible only through an earlier version that points to the ``Chunk``.

When cleaning was run in September 2016 on a copy of the deployed
database, it reduced the number of visible versions by more than 50%!


Bibliographical Formats
=======================

At the same time we've added the "how to cite" functionality, we've
considered adding the framework necessary for the autodiscovery of
bibliographical formats. For instance, a user visiting our page and
who'd like to include into their Zotero database the bibliographical
information for an article could just click a button to have the
information be transfered to their database.

Unfortunately, the realm of bibliographical data interchange standards
is a mess. Dublin Core does not have a notion of "encylopedia
article". Neither does COinS. MODS is a format that fully support what
we need but it is discoverable only by using unAPI, which is a clunky
standard and also requires making HTML5 pages invalid.

In light of the problems above, we will settle for now on providing an
option to download MODS manually.

Citation Formats
================

Unfortunately, various sources quote the style guides
inconsistently. To generate the citations that BTW produces we
examined how the HTE does it and we consulted the following sources:

The guide used for the MLA citation formati is this one:

https://www.library.cornell.edu/research/citation/mla

We have elected, like the OED and the HTE do, to not include the
editor names in the citation generated according to the MLA. This
simplifies the code quite a bit.

For the Chicago style:

http://library.osu.edu/documents/english/FINALlibrary_CMS.pdf

Test Suite Optimization Notes
=============================

In May 2016, we've moved to disable migrations during testing. The
problem with migrations is that all migrations ever created must be
performed. It is slow as hell. (Squashing is not quite the answer it
seems. We don't control the squashing behavior of third-party
apps. Also, in the past we've been able to modify migration code after
the fact. Squashing complicates this.) By moving the liveserver to
disable migrations during testing, and move away from fixtures to some
extent, we have reduced the run time of a full selenium test with
Chrome 50 from 30 minutes to 25 minutes. That's about 16%
improvement. The 5 minutes saved is going to be repeated over and over
during the life of the project.

CMS Choice for BTW
==================

The Short List
--------------

Django CMS: One rather major issue with Django CMS is that people who
can edit pages must be able to access the ``admin`` interface.

feinCMS: This tool also needs to give CMS editors access to the
``admin`` interface.

Candidates
----------

As of 2015-04-23, after removing projects that are dead or in an alpha
state or not updated in years from the table at:

https://www.djangopackages.com/grids/g/cms/

we get these candidates:

* Django CMS
* Wagtail
* Mezzanine
* feinCMS
* django-fiber
* Opps
* Django page CMS

Rejected
--------

Mezzanine: As of 2015-04-23 does not support Django 1.7 or later.

Wagtail: appears to completely take over the admin interface. No
support for revisions.

django-fiber: eliminated because it needs djangorestframework to be
less than 3 but BTW already uses the 3 series.

Opps: documentation seemed rather rudimentary, it is also not clear
how it performs with Django > 1.5.

Django page CMS: compatible with Django 1.5, 1.6 but not 1.7 or 1.8.

Full Text Databases
===================

XML databases can be used but the quality of these databases is not great.

Elasticsearch
-------------

The problem with Elasticsearch is that it does not know anything about
the structure of documents. Putting and querying some simple XML
documents in Elasticsearch is probably doable without too much
trouble. But when it comes to multilingual search, there's a
problem. If I want to match "circus" only in a Latin citation, the
search has to konw which parts of the text are in Latin. With an
XML-aware database We'd do this by querying @xml:lang. With
Elasticsearch, we'd have to setup some sort of tokenizer that extracts
only the Latin text.

1. Install it through their deb repository.

2. Install the shield plugin: https://www.elastic.co/downloads/shield

  ::

      sudo /usr/share/elasticsearch/bin/plugin install license
      sudo /usr/share/elasticsearch/bin/plugin install shield
      sudo service elasticsearch restart

3. Create users::

      sudo /usr/share/elasticsearch/bin/shield/esusers useradd es_admin -r admin
      # This is for the kibana tool
      sudo /usr/share/elasticsearch/bin/shield/esusers useradd kibana4_server -r kibana4_server

4. Edit the kibana config so that it uses the user::

      sudo vi /opt/kibana/config/kibana.yml

  Edit it to read:

  > elasticsearch.username: "kibana4_server"
  > elasticsearch.password: "password"

  While you are at it::

     sudo chmod og-r /opt/kibana/config/kibana.yml
     sudo chown kibana /opt/kibana/config/kibana.yml

4. Add a ``kibana_user`` role::

kibana_user:
  cluster:
      - monitor
  indices:
    - names: '.kibana*'
      privileges:
        - manage
        - read
        - index

5. Add a "btw_admin" role::

btw_admin:
  indices:
    - names: 'btw-*'
      privileges:
        - all

6. Add a "btw" user::

      sudo /usr/share/elasticsearch/bin/shield/esusers useradd btw -r btw_admin,kibana_user

Solr
----

You can find a lot of talk about how Solr is able to load XML
documents. This is a true statement but one that is misleading. It
means that you can use XML rather than JSON to put documents in Solr,
not that Solr is able to index XML documents like eXist or BaseX are
able to.

XML Database choices for BTW
============================

This investigation was performed in October 2015.

We started with the list of databases at: https://en.wikipedia.org/wiki/XML_database

Out of BaseX, Berkeley DB XML Edition, eXist-db, MarkLogic and Qizx
only the first 3 are open-source.

Berkeley DB XML Edition
-----------------------

Documentation says that it supports only XQuery 1.0, which is
ancient. Produced by Oracle and consequently exhibits the typical
Oracle documentation (monolithic, hard to read, etc.)

Base X
------

Problems:

- Issuing a db creation command with a db name that already exists
  will wipe the existing db. This can be worked around.

- Any change to the database flushes the indexes until they are
  explicitly rebuilt. There is an autoindexing mode but it is
  recommended only for small to medium databases. This could probably
  be worked around but seems stupid. What's the point of having a
  **database** system if indexing has to be managed
  explicitly. (http://docs.basex.org/wiki/Index#Updates)

- Speed tests with extracting all semantic fields from published
  articles with the real BTW database (at the time of 2015/10/15) do
  not show any speed improvement over a naive lxml-based scan.

eXist-db
--------

- Does not fully support XQuery 3.0. For some of the XQuery functions it
requires the use of eXist-db-specific extensions. (Why not provide an
alias???) Needs the use of custom extensions for supporting what
XQuery Update and XQuery Full Text provide.

- However, eXist-db has "real indexes" that are updated as the data is
  updated rather than flushed whenever the data is updated like BaseX
  does.

- The same speed tests as BaseX show that it is not faster than our
  naive lxml-based scan.

Overall, when we *are* ready to add an XML-based database to BTW this
should be the choice.

eXist-db vs lxml
----------------

It is difficult to quantify the speed difference between using
``lxml`` to extract data from XML documents and using eXist-db. The
tests conducted using the custom ``extract`` command (which extracts
semantic fields from articles) did not show much difference in
speed. Mind you, this test is one which does not actually take full
advantage of eXist-db. The query made is pretty simple (get all
``btw:sf`` elements from the documents) so there is not much
optimization that eXist-db can perform on the query. It is likely that
more sophisticated queries would operate faster with eXist-db than
custom ``lxml`` code.

Backend Transformations
=======================

We checked how fast it would be to apply the transformations performed
by ``btw_view.js`` to an article in the backend (server-side). For
these tests we converted the prasada article 10 times. The Chrome and
Phantom tests were conducted by contacting a tornado server that
started Chrome or Phantom and passed the data to them and retrieved it
back. See the notes under the Saxon test to see how it differs.

Chrome 51:

real    0m6.173s
user    0m0.080s
sys     0m0.020s

PhantomJS 2.1.1

real    0m3.399s
user    0m0.068s
sys     0m0.032s

Saxon 9.4.0.4 with an XSL 2 transform:

real    0m6.241s
user    0m14.260s
sys     0m0.780s

The Saxon test is really an underestimate of the cost of running an
XLST 2 transform because the transform used was the xml-to-html
transform which does almost nothing. None of the reordering and
processing of semantic fields, for instance was done. Moreover this
was done with a bash script whereas the 2 earlier tests were done with
a Tornado server receiving queries on a Unix socket. So the cost of
processing the queries is not accounted for in this test.

I may actually be possible to improve this by having saxon be a
service rather than restarting it for every iteration. The time spent
compiling the stylesheet would be saved. However, there is no ready
way to test this. And the stylesheet is super simple so the time saved
is not great. Even halving the time would make it similar to Phantom
in performance.

Backup System Choice for BTW
============================

From the time BTW became an actual web site to Spring 2016, BTW used
copy.com to store off-site backups. copy.com announced in Winter 2016
that they'd close in May 2016. We needed a new setup.

Copy.com offered 20GB free. As of April 2016, BTW used 8.7GB of that memory.

AWS
---

Estimate about $2/month.

Dropbox
-------

2GB free, which is way too small.

Google Drive
------------

15GB free.

No official Linux support.

There is no sanctioned daemon to keep a local folder in sync with the
drive. Many projects started but seem to have stalled.

The only viable option seems to be https://www.insynchq.com which
costs $25 a year for "organizations".

Hubic
-----

On paper Hubic seems great. 25GB free.

We actually tried Hubic and found it to be buggy. It looks like if a
file was being modified while Hubic was working on it, it caused a
conflict and could corrupt the file.

OneDrive
--------

No official Linux support.

Amazon Cloud Drive
------------------

No free plan.

Yandex
------

Located in Russia. Russian law being the way it is, best to avoid.

Websockets
==========

October 2015.

As I had long suspected, the whole notion of just adding a nonblocking event loop to a blocking app is utter nonsense. See https://uwsgi-docs.readthedocs.org/en/latest/articles/OffloadingWebsocketsAndSSE.html

When we want to add websockets to BTW, it is worth taking a look at
https://pypi.python.org/pypi/django-websocket-redis

..  LocalWords: uwsgi sqlite backend Django init py env config btw
..  LocalWords:  Zotero Zotero's zotero BTW's auth
