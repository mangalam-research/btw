Requirements
============

Ace
---

django_ace: https://github.com/bradleyayers/django-ace

(DO I STILL WANT ACE?)

The ace code must be available in lexicography/static/lexicography/ace/

RequireJS
---------

The requirejs code must be available and its path set in the settings of BTW with the variable BTW_REQUIREJS_PATH and BTW_REQUIREJS_CONFIG must be set to a javascript fragment that calls requirejs' config.

jQuery
------

jQuery must be available for wed. If wed is using requirejs, then everything is taken care of. Otherwise, it must load before wed.

Bootstrap
---------

Nothing to say here...

wed
---

BTW_WED_USE_REQUIREJS must be true if requirejs is used to load wed.

BTW_WED_PATH= must point to the source of wed.
BTW_WED_CSS = must point to the css of wed.

salve
-----

...


Requirements for testing
========================

* node-amd-loader

* mocha
* chai
* sax
If you want to contribute to salve, your code will have to pass the
checks listed in `<.glerbl/repo_conf.py>`_. So you either have to
install glerbl to get those checks done for you or run the checks
through other means. See Contributing_.

Testing
=======

Javascript
----------

Javascript tests are of two types:

* Runnable outside a browser. We run these inside Node.js.

* Runnable inside a browser.

Some tests can be run both inside and outside a browser. This typically happens when a mock DOM setup is used in Node.js

Issues
======

There seem to be a small leakage of memory upon reloading a window
with Wed in it.

Tests performed with Chrome's memory profiler by doing:

1. One load.
2. Issuing a memory profile.
3. Reload.
4. Issuing a memory profile. 

Show that the whole Walker tree created before the first profile is
created still exists at the time of the second profile. I do not know
of a good explanation for this.

============
Contributing
============

Contributions must pass the commit checks turned on in
`<.glerbl/repo_conf.py>`. Use ``glerbl install`` to install the
hooks. Glerbl itself can be found at
https://github.com/lddubeau/glerbl. It will eventually make its way to
the Python package repository so that ``pip install glerbl`` will
work.
