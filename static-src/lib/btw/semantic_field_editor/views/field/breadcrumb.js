define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var Bb = require("backbone");
  var Handlebars = require("handlebars");
  var _ = require("lodash");
  var tools = require("../../tools");

  var linkTemplate = Handlebars.compile(
    "<a class='btn btn-default btn-sm sf-link' href='{{url}}'>" +
      "{{heading}}{{#if includePos}} ({{verbose_pos}}){{/if}}</a>");

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
{{> field/breadcrumbTemplate parent includePos=false}} {{#if is_subcat}}::{{else}}>{{/if}} \
{{/if}}\
{{> field/linkTemplate includePos=includePos}} \
");

  Handlebars.partials["field/breadcrumbTemplate"] = breadcrumbTemplate;

  var breadcrumbWrapperTemplate = Handlebars.compile("\
<table class='sf-breadcrumb-view'>\
<tbody>\
<tr>\
{{#if helpers.canBeAdded}}\
<td class='control-column'>\
<a href='#' class='btn btn-default sf-add'><i class='fa fa-fw fa-thumbs-up'></i></a><br/>\
<a href='#' class='btn btn-default sf-combine'><i class='fa fa-fw fa-at'></i></a>\
</td>\
{{/if}}\
<td>\
<p><span class='sf-breadcrumbs'>{{> field/breadcrumbTemplate includePos=true}}\
</span>{{#if helpers.allDetails}} {{path}}{{/if}}</p>\
{{#if related_by_pos }}\
{{> field/otherPosTemplate }}\
{{/if}}\
{{#if helpers.allDetails}}\
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
</td>\
</tr>\
</tbody>\
</table>\
");

  var BreadcrumbView = Mn.ItemView.extend({
    __classname__: "BreadcrumbView",
    initialize: function initialize(options) {
      this.details = this.details || options.details;
      this.canBeAdded = this.canBeAdded || options.canBeAdded;
      this._cachedApplication = null;
      this._cachedChannel = null;

      tools.GettersMixin.call(this);
      BreadcrumbView.__super__.initialize.call(
        this, _.omit(options, ["details", "canBeAdded"]));
    },

    template: breadcrumbWrapperTemplate,
    templateHelpers: function templateHelpers() {
      return {
        helpers: {
          allDetails: this.details === "all",
          canBeAdded: this.canBeAdded,
        },
      };
    },

    modelEvents: {
      change: "render",
    },

    ui: {
      link: ".sf-link",
      addButton: ".sf-add",
      combineButton: ".sf-combine",
    },

    events: {
      "mousedown .btn": "preventDefault",
      "click @ui.link": "onLinkClick",
      "click @ui.addButton": "onAddButtonClick",
      "click @ui.combineButton": "onCombineButtonClick",
    },

    getters: tools.communicationGetters,

    preventDefault: function preventDefault(ev) {
      ev.preventDefault();
    },

    onLinkClick: function onLinkClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.triggerMethod("sf:selected", ev.currentTarget.href);
    },

    onAddButtonClick: function onAddButtonClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.channel.trigger("sf:add", this, this.model);
    },

    onCombineButtonClick: function onCombineButtonClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.channel.trigger("sf:combine", this, this.model);
    },
  });

  return BreadcrumbView;
});