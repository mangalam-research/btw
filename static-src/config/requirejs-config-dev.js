require.config({
 baseUrl: '/static/lib/',
 paths: {
   'jquery': 'jquery-1.9.1',
   'qunit': 'qunit-1.12.0',
   'bootstrap': 'bootstrap/js/bootstrap.min',
     // For bibsearch
   'modules': '/static/scripts/modules'
 },
 shim: {
   'bootstrap': {
     deps: ["jquery"],
     exports: "jQuery.fn.popover",
     init: function () { jQuery.noConflict() }
   },
   'bootstrap-contextmenu': {
     deps: ["bootstrap"],
     exports: "jQuery.fn.contextmenu"
   },
   'rangy/rangy-core': {
     exports: "rangy",
     init: function() { return this.rangy; }
   },
   'rangy/rangy-selectionsaverestore': {
     deps: ["rangy/rangy-core"],
     exports: "rangy.modules.SaveRestore"
   },
   'wed/jquery.findandself': {
     deps: ["jquery"],
     exports: "jQuery.fn.findAndSelf"
   },
   'jquery.bootstrap-growl': {
     deps: ["jquery", "bootstrap"],
     exports: "jQuery.bootstrapGrowl"
   },
   'jquery.cookie': {
     deps: ["jquery"],
     exports: "jQuery.cookie"
   },
   'mocha/mocha': {
     exports: "mocha",
     init: function () { this.mocha.setup('bdd'); return this.mocha; }
   },
   'log4javascript': {
       exports: "log4javascript"
   },
   'qunit': {
       exports: 'QUnit',
       init: function () { this.QUnit.config.autostart = false;
                           return this.QUnit; }
   }
 },
 config: {
     "wed/wed": {
         schema: "btw/btw-storage.js",
         mode: {
             path: "btw/btw_mode",
             options: {
                 bibl_info_url: "/search/<itemKey>/info",
                 bibl_abbrev_url: "/search/<itemKey>/abbrev"
             }
         }
     }
 },
 enforceDefine: true
});
