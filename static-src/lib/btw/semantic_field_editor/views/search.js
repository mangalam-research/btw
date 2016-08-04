define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var _ = require("lodash");
  var $ = require("jquery");
  var Mn = require("marionette");
  var Bb = require("backbone");
  var Handlebars = require("handlebars");
  var panelTemplate = require("text!./panel.hbs");
  var queryFormTemplate = require("text!./query-form.html");
  var BreadcrumbView = require("./field/breadcrumb");
  var Field = require("../models/field");
  require("bootstrap");
  require("backbone.paginator");
  require("twbs-pagination");

  function id(x) {
    return function innerId() {
      return x;
    };
  }

  var ResultCollection = Bb.PageableCollection.extend({
    initialize: function initialize(models, options) {
      this.url = options.url;
      delete options.url;

      Bb.PageableCollection.prototype.initialize.apply(this, arguments);
    },

    model: Field,

    state: {
      firstPage: 0,
      currentPage: 0,
      pageSize: 10,
      totalRecords: 10,
      unfilteredTotal: 0,
      totalPages: 0,
    },

    // Init it empty so that immediate calls to getPage won't crash.
    searchParams: {
    },

    fetch: function fetch(options) {
      options = options || {};
      options.reset = true;
      return ResultCollection.__super__.fetch.call(this, options);
    },

    sync: function sync(method, model, options) {
      options.btwAjax = true;
      return Bb.sync.call(this, method, model, options);
    },

    queryParams: {
      currentPage: null,
      firstPage: null,
      pageSize: "limit",
      totalRecords: null,
      totalPages: null,
      unfilteredTotal: null,
      offset: function offset() {
        return this.state.currentPage * this.state.pageSize;
      },
      search: function search() {
        return this.searchParams.search;
      },
      scope: function scope() {
        return this.searchParams.scope;
      },
      aspect: function aspect() {
        return this.searchParams.aspect;
      },
      "depths.parent": -1,
      "depths.related_by_pos": 1,
      fields: "@search",
    },

    parseRecords: function parseRecords(data) {
      return data.results;
    },

    parseState: function parseState(data, _params, state) {
      return {
        unfilteredTotal: data.unfiltered_count,
        totalRecords: data.count,
        totalPages: Math.ceil(data.count / state.pageSize),
      };
    },
  });

  var ResultRowView = BreadcrumbView.extend({
    tagName: "tr",
    template: function template() {
      var html = ResultRowView.__super__.template.apply(this, arguments);
      // We need to wrap the original HTML in a td element.
      return "<td>" + html + "</td>";
    },
  });

  var NoResultView = Mn.LayoutView.extend({
    template: id("<p>No results</p>"),
  });

  function bubble(name) {
    return function bubbleUp(view, ev) {
      this.triggerMethod(name, ev);
    };
  }

  // CompositeView is deprecated in v3 but there is no way to easily avoid it in
  // v2.4.5.
  var ResultCollectionView = Mn.CompositeView.extend({
    __classname__: "ResultCollectionView",
    initialize: function initialize(options) {
      this.canAddResults = options.canAddResults;
      ResultCollectionView.__super__.initialize.call(
        this, _.omit(options, ["canAddResults"]));
    },
    attributes: {
      // We need this for the spinner to be positioned properly.
      style: "position: relative;",
    },
    template: id("\
<table class='table table-striped'><tbody></tbody><tfoot></tfoot></table>\
<div class='table-processing' style='display: none;'>\
<i class='fa fa-spinner fa-2x fa-spin'></i>\
</div>\
"),
    childView: ResultRowView,
    childViewOptions: function childViewOptions() {
      // Yes, the name is different on the child. If the result collection can
      // add results, then the results themselves can be added.
      return {
        canBeAdded: this.canAddResults,
      };
    },
    emptyView: NoResultView,
    childViewContainer: "tbody",

    ui: {
      table: "table",
      foot: "tfoot",
      processing: ".table-processing",
    },

    footTemplate: Handlebars.compile("\
<div class='row'>\
  <div class='col-sm-5 footer-information'>\
    Showing {{start}} to {{end}} of {{totalRecords}} entries \
    (filtered from {{unfilteredTotal}} total entries)\
  </div>\
  <div class='col-sm-7'>\
    <div class='table-pagination'>\
      <nav aria-label='Table navigation'>\
        <ul class='pagination'></ul>\
      </nav>\
    </div>\
  </div>\
</div>"),

    collectionEvents: {
      reset: "_footRefresh",
      request: "_onRequest",
      sync: "_onSync",
    },

    _onRequest: function _onRequest() {
      this.ui.table[0].classList.add("loading");
      this.ui.processing[0].style.display = "";
    },

    _onSync: function _onSync() {
      this.ui.table[0].classList.remove("loading");
      this.ui.processing[0].style.display = "none";
    },

    _footRefresh: function footRefresh() {
      var foot = this.ui.foot[0];
      var collection = this.collection;
      var state = collection.state;

      if (state.totalRecords === 0) {
        foot.innerHTML = "";
        return;
      }

      var start = state.currentPage * state.pageSize;
      foot.innerHTML = this.footTemplate({
        // Make it 1-based for non-devs.
        start: start + 1,
        // The first argument is simplified from
        // (start + 1) + (state.pageSize - 1).
        end: Math.min(start + state.pageSize, state.totalRecords),
        totalRecords: state.totalRecords,
        unfilteredTotal: state.unfilteredTotal,
      });
      var pagination = foot.getElementsByClassName("pagination")[0];
      // twbsPagination is 1-based, whereas PageableCollection is 0-based.
      // Hence the base fixes below.
      $(pagination).twbsPagination({
        totalPages: state.totalPages,
        // Fix the base.
        startPage: state.currentPage + 1,
        visiblePages: 6,
        initiateStartPageClick: false,
        onPageClick: function onPageClick(ev, page) {
          // We need to fix the base here too.
          collection.getPage(page - 1);
        },
      });
    },
  });

  function makeHelpPopover(el, content) {
    $(el).popover({
      placement: "auto",
      content: content,
      html: "true",
    });
  }


  var QueryForm = Mn.ItemView.extend({
    className: "form-inline",
    template: id(queryFormTemplate),
    ui: {
      search: "[name=search]",
      searchHelpLabel: "i.search-help",
      searchHelp: "p.search-help",
      aspect: "[name=aspect]",
      aspectHelpLabel: "i.aspect-help",
      aspectHelp: "p.aspect-help",
      scope: "[name=scope]",
      scopeHelpLabel: "i.scope-help",
      scopeHelp: "p.scope-help",
    },

    triggers: {
      "input @ui.search": "change",
      "change @ui.aspect": "change",
      "change @ui.scope": "change",
    },

    serializeData: function serializeData() {
      var fields = ["search", "aspect", "scope"];
      var ret = {};
      for (var i = 0; i < fields.length; ++i) {
        var field = fields[i];
        ret[field] = this.ui[field][0].value;
      }
      return ret;
    },

    onRender: function onRender() {
      var names = ["searchHelp", "aspectHelp", "scopeHelp"];
      for (var i = 0; i < names.length; ++i) {
        var name = names[i];
        makeHelpPopover(this.ui[name + "Label"], this.ui[name][0].innerHTML);
      }
    },
  });

  var SearchView = Mn.LayoutView.extend({
    initialize: function initialize(options) {
      this.searchUrl = options.searchUrl;
      this.canAddResults = options.canAddResults;
      this.debounceTimeout = options.debounceTimeout !== undefined ?
        options.debounceTimeout : 500;

      this.collection = new ResultCollection(null, {
        url: this.searchUrl,
      });

      this.queryForm = new QueryForm();

      var change = function change() {
        this.triggerMethod("change", this.queryForm.serializeData());
      }.bind(this);

      this.queryForm.on("change",
                        this.debounceTimeout !== 0 ?
                        _.debounce(change, this.debounceTimeout) :
                        change);

      SearchView.__super__.initialize.call(
        this,
        _.omit(options, ["searchUrl", "canAddResults", "debounceTimeout"]));
    },

    template: Handlebars.compile(panelTemplate),

    templateHelpers: function templateHelpers() {
      return {
        collapse: true,
        headingId: "sf-editor-collapse-heading-" + this.cid,
        collapseId: "sf-editor-collapse-" + this.cid,
        panelTitle: "Semantic Field Search",
        panelBody: new Handlebars.SafeString(
          "<div class='search-form'></div><hr />" +
            "<div class='results'></div>"),
      };
    },

    regions: {
      searchForm: ".search-form",
      results: ".results",
    },

    childEvents: {
      "sf:selected": bubble("sf:selected"),
    },

    onChange: function onChange(params) {
      if (this.isRendered && params.search !== "") {
        this.collection.searchParams = params;
        this.collection.getPage(0);
      }
    },

    onRender: function onRender() {
      this.showChildView("results", new ResultCollectionView({
        collection: this.collection,
        canAddResults: this.canAddResults,
      }));
      this.showChildView("searchForm", this.queryForm);
    },
  });


  return SearchView;
});
