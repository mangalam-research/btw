/* global jQuery XRegExp */
require.config({
  baseUrl: "/static/lib/",
  paths: {
    text: "requirejs/text",
    optional: "requirejs/optional",
    jquery: "external/jquery",
    bootstrap: "external/bootstrap/js/bootstrap",
    log4javascript: "external/log4javascript",
    "jquery.bootstrap-growl": "external/jquery.bootstrap-growl",
    "font-awesome": "external/font-awesome",
    "jquery.cookie": "external/jquery.cookie",
    "datatables.net": "external/datatables/js/jquery.dataTables.min",
    "datatables.bootstrap": "external/datatables/js/dataTables.bootstrap",
    "bootstrap-editable": "external/bootstrap3-editable/js/bootstrap-editable",
    "bootstrap-datepicker":
    "external/bootstrap-datepicker/js/bootstrap-datepicker",
    "pubsub-js": "external/pubsub",
    xregexp: "external/xregexp",
    "jquery.growl": "external/jquery-growl/js/jquery.growl",
    typeahead: "external/typeahead.bundle.min",
    modules: "/static/scripts/modules",
    localforage: "external/localforage",
    bluebird: "external/bluebird.min",
    moment: "external/moment",
    interact: "external/interact.min",
    "merge-options": "external/merge-options",
    "is-plain-obj": "external/is-plain-obj",
    velocity: "external/velocity/velocity.min",
    "velocity-ui": "external/velocity/velocity.ui.min",
    bluejax: "external/bluejax",
    "bluejax.try": "external/bluejax.try",
    "last-resort": "external/last-resort",
    "lucene-query-parser": "external/lucene-query-parser",
    urijs: "external/urijs",
    "bootstrap-treeview": "external/bootstrap-treeview.min",
    backbone: "external/backbone",
    marionette: "external/backbone.marionette",
    "backbone-forms": "external/backbone-forms/backbone-forms",
    "backbone.paginator": "external/backbone.paginator",
    "backbone-relational": "external/backbone-relational",
    underscore: "external/underscore-min",
    handlebars: "external/handlebars.min",
    "backbone.radio": "external/backbone.radio.min",
    "twbs-pagination": "external/jquery.twbsPagination",
    dragula: "external/dragula.min",
    ResizeObserver: "external/ResizeObserver",
    salve: "external/salve.min",
    "salve-dom": "external/salve-dom",
    "rangy-core": "external/rangy/rangy-core",
    "rangy-textrange": "external/rangy/rangy-textrange",
    "bootstrap-notify": "external/bootstrap-notify",
    ajv: "external/ajv.min",
    rxjs: "external/rxjs",
    diff: "external/diff",
    dexie: "external/dexie.min",
    bootbox: "external/bootbox",
  },
  map: {
    "*": {
      // This is needed due to the disconnect between the hardcoded name
      // in the file that is shipped by interactjs and the name of the npm
      // package.
      interactjs: "interact",
      velocity: "velocity-glue",
      bluebird: "bluebird-glue",
      jquery: "jquery-glue",
      backbone: "backbone-glue",
      marionette: "marionette-glue",
      bootstrap: "wed/patches/bootstrap",
      datatables: "datatables.net",
      "btw/btw-storage-metadata.json": "text!btw/btw-storage-metadata.json",
      "wed/modes/generic/metadata-schema.json": "json!wed/modes/generic/metadata-schema.json",
      "wed/wed-options-schema.json": "json!wed/wed-options-schema.json",
      "wed/options-schema.json": "json!wed/options-schema.json",
      rangy: "wed/glue/rangy-glue",
    },
    "jquery-glue": {
      jquery: "jquery",
    },
    "velocity-glue": {
      velocity: "velocity",
    },
    "bluebird-glue": {
      bluebird: "bluebird",
    },
    "backbone-glue": {
      backbone: "backbone",
    },
    "marionette-glue": {
      marionette: "marionette",
    },
    "wed/glue/rangy-glue": {
      rangy: "rangy-core",
    },
    marionette: {
      backbone: "backbone",
      marionette: "marionette",
    },
    "wed/patches/bootstrap": {
      bootstrap: "bootstrap",
    },
    // bootbox is buggy. It only requires jquery but it needs bootstrap too.
    // Loading bootstrap works due to the init we have below which makes
    // bootstrap return $.
    bootbox: {
      jquery: "bootstrap",
    },
  },
  packages: [
    {
      name: "lodash",
      location: "external/lodash",
    },
  ],
  bundles: {
  },
  shim: {
    xregexp: {
      // RequireJS wants to have this here even if the ``init`` field
     // makes it pointless.
      exports: "XRegExp",
      // We do it this way because salve is developed in Node and in
      // Node when we require XRegExp we get a module which has an
      // XRegExp field on it.
      init: function init() {
        "use strict";
        return { XRegExp: XRegExp };
      },
    },
    bootstrap: {
      deps: ["jquery"],
      exports: "jQuery.fn.popover",
      init: function init($) {
        "use strict";
        return $;
      },
    },
    "bootstrap-treeview": {
      deps: ["bootstrap"],
      exports: "jQuery.fn.treeview",
    },
    "external/rangy/rangy-core": {
      exports: "rangy",
      init: function init() {
        "use strict";
        return this.rangy;
      },
    },
    "external/rangy/rangy-selectionsaverestore": {
      deps: ["external/rangy/rangy-core"],
      exports: "rangy.modules.SaveRestore",
    },
    "jquery.bootstrap-growl": {
      deps: ["jquery", "bootstrap"],
      exports: "jQuery.bootstrapGrowl",
    },
    "jquery.cookie": {
      deps: ["jquery"],
      exports: "jQuery.cookie",
    },
    "bootstrap-editable": {
      deps: ["bootstrap"],
      exports: "jQuery.fn.editable",
    },
    "bootstrap-datepicker": {
      deps: ["bootstrap"],
      exports: "jQuery.fn.datepicker",
    },
    "jquery.growl": {
      deps: ["jquery"],
      exports: "jQuery.growl",
    },
    typeahead: {
      deps: ["jquery"],
      exports: "Bloodhound",
    },
    "twbs-pagination": {
      deps: ["bootstrap"],
      exports: "jQuery.fn.twbsPagination",
    },
  },
  waitSeconds: 12,
  enforceDefine: true,
});
