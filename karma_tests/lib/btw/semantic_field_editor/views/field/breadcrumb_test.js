/* global chai describe afterEach beforeEach before after it fixture */
/* eslint-env module */
import velocity from "velocity";
import Promise from "bluebird";
import BreadcrumbView from "btw/semantic_field_editor/views/field/breadcrumb";
import Field from "btw/semantic_field_editor/models/field";
import { BoneBreaker, isInViewText, makeFakeApplication }
from "testutils/backbone";
import { waitFor } from "testutils/util";
import * as urls from "testutils/urls";
import Bb from "backbone";
import Mn from "marionette";
import _ from "lodash";

const assert = chai.assert;

describe("BreadcrumbView", () => {
  let view;
  let renderDiv;
  const firstUrl = urls.detailURLFromId("2234");
  let firstField;
  let breaker;
  // We want to be able to just modify ``keep`` in tests, so.
  // eslint-disable-next-line prefer-const
  let keep = false;

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
  });

  after(() => {
    breaker.uninstall();
    velocity.mock = false;
  });

  function makeView(options) {
    options = options || {};
    // We purposely leak everything.
    renderDiv = document.createElement("div");
    document.body.appendChild(renderDiv);

    options = _.extend({
      model: new Field(firstField),
    }, options);

    view = new BreadcrumbView(options);
    view.setElement(renderDiv);
    view.render();
    return waitFor(() => isInViewText(view, firstField.heading));
  }

  afterEach(() => {
    breaker.neutralize();
    if (!keep) {
      view.destroy();
      if (renderDiv && renderDiv.parentNode) {
        renderDiv.parentNode.removeChild(renderDiv);
      }
    }
  });

  function checkParents(field) {
    const breadcrumbLinks =
            _.reverse(
              [...view.el.querySelectorAll(".sf-breadcrumbs .sf-link")]);
    let parent = field;
    let first = true;
    assert.isTrue(breadcrumbLinks.length > 1);
    for (const link of breadcrumbLinks) {
      assert.equal(link.href, parent.url);
      assert.equal(link.textContent,
                   first ? `${parent.heading} (${parent.verbose_pos})` :
                   parent.heading);

      if (parent.parent) {
        const text = link.previousSibling.textContent.trim();
        assert.equal(text, parent.is_subcat ? "::" : ">");
      }

      parent = parent.parent;
      first = false;
    }
    return Promise.resolve();
  }


  function checkOtherPOS() {
    const links = [...view.el.querySelectorAll(".sf-other-pos .sf-link")];
    assert.isTrue(links.length > 1);
    for (const related of firstField.related_by_pos) {
      const link = links.shift();
      assert.equal(link.href, related.url);
      assert.equal(link.textContent,
                   `${related.heading} (${related.verbose_pos})`);
    }
    assert.isTrue(links.length === 0);
    return Promise.resolve();
  }

  describe("with all details on", () => {
    beforeEach(() => makeView({ details: "all" }));

    it("displays all parents", () => checkParents(firstField));

    it("displays the field path", () => {
      assert.isTrue(isInViewText(view, firstField.path));
      return Promise.resolve();
    });

    it("displays other pats of speech", () => checkOtherPOS());

    it("displays all children", () => {
      const links = [...view.el.querySelectorAll(".sf-children .sf-link")];
      assert.isTrue(links.length > 1);
      for (const child of firstField.children) {
        const link = links.shift();
        assert.equal(link.href, child.url);
        assert.equal(link.textContent, child.heading);
      }
      assert.isTrue(links.length === 0);
      return Promise.resolve();
    });

    it("displays all lexemes", () => {
      const labels = [...view.el.querySelectorAll(".sf-lexemes .label")];
      assert.isTrue(labels.length > 1);
      for (const lexeme of firstField.lexemes) {
        const label = labels.shift();
        assert.equal(label.textContent, `${lexeme.word} ${lexeme.fulldate}`);
      }
      assert.isTrue(labels.length === 0);
      return Promise.resolve();
    });
  });

  describe("with the default level of details on", () => {
    beforeEach(() => makeView());

    it("displays all parents", () => checkParents(firstField));

    it("displays other parts of speech", () => checkOtherPOS());

    it("does not display the field path", () => {
      assert.isFalse(isInViewText(view, firstField.path));
      return Promise.resolve();
    });

    it("does not display children", () => {
      const links = view.el.querySelector(".sf-children");
      assert.isNull(links);
      return Promise.resolve();
    });

    it("does not display lexemes", () => {
      const labels = view.el.querySelector(".sf-lexemes");
      assert.isNull(labels);
      return Promise.resolve();
    });
  });

  describe("", () => {
    beforeEach(() => makeView());
    it("puts a proper separator for subcats", () => {
      const field = _.extend({}, firstField, {
        is_subcat: true,
      });
      return makeView({ model: new Field(field) })
        .then(checkParents.bind(undefined, field));
    });
  });

  describe("", () => {
    beforeEach(() => makeView());

    it("generates sf:selected when a link is clicked", () => {
      const link = view.el.querySelector(".sf-link");
      const p = new Promise(resolve => {
        view.once("sf:selected", () => resolve(1));
      });
      link.click();
      return p;
    });
  });

  describe("without ``canBeAdded`` truthy", () => {
    beforeEach(() => makeView());

    it("does not show any buttons for adding", () => {
      assert.isUndefined(view.ui.addButton[0]);
      assert.isUndefined(view.ui.combineButton[0]);
      return Promise.resolve();
    });
  });

  describe("with ``canBeAdded`` truthy", () => {
    beforeEach(() => makeView({ canBeAdded: true }));

    function clickAndWait(eventName, $uiElement) {
      const fakeApp = makeFakeApplication();
      view._cachedApplication = fakeApp;
      const global = Bb.Radio.channel(fakeApp.channels.global);
      return new Promise((resolve) => {
        global.once(eventName,
                    (eventView, model) => resolve([eventView, model]));
        $uiElement.click();
      }).spread((eventView, model) => {
        assert.equal(view, view);
        assert.equal(model, view.model);
      });
    }

    describe("emits a sf:add event on the global channel", () => {
      it("with the view and model when the add button is clicked",
         () => clickAndWait("sf:add", view.ui.addButton));
    });

    describe("emits a sf:combine event on the global channel", () => {
      it("with the view and model when the combine button is clicked",
         () => clickAndWait("sf:combine", view.ui.combineButton));
    });
  });
});
