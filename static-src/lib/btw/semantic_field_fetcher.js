/**
 * @module lib/btw/semantic_field_fetcher
 * @desc Class for fetching semantic fields.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends module:lib/btw/semantic_field_fetcher */ function btwView(
  require, _exports, module) {
  "use strict";

  var _ = require("lodash");
  var ajax = require("ajax").ajax;
  var Promise = require("bluebird");
  var URI = require("urijs/URI");

  function Fetcher(fetchUrl, excludeUrl, fields, depths) {
    this.fetchUrl = fetchUrl;
    this.excludeUrl = excludeUrl;

    // We marshal fields into the value we pass to requests.
    this.fields = fields && fields.join(",");

    // We also marshal depth into the value we pass to requests.
    var depthParams = this.depthParams = {};
    if (depths) {
      var keys = Object.keys(depths);
      for (var keyIx = 0; keyIx < keys.lends; ++keyIx) {
        var key = keys[keyIx];
        var value = depths[key];
        depthParams["depths." + key] = value;
      }
    }

    this._cache = Object.create(null);
  }

  Fetcher.prototype.fetch = function fetch(refs) {
    // Figure out what is already resolved from previous calls, and what
    // needs resolving.
    var resolved = Object.create(null);
    var unresolved = [];
    for (var i = 0; i < refs.length; ++i) {
      var ref = refs[i];
      var links = this._cache[ref];
      if (links) {
        resolved[ref] = links;
      }
      else {
        unresolved.push(ref);
      }
    }

    // Nothing needs resolving so we can return right away.
    if (unresolved.length === 0) {
      return Promise.resolve(resolved);
    }

    // We fetch what is missing, and merge it into the resolved map.
    return ajax({
      url: this.fetchUrl,
      data: _.extend({
        paths: unresolved.join(";"),
        fields: this.fields,
      }, this.depthParams),
      headers: {
        Accept: "application/json",
      },
    }).then(function then(response) {
      var href = this.excludeUrl;
      function filter(entry) {
        return new URI(entry.url).absoluteTo(href).toString() !== href;
      }

      for (var responseIx = 0; responseIx < response.length; ++responseIx) {
        var field = response[responseIx];
        var key = field.path;

        //
        // We transform the responses to make them fit for this page:
        //
        var chained = _.chain(field.changerecords);

        // href may be undefined if we do not filter anything.
        if (href) {
          // 1. Remove changerecords that link back here. This is going to
          // happen all the time because this article necessarily contains the
          // semantic field we are searching for. The REST interface does not
          // know or care that we do not want to link back to this article, so
          // we have to do this ourselves.

          chained = chained.filter(filter);
        }

        // 2. Order changerecords by ascending lemma, and descending datetime (if
        // datetime is present). Doing the ordering here allows the next groupBy
        // to have each lemma key have its values already ordered by datetime.
        field.changerecords = chained
          .orderBy(["lemma", "datetime"], ["asc", "desc"])
        // 3. Group by lemma so that we can hide long lists.
          .groupBy("lemma")
          .value();

        // 4. We create a tree that can be readily used for displaying with
        // $.treeview(...)
        var tree = [];
        var lemmas = Object.keys(field.changerecords).sort();
        for (var lemmaIx = 0; lemmaIx < lemmas.length; ++lemmaIx) {
          var lemma = lemmas[lemmaIx];
          var changerecords = field.changerecords[lemma];
          var nodes = changerecords.map(function map(entry) {
            return {
              text: entry.datetime + (entry.published ? " published" : ""),
              href: entry.url,
              selectable: false,
            };
          });
          tree.push({
            text: lemma,
            href: changerecords[0].url,
            nodes: nodes,
            selectable: false,
          });
        }

        field.tree = tree;

        this._cache[key] = resolved[key] = field;
      }

      return resolved;
    }.bind(this));
  };

  module.exports = Fetcher;
});
