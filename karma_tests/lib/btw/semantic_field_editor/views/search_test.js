/* global chai describe afterEach beforeEach before after it */
/* eslint-env module */
import $ from "jquery";
import Promise from "bluebird";
import { BoneBreaker, waitForEventOn, isInViewText } from "testutils/backbone";
import XHRGrabber from "testutils/xhr_grabber";
import { waitFor } from "testutils/util";
import Bb from "backbone";
import SearchView from "btw/semantic_field_editor/views/search";
import SearchEngine from "testutils/search";
import URI from "urijs/URI";
import _ from "lodash";
import Handlebars from "handlebars";
import sinon from "sinon";

const assert = chai.assert;

const fetcherUrl = "/en-us/semantic-fields/semanticfield/";

describe("SearchView", () => {
  let view;
  let renderDiv;
  let breaker;
  let grabber;
  const searchEngine = new SearchEngine(25);
  const constantFields = {
    "depths.parent": "-1",
    "depths.related_by_pos": "1",
    fields: "@search",
  };

  before(() => {
    breaker = new BoneBreaker(Bb);
    grabber = new XHRGrabber();
  });

  after(() => {
    breaker.uninstall();
    grabber.restore();
  });

  function makeAndRender(options) {
    view = new SearchView(_.extend({
      debounceTimeout: 0,
    }, options));
    view.setElement(renderDiv);
    view.render();
  }

  beforeEach(() => {
    const renderParent = document.body;
    renderDiv = renderParent.ownerDocument.createElement("div");
    renderParent.appendChild(renderDiv);
    grabber.clear();
  });

  afterEach(() => {
    breaker.neutralize();
    view.destroy();
    if (renderDiv && renderDiv.parentNode) {
      renderDiv.parentNode.removeChild(renderDiv);
    }
  });

  function* threePageQuery() {
    const input = view.queryForm.ui.search[0];
    const $input = $(input);
    input.value = "Foo";
    $input.trigger("input");
    yield waitFor(() => grabber.hasRequests());

    const request = grabber.getSingleRequest();
    const uri = new URI(request.url);
    assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
    grabber.clear();
    // We want to respond to the request so that we have more than one
    // page.
    searchEngine.respond(request);
    yield waitFor(
      () => view.el.querySelectorAll(".table-pagination .page")
        .length === 3);
  }

  describe("issues a search on", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    function* test(uiElement, event) {
      // The search field must always be populated.
      const searchField = view.queryForm.ui.search[0];
      searchField.value = "Foo";

      const input = view.queryForm.ui[uiElement][0];
      input.value = "Foo";
      const $input = $(input);
      $input.trigger(event);
      yield waitFor(() => grabber.hasRequests());

      let request = grabber.getSingleRequest();
      let uri = new URI(request.url);
      assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
      grabber.clear();
      $input.trigger(event);
      yield waitFor(() => grabber.hasRequests());

      request = grabber.getSingleRequest();
      uri = new URI(request.url);
      assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
      grabber.clear();
    }

    const inputsAndEvents = [
      ["search", "input"],
      ["aspect", "change"],
      ["scope", "change"],
    ];

    for (const [uiElement, event] of inputsAndEvents) {
      it(`changes in the ${uiElement} field`,
         Promise.coroutine(test.bind(undefined, uiElement, event)));
    }

    it("clicks on page numbers", Promise.coroutine(function* click() {
      yield Promise.coroutine(threePageQuery)();

      // Click the 2nd page button.
      const pageButtons = view.el.querySelectorAll(".table-pagination .page");
      grabber.clear();
      pageButtons[1].click();
      yield waitFor(() => grabber.hasRequests());

      const request = grabber.getSingleRequest();
      const uri = new URI(request.url);
      assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
      grabber.clear();
    }));

    it("clicks on the next page button", Promise.coroutine(function* click() {
      yield Promise.coroutine(threePageQuery)();

      const nextButton = view.el.querySelector(".table-pagination .next");
      grabber.clear();
      nextButton.click();
      yield waitFor(() => grabber.hasRequests());

      const request = grabber.getSingleRequest();
      const uri = new URI(request.url);
      assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
      grabber.clear();
    }));

    it("clicks on the previous page button",
       Promise.coroutine(function* click() {
         yield Promise.coroutine(threePageQuery)();
         view.collection.getLastPage();
         yield waitFor(() => grabber.hasRequests());
         let request = grabber.getSingleRequest();
         let uri = new URI(request.url);
         assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");

         searchEngine.respond(request, {
           offset: 20,
           limit: 10,
         });
         const prevButton = view.el.querySelector(".table-pagination .prev");

         yield waitFor(() => !prevButton.classList.contains("disabled"));

         grabber.clear();
         prevButton.click();
         yield waitFor(() => grabber.hasRequests());

         request = grabber.getSingleRequest();
         uri = new URI(request.url);
         assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
         grabber.clear();
       }));

    it("clicks on the first page button",
       Promise.coroutine(function* click() {
         yield Promise.coroutine(threePageQuery)();
         view.collection.getLastPage();
         yield waitFor(() => grabber.hasRequests());
         let request = grabber.getSingleRequest();
         let uri = new URI(request.url);
         assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");

         searchEngine.respond(request, {
           offset: 20,
           limit: 10,
         });
         const firstButton =
                 view.el.querySelector(".table-pagination .first");

         yield waitFor(() => !firstButton.classList.contains("disabled"));

         grabber.clear();
         firstButton.click();
         yield waitFor(() => grabber.hasRequests());

         request = grabber.getSingleRequest();
         uri = new URI(request.url);
         assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
         grabber.clear();
       }));
  });

  describe("does not issue a search", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    it("when the search field is empty", () => {
      const input = view.queryForm.ui.search[0];
      const $input = $(input);

      const spy = sinon.spy(view.collection, "getPage");
      // First test that it works when the input contains something.
      input.value = "Foo";
      $input.trigger("input");
      assert.isTrue(spy.calledOnce);

      // The call count should not increase.
      input.value = "";
      $input.trigger("input");
      assert.isTrue(spy.calledOnce);
      return Promise.resolve();
    });
  });

  describe("serializes the search parameters properly", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    it("on search changes", Promise.coroutine(
      function* serializes() {
        const searchInput = view.queryForm.ui.search[0];
        const aspect = view.queryForm.ui.aspect[0];
        const scope = view.queryForm.ui.scope[0];
        const baseQuery = _.extend({
          limit: "10",
          offset: "0",
          scope: "all",
          aspect: "sf",
        }, constantFields);

        searchInput.value = "Foo";
        $(searchInput).trigger("input");
        yield waitFor(() => grabber.hasRequests());

        let request = grabber.getSingleRequest();
        let uri = new URI(request.url);
        let query = uri.query(true);
        assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
        assert.deepEqual(query, _.extend({}, baseQuery, { search: "Foo" }));

        searchInput.value = "Bar";
        aspect.value = "lexemes";
        scope.value = "btw";
        grabber.clear();
        $(searchInput).trigger("input");
        yield waitFor(() => grabber.hasRequests());

        request = grabber.getSingleRequest();
        uri = new URI(request.url);
        query = uri.query(true);
        assert.equal(uri.path(), "/en-us/semantic-fields/semanticfield/");
        assert.deepEqual(query, _.extend({}, baseQuery, {
          search: "Bar",
          aspect: "lexemes",
          scope: "btw",
        }));
      }));

    it("on arbitrary page movements", Promise.coroutine(function* page() {
      const baseQuery = _.extend({}, constantFields, {
        limit: "10",
        scope: "all",
        aspect: "sf",
        search: "Foo",
      });

      yield Promise.coroutine(threePageQuery)();

      grabber.clear();
      view.collection.getPage(1);
      yield waitFor(() => grabber.hasRequests());

      let request = grabber.getSingleRequest();
      let uri = new URI(request.url);
      let query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "10", // We got the first page: start at 10.
      }));

      grabber.clear();
      view.collection.getNextPage();
      yield waitFor(() => grabber.hasRequests());
      request = grabber.getSingleRequest();
      uri = new URI(request.url);
      query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "20", // Next page.
      }));

      grabber.clear();
      view.collection.getPreviousPage();
      yield waitFor(() => grabber.hasRequests());
      request = grabber.getSingleRequest();
      uri = new URI(request.url);
      query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "10", // Previous page.
      }));

      grabber.clear();
      view.collection.getFirstPage();
      yield waitFor(() => grabber.hasRequests());
      request = grabber.getSingleRequest();
      uri = new URI(request.url);
      query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "0", // First page.
      }));
    }));
  });

  describe("shows correct footer information", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    it("when there are no results", Promise.coroutine(function* page() {
      yield Promise.coroutine(threePageQuery)();
      grabber.clear();
      const searchInput = view.queryForm.ui.search[0];
      $(searchInput).trigger("input");

      yield waitFor(() => grabber.hasRequests());
      const request = grabber.getSingleRequest();
      grabber.clear();

      const previousFooter = view.el.querySelector(".footer-information");

      const response = {
        count: 0,
        results: [],
        unfiltered_count: 1000,
      };

      // We provide an empty response.
      request.respond(200, { "Content-Type": "application/json" },
                      JSON.stringify(response));

      yield waitFor(() => previousFooter !==
                       view.el.querySelector(".footer-information"));

      assert.equal(view.el.querySelector("tfoot").childNodes.length, 0);
    }));

    it("on arbitrary page movements", Promise.coroutine(function* page() {
      const baseQuery = _.extend({}, constantFields, {
        limit: "10",
        scope: "all",
        aspect: "sf",
        search: "Foo",
      });

      const footerTemplate = Handlebars.compile(
        "Showing {{start}} to {{end}} of {{totalRecords}} entries \
    (filtered from {{unfilteredTotal}} total entries)");
      yield Promise.coroutine(threePageQuery)();

      let footerInformation = view.el.querySelector(".footer-information");
      assert.equal(footerInformation.textContent.trim().replace(/\s+/, " "),
                   footerTemplate({
                     start: 1,
                     end: 10,
                     totalRecords: 25,
                     unfilteredTotal: 1000,
                   }));

      let previousFooterText = footerInformation.textContent;

      function footerRefreshed() {
        return waitFor(() => previousFooterText !==
                       view.el.querySelector(".footer-information"));
      }

      grabber.clear();
      view.collection.getPage(1);
      yield waitFor(() => grabber.hasRequests());

      let request = grabber.getSingleRequest();
      let uri = new URI(request.url);
      let query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "10", // We got the first page: start at 10.
      }));

      searchEngine.respond(request);
      yield footerRefreshed();
      // We need to grab it again because the old one gets obliterated.
      footerInformation = view.el.querySelector(".footer-information");
      assert.equal(footerInformation.textContent.trim().replace(/\s+/, " "),
                   footerTemplate({
                     start: 11,
                     end: 20,
                     totalRecords: 25,
                     unfilteredTotal: 1000,
                   }));
      previousFooterText = footerInformation.textContent;

      grabber.clear();
      view.collection.getLastPage();
      yield waitFor(() => grabber.hasRequests());
      request = grabber.getSingleRequest();
      uri = new URI(request.url);
      query = uri.query(true);
      assert.deepEqual(query, _.extend({}, baseQuery, {
        offset: "20", // Last page.
      }));

      searchEngine.respond(request);
      yield footerRefreshed();
      // We need to grab it again because the old one gets obliterated.
      footerInformation = view.el.querySelector(".footer-information");
      assert.equal(footerInformation.textContent.trim().replace(/\s+/, " "),
                   footerTemplate({
                     start: 21,
                     end: 25,
                     totalRecords: 25,
                     unfilteredTotal: 1000,
                   }));
    }));
  });


  function* checkButtons(present) {
    yield Promise.coroutine(threePageQuery.bind(undefined, grabber))();
    const viewRoot = view.el;
    const breadrumbViews =
            viewRoot.getElementsByClassName("sf-breadcrumb-view");

    // Wait for a full page.
    yield waitFor(() => breadrumbViews.length === 10);

    // Wait for the views to be rendered.
    const firstView = breadrumbViews[0];
    yield waitFor(
      () => firstView.getElementsByClassName("sf-link").length !== 0);

    const count = present ? 1 : 0;
    assert.equal(firstView.getElementsByClassName("sf-add").length, count);
    assert.equal(firstView.getElementsByClassName("sf-combine").length, count);
  }

  describe("", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    it("shows 'No results' at startup", () =>
       waitFor(() => isInViewText(view, "No results")));

    function labelTest(label) {
      assert.isNull(view.el.querySelector(".popover"));
      const el = view.el.querySelector(`i.${label}-help`);
      el.click();
      return waitFor(() => view.el.querySelector(".popover") !== null);
    }

    for (const label of ["search", "aspect", "scope"]) {
      it(`clicking the ${label} help label brings a popover`,
         () => labelTest(label));
    }
  });

  describe("with canAddResults ``false``", () => {
    beforeEach(() => makeAndRender({
      searchUrl: fetcherUrl,
      canAddResults: false,
    }));

    it("does not crash on an immediate getPage", () => {
      view.collection.getPage(0);
      return Promise.resolve();
    });

    it("results do not contain add and combine buttons",
       Promise.coroutine(checkButtons.bind(undefined, false)));

    it("generates a sf:selected event when a link is clicked",
       () => Promise.coroutine(checkButtons.bind(undefined, false))().then(
         () => {
           const button = view.el.querySelector(".sf-breadcrumb-view .sf-link");
           return waitForEventOn(view, "sf:selected", () => button.click());
         }));
  });

  describe("with canAddResults ``true``", () => {
    beforeEach(() =>
      makeAndRender({
        searchUrl: fetcherUrl,
        canAddResults: true,
      }));

    it("results contain add and combine buttons",
       Promise.coroutine(checkButtons.bind(undefined, true)));

    // We do not test that the buttons emit on the radio, as this is done in the
    // breadcrumb views.
  });
});
