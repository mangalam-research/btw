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
  });

  var NoResultView = Mn.LayoutView.extend({
    template: id("<p>No results</p>"),
  });

  function bubble(name) {
    return function bubbleUp(view, ev) {
      this.triggerMethod(name, ev);
    };
  }

  // CompositeView is deprected in v3 but there is no way to easily avoid it in
  // v2.4.5.
  var ResultCollectionView = Mn.CompositeView.extend({
    __classname__: "ResultCollectionView",
    initialize: function initialize() {
      Mn.CompositeView.prototype.initialize.apply(this, arguments);
    },
    tagName: "table",
    className: "table table-striped",
    template: id("<tbody></tbody><tfoot></tfoot>"),
    childView: ResultRowView,
    emptyView: NoResultView,
    childViewContainer: "tbody",

    ui: {
      foot: "tfoot",
    },

    footTemplate: Handlebars.compile("\
<div class='row'>\
  <div class='col-sm-5'>\
    Showing {{ start }} to {{ end }} of {{ totalRecords }} entries \
    (filtered from {{ unfilteredTotal }} total entries)\
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
      update: "footRefresh",
    },

    footRefresh: function footRefresh() {
      var foot = this.ui.foot[0];
      var collection = this.collection;
      var state = this.collection.state;
      var start = state.currentPage * state.pageSize;
      foot.innerHTML = this.footTemplate({
        start: start,
        end: start + state.pageSize,
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

  var QueryForm = Mn.LayoutView.extend({
    className: "form-inline",
    template: id(queryFormTemplate),
    ui: {
      search: "[name=search]",
      searchHelp: ".search-help",
      aspect: "[name=aspect]",
      aspectHelp: ".aspect-help",
      scope: "[name=scope]",
      scopeHelp: ".scope-help",
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
  });

  var SearchView = Mn.LayoutView.extend({
    initialize: function initialize(options) {
      this.searchUrl = options.searchUrl;
      delete options.searchUrl;

      this.collection = new ResultCollection(null, {
        url: this.searchUrl,
      });

      this.queryForm = new QueryForm();
      this.queryForm.on(
        "change",
        _.debounce(function change() {
          this.triggerMethod("change",
                             this.queryForm.serializeData());
        }.bind(this), 500));

      Mn.LayoutView.prototype.initialize.apply(this, arguments);
    },

    template: Handlebars.compile(panelTemplate),

    templateHelpers: {
      panelTitle: "Semantic Field Search",
      panelBody: new Handlebars.SafeString(
        "<div class='search-form'></div><hr />" +
          "<div class='results'></div>"),
    },

    regions: {
      searchForm: ".search-form",
      results: ".results",
    },

    childEvents: {
      "sf:selected": bubble("sf:selected"),
    },

    onChange: function onChange(params) {
      if (this.shown) {
        this.collection.searchParams = params;
        this.collection.getPage(0);
      }
    },

    onShow: function onShow() {
      this.shown = true;
      this.showChildView("results", new ResultCollectionView({
        collection: this.collection,
      }));
      this.showChildView("searchForm", this.queryForm);
    },
  });


  return SearchView;
});
