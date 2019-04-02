/* global chai describe afterEach beforeEach before after it fixture */
/* eslint-env module */
import velocity from "velocity";
import Promise from "bluebird";
import CombinatorView from "btw/semantic_field_editor/views/combinator";
import { SFFetcher } from "btw/semantic-field-fetcher";
import { BoneBreaker, waitForEventOn, doAndWaitForRadio }
from "testutils/backbone";
import { FetcherServer as TestServer } from "testutils/fetcher_server";
import * as urls from "testutils/urls";
// eslint-disable-next-line import/no-extraneous-dependencies
import Bb from "backbone";
import Mn from "marionette";
import sinon from "sinon";

const { assert } = chai;

const fetcherUrl = "/en-us/semantic-fields/semanticfield/";

describe("CombinatorView", () => {
  let view = null;
  let server;
  let renderDiv;
  const firstUrl = urls.detailURLFromId("2234");
  const secondUrl = urls.detailURLFromId("225241");
  let firstField;
  let secondField;
  let breaker;
  // We want to be able to just modify ``keep`` in tests, so.
  // eslint-disable-next-line prefer-const
  let keep = false;
  const verboseServer = false;


  before(() => {
    fixture.setBase(
      "karma_tests/lib/btw/semantic_field_editor/views/navigators");

    const json = fixture.load("navigator_test_fixture.json");
    firstField = json[urls.queryURLFromDetailURL(firstUrl)];
    secondField = json[urls.queryURLFromDetailURL(secondUrl)];

    breaker = new BoneBreaker(Bb, Mn);

    // Make all animations be instantaneous so that we don't spend
    // seconds waiting for them to happen.
    velocity.mock = true;
    server = new TestServer({
      fixture: json,
      verboseServer,
    });
  });

  after(() => {
    breaker.uninstall();
    server.restore();
    velocity.mock = false;
  });

  beforeEach(() => {
    renderDiv = document.createElement("div");
    document.body.appendChild(renderDiv);
    if (view !== null) {
      throw new Error("overwriting view!");
    }
    const fetcher = new SFFetcher(fetcherUrl, undefined);
    view = new CombinatorView({ fetcher });
    view.setElement(renderDiv);
    view.render();
  });

  afterEach(() => {
    breaker.neutralize();
    if (!keep) {
      if (view) {
        view.destroy();
        view = null;
      }
      if (renderDiv && renderDiv.parentNode) {
        renderDiv.parentNode.removeChild(renderDiv);
      }
    }
  });

  it("starts with empty element collections", () => {
    assert.equal(view.elementsCollection.length, 0);
    assert.equal(view.resultCollection.length, 0);
    return Promise.resolve();
  });

  function addAndWait(field) {
    return waitForEventOn(
      view.resultCollection, "reset", () => view.addSF(field));
  }

  function assertResults(...fields) {
    const results = view.resultCollection;
    if (fields.length === 0) {
      assert.equal(results.length, 0);
      return;
    }

    const elements = view.elementsCollection;
    assert.equal(results.length, 1);
    if (fields.length === 1) {
      // There's nothing combined so the paths should be equal.
      assert.equal(fields[0].path, results.at(0).get("path"));
    }
    else if (fields.length === 2) {
      const combined =
              `${elements.at(0).get("path")}@${elements.at(1).get("path")}`;
      assert.equal(results.at(0).get("path"), combined);
    }
    else {
      throw new Error("unexpected number of fields");
    }
  }

  function addFieldAssertResults(field, results) {
    return addAndWait(field).then(() => assertResults(...results));
  }

  describe("#addSF", () => {
    it("adds a semantic field to the two collections",
       () => addAndWait(firstField).then(
         () => assert.equal(view.elementsCollection.length, 1)));

    it("can add more than one field to the elements collection", () => {
      view.addSF(firstField);
      view.addSF(secondField);
      assert.equal(view.elementsCollection.length, 2);
      return Promise.resolve();
    });

    it("cannot add more than one field to the results collection",
       () => addAndWait(firstField).then(() => {
         assert.equal(view.resultCollection.length, 1);
         return addAndWait(secondField)
           .then(() => assert.equal(view.resultCollection.length, 1));
       }));
  });

  it("should have the add button disabled when the result collection is empty",
     () => Promise.try(() => {
       const addButton = view.resultView.ui.addButton[0];
       // Starts disabled.
       assert.isTrue(addButton.disabled);
       const spy = sinon.spy();
       addButton.addEventListener("click", spy);
       addButton.click();
       assert.equal(spy.callCount, 0);
       // Adding an element enables the button.
       return addAndWait(firstField).then(() => {
         // We only check the button's status.
         assert.isFalse(addButton.disabled);

         // Returning to length 0 disables the button.
         view.elementsCollection.reset();
         assert.isTrue(addButton.disabled);
         addButton.click();
         assert.equal(spy.callCount, 0);
       });
     }));

  describe("should update the result", () => {
    it("when an field is added to the elements to combine", () => {
      assertResults();
      return addFieldAssertResults(firstField, [firstField])
        .then(() => addFieldAssertResults(secondField,
                                          [firstField, secondField]));
    });

    it("when all fields are removed from the elements collection", () => {
      const results = view.resultCollection;
      assertResults();
      return addFieldAssertResults(firstField, [firstField])
        .then(() => waitForEventOn(
          results, "reset",
          () => view.elementsView.el.querySelector(".delete-button").click()))
      // Results becomes empty again.
        .then(() => assertResults());
    });

    it("when a field is removed from the elements collection", () => {
      const results = view.resultCollection;
      assertResults();
      return addAndWait(firstField)
        .then(() => addFieldAssertResults(secondField,
                                          [firstField, secondField]))
        .then(() => waitForEventOn(
          results, "reset",
          () => view.elementsView.el.querySelector(".delete-button").click()))
        .then(() => assertResults(secondField));
    });
  });

  it("should not show a delete button in the results",
     () => addFieldAssertResults(firstField, [firstField]).then(
       () => assert.isUndefined(
         view.resultView.el.getElementsByClassName("delete-button")[0])));

  describe("emits a sf:add event on the global channel", () => {
    it("with the view and model when the add button is clicked",
       () => addAndWait(firstField)
       .then(() => doAndWaitForRadio(
         view, "sf:add",
         () => view.resultView.ui.addButton.click()))
       .spread((eventView, model) => {
         assert.equal(model.get("path"),
                      view.elementsCollection.at(0).get("path"));
       }));
  });
});
