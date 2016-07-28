/* global chai describe afterEach beforeEach before after it fixture */
/* eslint-env module */
import velocity from "velocity";
import Promise from "bluebird";
import InlineView from "btw/semantic_field_editor/views/field/inline";
import Field from "btw/semantic_field_editor/models/field";
import SFFetcher from "btw/semantic_field_fetcher";
import { BoneBreaker, isInViewText } from "testutils/backbone";
import { waitFor } from "testutils/util";
import Server from "testutils/server";
import * as urls from "testutils/urls";
import Bb from "backbone";
import Mn from "marionette";
import _ from "lodash";

const assert = chai.assert;

describe("InlineView", () => {
  let view;
  let server;
  let renderDiv;
  const firstUrl = urls.detailURLFromId("2234");
  let firstField;
  let breaker;
  // We want to be able to just modify ``keep`` in tests, so.
  // eslint-disable-next-line prefer-const
  let keep = false;
  const verboseServer = false;

  before(() => {
    // Yes, we use the navigators fixture.
    fixture.setBase(
      "karma_tests/lib/btw/semantic_field_editor/views/navigators");

    const json = fixture.load("navigator_test_fixture.json");
    firstField = json[urls.queryURLFromDetailURL(firstUrl)];

    breaker = new BoneBreaker(Bb, Mn);

    // Make all animations be instantaneous so that we don't spend
    // seconds waiting for them to happen.
    velocity.mock = true;
    server = new Server({
      fixture: json,
      verboseServer,
    });
  });

  after(() => {
    breaker.uninstall();
    server.restore();
    velocity.mock = false;
  });

  function makeAndRender(field, canDelete) {
    // Yes we leak into the upper scope.
    view = new InlineView({
      el: renderDiv,
      model: new Field(field),
      fetch: new SFFetcher(),
      canDelete,
    });
    view.render();
  }

  beforeEach(() => {
    renderDiv = document.createElement("div");
    document.body.appendChild(renderDiv);
  });

  afterEach(() => {
    breaker.neutralize();
    if (!keep) {
      view.destroy();
      if (renderDiv && renderDiv.parentNode) {
        renderDiv.parentNode.removeChild(renderDiv);
      }
    }
  });

  describe("", () => {
    // We create a fake field rather than add one to the fixture.
    const fakeField = _.extend({}, firstField, {
      heading: "fake heading",
      heading_for_display: "fake heading for display",
      is_subcat: true,
    });
    beforeEach(() => makeAndRender(fakeField, false));

    it("uses the heading for display", () =>
       waitFor(() => isInViewText(view, fakeField.heading_for_display)));
  });

  describe("with canDelete false", () => {
    beforeEach(() => makeAndRender(firstField, false));

    it("does not show a delete button", () =>
       waitFor(() => isInViewText(view, firstField.path)).then(() => {
         assert.isUndefined(view.ui.deleteButton[0]);
       }));

    it("shows a popover button", () =>
       waitFor(() => isInViewText(view, firstField.path)).then(() => {
         assert.isDefined(view.ui.popoverButton[0]);
       }));
  });

  describe("with canDelete true", () => {
    beforeEach(() => makeAndRender(firstField, true));

    it("does shows a delete button", () =>
       waitFor(() => isInViewText(view, firstField.path)).then(() => {
         assert.isDefined(view.ui.deleteButton[0]);
       }));

    it("shows a popover button", () =>
       waitFor(() => isInViewText(view, firstField.path)).then(() => {
         assert.isDefined(view.ui.popoverButton[0]);
       }));

    it("emits sf:delete with the model when the delete button is clicked", () =>
       waitFor(() => isInViewText(view, firstField.path)).then(() => {
         const p = new Promise(resolve => {
           view.once("sf:delete", (model) => {
             assert.equal(model, view.model);
             resolve(1);
           });
         });
         view.ui.deleteButton.click();
         return p;
       }));
  });
});
