define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var Handlebars = require("handlebars");
  var _ = require("lodash");

  var linkTemplate = Handlebars.compile(
    "<a class='btn btn-default btn-sm sf-link' href='{{ url }}'>" +
      "{{ heading }}{{#if includePos}} ({{verbose_pos}}){{/if}}</a>");

  Handlebars.partials["field/linkTemplate"] = linkTemplate;

  var otherPosTemplate = Handlebars.compile("\
<p><label> Other parts of speech: \
{{#each related_by_pos}} \
<span class='sf-other-pos'>{{> field/linkTemplate includePos=true }}</span> \
{{/each}}\
</label></p>");

  Handlebars.partials["field/otherPosTemplate"] = otherPosTemplate;

  var breadcrumbTemplate = Handlebars.compile("\
{{#if parent}}\
{{> field/breadcrumbTemplate parent includePos=false}} > \
{{/if}}\
{{> field/linkTemplate includePos=includePos}} \
");

  Handlebars.partials["field/breadcrumbTemplate"] = breadcrumbTemplate;

  var breadcrumbWrapperTemplate = Handlebars.compile("\
<p><span class='sf-breadcrumbs'>{{> field/breadcrumbTemplate includePos=true}} \
{{path}}</span></p>\
{{#if related_by_pos }}\
{{> field/otherPosTemplate }}\
{{/if}}\
{{#if allDetails}}\
{{#if lexemes}}\
<p><label>Lexemes: \
<span class='sf-lexemes'>\
{{#each lexemes}} \
<span class='label label-default'>{{word}} {{fulldate}}</span>{{#unless @last}}, \
{{/unless}}\
{{/each}}\
</span>\
</label></p>\
{{/if}}\
{{#if children}}\
<p><label>Children: \
<span class='sf-children'>\
{{#each children}}{{>field/linkTemplate}}{{#unless @last}} {{/unless}}\
{{/each}}\
</span>\
</label></p>\
{{/if}}\
{{/if}}\
");

  var BreadcrumbView = Mn.ItemView.extend({
    initialize: function initialize(options) {
      this.details = this.details || options.details;

      Mn.ItemView.prototype.initialize.call(this, _.omit(options, "details"));
    },

    template: breadcrumbWrapperTemplate,
    templateHelpers: function templateHelpers() {
      return {
        allDetails: this.details === "all",
      };
    },

    modelEvents: {
      change: "render",
    },

    ui: {
      link: ".sf-link",
    },

    events: {
      "click @ui.link": "onLinkClick",
    },

    onLinkClick: function onLinkClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.triggerMethod("sf:selected", ev.currentTarget.href);
    },
  });

  return BreadcrumbView;
});
