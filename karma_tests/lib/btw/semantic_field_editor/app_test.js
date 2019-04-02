/* global chai describe afterEach beforeEach before after it fixture */
/* eslint-env module */
// eslint-disable-next-line import/no-extraneous-dependencies
import $ from "jquery";
import sinon from "sinon";
import velocity from "velocity";
import Promise from "bluebird";
import { BoneBreaker, isInViewText } from "testutils/backbone";
import { FetcherServer as TestServer } from "testutils/fetcher_server";
import { waitFor } from "testutils/util";
// eslint-disable-next-line import/no-extraneous-dependencies
import Bb from "backbone";
import SFEditor from "btw/semantic_field_editor/app";
import { SFFetcher } from "btw/semantic-field-fetcher";
import { SearchEngine } from "testutils/search";
// eslint-disable-next-line import/no-extraneous-dependencies
import _ from "lodash";
import URI from "urijs/URI";

const { assert } = chai;

const fetcherUrl = "/en-us/semantic-fields/semanticfield/";
const fetcherUrlRe = /^\/en-us\/semantic-fields\/semanticfield\/(.*)$/;

class AppServer extends TestServer {
  constructor(options) {
    super(_.omit(options, ["engine"]));
    this.engine = options.engine;
  }

  respond(request) {
    super.respond(request);
    if (request.status === 200) {
      return;
    }

    const uri = new URI(request.url);
    if (uri.path() === fetcherUrl) {
      this.engine.respond(request);
    }
  }
}

class AppUtil {
  constructor(app) {
    this.app = app;
  }

  get searchDiv() {
    return this.app.layoutView.el.querySelector(".sf-search");
  }

  get searchInput() {
    return this.searchDiv.querySelector(".form-inline [name=search]");
  }

  getSearchResult(index) {
    return this.searchDiv.getElementsByClassName("sf-breadcrumb-view")[index];
  }
}

describe("SFEditor", () => {
  let app;
  let appUtil;
  let server;
  let renderDiv;
  let breaker;
  const searchEngine = new SearchEngine(25);
  const paths = ["02.02.18n", "02.02.19n", "01.04.04n"];
  const verboseServer = false;

  before(() => {
    // Make all animations be instantaneous so that we don't spend
    // seconds waiting for them to happen.
    velocity.mock = true;

    breaker = new BoneBreaker(Bb);

    fixture.setBase(
      "karma_tests/lib/btw/semantic_field_editor/views/navigators");
  });

  after(() => {
    server.restore();
    velocity.mock = false;
    breaker.uninstall();
  });

  beforeEach(() => {
    const renderParent = document.body;
    renderDiv = renderParent.ownerDocument.createElement("div");
    renderParent.appendChild(renderDiv);

    server = new AppServer({
      fetcherUrlRe,
      engine: searchEngine,
      verboseServer,
    });
    const fetcher = new SFFetcher(fetcherUrl, undefined);
    return fetcher.fetch(paths)
      .then((resolved) => {
        const fields = _.values(resolved);
        app = new SFEditor({
          container: renderDiv,
          fields,
          fetcher,
          searchUrl: fetcherUrl,
        });
        app.start();
        appUtil = new AppUtil(app);
      });
  });

  afterEach(() => {
    breaker.neutralize();
    // $(renderDiv, "*").velocity("stop", true);
    app.destroy();
    // Yep, we add back bunk data to prevent a failure.
    // $(renderDiv, "velocity-animating").data("velocity", {});
    if (renderDiv && renderDiv.parentNode) {
      renderDiv.parentNode.removeChild(renderDiv);
    }
    server.restore();
  });

  it("shows the list of fields passed to it at startup",
     // We just want to know that it has been displaying the fields. So
     // we do not check for each path.
     () => Promise.try(() => assert.isTrue(isInViewText(
       app.layoutView.getChildView("fieldList"),
       paths[0]))));

  describe("#getChosenFields", () => {
    it("returns an array containing the fields passed at startup", () => {
      assert.sameMembers(_.map(app.getChosenFields(), x => x.get("path")),
                         paths);
      return Promise.resolve();
    });

    it("exludes form the return those fields that the user deleted", () => {
      const button = app.layoutView.el.querySelector(
        ".sf-field-list .delete-button");
      button.click();
      assert.sameMembers(_.map(app.getChosenFields(), x => x.get("path")),
                         paths.slice(1));
      return Promise.resolve();
    });
  });

  function searchSomething() {
    const { searchDiv } = appUtil;
    const input = appUtil.searchInput;
    input.value = "Foo";
    $(input).trigger("input");
    return waitFor(() => searchDiv.textContent.indexOf("No results") === -1);
  }

  it("launches navigators", Promise.coroutine(function *display() {
    yield searchSomething();
    assert.equal(app._chosenFieldCollection.length, 3);
    assert.equal(app.combinatorView.elementsCollection.length, 0);
    assert.equal(app.navigatorsView.collection.length, 0);
    const result = appUtil.getSearchResult(0);
    const button = result.getElementsByClassName("sf-link")[0];
    button.click();
    assert.equal(app._chosenFieldCollection.length, 3);
    assert.equal(app.combinatorView.elementsCollection.length, 0);
    assert.equal(app.navigatorsView.collection.length, 1);
  }));

  it("allows searching", () => searchSomething());

  describe("from search results", () => {
    it("can choose fields", Promise.coroutine(function *display() {
      yield searchSomething();

      // We do not test sf:chosen:change separately. We test it together with
      // every action that triggers a change in the chosen fields.
      const stub = sinon.stub();
      app.on("sf:chosen:change", stub);

      assert.equal(app._chosenFieldCollection.length, 3);
      const result = appUtil.getSearchResult(0);
      const button = result.getElementsByClassName("sf-add")[0];
      button.click();
      assert.equal(app._chosenFieldCollection.length, 4);

      assert.isTrue(stub.calledOnce);
    }));

    it("can combine fields", Promise.coroutine(function *display() {
      yield searchSomething();

      assert.equal(app._chosenFieldCollection.length, 3);
      assert.equal(app.combinatorView.elementsCollection.length, 0);
      const result = appUtil.getSearchResult(0);
      const button = result.getElementsByClassName("sf-combine")[0];
      button.click();
      assert.equal(app._chosenFieldCollection.length, 3);
      assert.equal(app.combinatorView.elementsCollection.length, 1);
    }));
  });

  describe("from navigators", () => {
    it("can choose fields", Promise.coroutine(function *display() {
      yield searchSomething();

      const stub = sinon.stub();
      app.on("sf:chosen:change", stub);

      const navView = app.navigatorsView;
      assert.equal(navView.collection.length, 0);
      const result = appUtil.getSearchResult(0);
      let button = result.getElementsByClassName("sf-link")[0];
      button.click();
      assert.equal(navView.collection.length, 1);

      assert.equal(app._chosenFieldCollection.length, 3);
      button =
        yield waitFor(() => navView.el.getElementsByClassName("sf-add")[0]);
      button.click();
      assert.equal(app._chosenFieldCollection.length, 4);

      assert.isTrue(stub.calledOnce);
    }));

    it("can combine fields", Promise.coroutine(function *display() {
      yield searchSomething();

      const navView = app.navigatorsView;
      assert.equal(navView.collection.length, 0);
      const result = appUtil.getSearchResult(0);
      let button = result.getElementsByClassName("sf-link")[0];
      button.click();
      assert.equal(navView.collection.length, 1);

      assert.equal(app.combinatorView.elementsCollection.length, 0);
      button =
        yield waitFor(() => navView.el.getElementsByClassName("sf-combine")[0]);
      button.click();
      assert.equal(app.combinatorView.elementsCollection.length, 1);
    }));
  });

  describe("from combinator", () => {
    it("can choose fields", Promise.coroutine(function *display() {
      yield searchSomething();

      const stub = sinon.stub();
      app.on("sf:chosen:change", stub);

      assert.equal(app._chosenFieldCollection.length, 3);
      assert.equal(app.combinatorView.elementsCollection.length, 0);
      const result = appUtil.getSearchResult(0);
      let button = result.getElementsByClassName("sf-combine")[0];
      button.click();
      assert.equal(app._chosenFieldCollection.length, 3);
      assert.equal(app.combinatorView.elementsCollection.length, 1);

      [button] = app.combinatorView.resultView.ui.addButton;

      assert.equal(app._chosenFieldCollection.length, 3);

      yield waitFor(() => app.combinatorView.resultCollection.length === 1);
      button.click();

      assert.equal(app._chosenFieldCollection.length, 4);
      assert.isTrue(stub.calledOnce);
    }));
  });
});
