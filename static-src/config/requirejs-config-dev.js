require.config({
 baseUrl: '/static/lib/',
 paths: {
   jquery: 'external/jquery-2.1.1',
   bootstrap: 'external/bootstrap/js/bootstrap.min',
   log4javascript: 'external/log4javascript',
   'jquery.bootstrap-growl': 'external/jquery.bootstrap-growl',
   'font-awesome': 'external/font-awesome',
   'jquery.cookie': 'external/jquery.cookie',
   datatables: 'external/datatables/js/jquery.dataTables',
   'datatables.bootstrap': 'external/datatables/js/dataTables.bootstrap',
   "bootstrap-editable": 'external/bootstrap3-editable/js/bootstrap-editable',
   qunit: 'external/qunit-1.12.0',
   'pubsub-js': 'external/pubsub',
   xregexp: 'external/xregexp',
     // For bibliography
   'modules': '/static/scripts/modules'
 },
 packages: [
     {
         name: "lodash",
         location: "external/lodash"
     }
 ],
 shim: {
   xregexp: {
     exports: "XRegExp",
     init: function () { return {XRegExp: XRegExp}; }
   },
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
   'bootstrap-editable': {
       deps: ["bootstrap"],
       exports: "jQuery.fn.editable"
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
                 bibl_search_url: "/bibliography/search/",
                 bibl_info_url: "/bibliography/<itemKey>/info",
                 bibl_abbrev_url: "/bibliography/<itemKey>/abbrev"
             }
         }
     }
 },
 enforceDefine: true
});
