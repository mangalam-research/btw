require.config({
 baseUrl: '/static/lib/',
 paths: {
   'jquery': 'external/jquery-1.9.1',
   'bootstrap': 'external/bootstrap/js/bootstrap.min',
   'log4javascript': 'external/log4javascript',
   'jquery.bootstrap-growl': 'external/jquery.bootstrap-growl',
   'font-awesome': 'external/font-awesome',
   'jquery.cookie': 'external/jquery.cookie',
   'qunit': 'external/qunit-1.12.0',
     // For bibsearch
   'modules': '/static/scripts/modules'
 },
 shim: {
   'bootstrap': {
     deps: ["jquery"],
     exports: "jQuery.fn.popover",
     init: function () { jQuery.noConflict() }
   },
   'external/rangy/rangy-core': {
     exports: "rangy",
     init: function() { return this.rangy; }
   },
   'external/rangy/rangy-selectionsaverestore': {
     deps: ["external/rangy/rangy-core"],
     exports: "rangy.modules.SaveRestore"
   },
   'jquery.bootstrap-growl': {
     deps: ["jquery", "bootstrap"],
     exports: "jQuery.bootstrapGrowl"
   },
   'jquery.cookie': {
     deps: ["jquery"],
     exports: "jQuery.cookie"
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
