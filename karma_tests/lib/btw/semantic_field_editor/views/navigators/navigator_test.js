/* global chai describe afterEach beforeEach before after it fixture */
/* eslint-env module */
import velocity from "velocity";
import Promise from "bluebird";
import NavigatorView from "btw/semantic_field_editor/views/navigators/navigator";
import Navigator from "btw/semantic_field_editor/models/navigator";
import { BoneBreaker, isInViewText } from "testutils/backbone";
import Server from "testutils/server";
import * as urls from "testutils/urls";
import { wasAnimated, clearAnimationInfo } from "testutils/velocity_util";
import Bb from "backbone";
import Mn from "marionette";

const assert = chai.assert;

function assertNumberOfPages(view, length) {
  assert.equal(view.model.get("pages").length, length);
}

function waitForView(view, fn) {
  return Promise.try(() => {
    if (fn()) {
      return 1;
    }

    // Wait for the next refresh.
    return view.makeDOMDisplayedPromise().then(waitForView.bind(undefined,
                                                                view, fn));
  });
}

describe("NavigatorView", () => {
  let view;
  let server;
  let renderDiv;
  const firstUrl = urls.detailURLFromId("2234");
  const secondUrl = urls.detailURLFromId("225241");
  const thirdUrl = urls.detailURLFromId("225242");
  let firstField;
  let secondField;
  let thirdField;
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
    thirdField = json[urls.queryURLFromDetailURL(thirdUrl)];

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

  beforeEach(() => {
    renderDiv = document.createElement("div");
    document.body.appendChild(renderDiv);
    view = new NavigatorView({
      model: new Navigator(firstUrl),
    });
    view.setElement(renderDiv);
    view.render();
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

  it("constructs a view that has a model with a single page", () => {
    assertNumberOfPages(view, 1);
    return Promise.resolve(1);
  });

  describe("#_showSF", () => {
    it("adds a new page", () => {
      view._showSF(undefined, secondUrl);
      assertNumberOfPages(view, 2);
      return Promise.resolve(1);
    });

    it("scraps the history tail", () => {
      view._showSF(undefined, secondUrl);
      view._showSF(undefined, thirdUrl);
      assertNumberOfPages(view, 3);
      view.model.moveToFirstPage();
      view._showSF(undefined, thirdUrl);
      assertNumberOfPages(view, 2);
      assert.equal(view.model.get("pages").at(0).url, firstUrl);
      assert.equal(view.model.get("pages").at(1).url, thirdUrl);
      return Promise.resolve(1);
    });

    it("is a no-op if the url is the same as the one already displayed", () => {
      view._showSF(undefined, firstUrl);
      assertNumberOfPages(view, 1);
      return Promise.resolve(1);
    });

    it("causes a dom:display event", () => {
      const p = view.makeDOMDisplayedPromise();
      view._showSF(undefined, secondUrl);
      return p;
    });

    it("shows the url contents", () => {
      assert.isFalse(isInViewText(view, secondField.path));
      view._showSF(undefined, secondUrl);

      return waitForView(view, () => isInViewText(view, secondField.path));
    });

    it("animates the content", () => {
      const el = view.el;
      const pagedContent = view.ui.pagedContent[0];
      // We wait for the initial animation to be done.
      return waitForView(view, () => wasAnimated(el)).then(() => {
        assert.isTrue(!wasAnimated(pagedContent));
        view._showSF(undefined, secondUrl);
        // When a subsequent page is added, the animation is done on
        // the paged content rather than the root element.
        return waitForView(view, () => wasAnimated(pagedContent));
      });
    });
  });

  describe("clicking to show", () => {
    describe("the first page should", () => {
      function moveToFirst() {
        view._showSF(undefined, secondUrl);
        view._showSF(undefined, thirdUrl);
        const pagedContent = view.ui.pagedContent[0];
        return waitForView(view, () => isInViewText(view, thirdField.path))
          .then(() => {
            // One of the tests needs this. It does not harm other tests.
            // It was animated from previous _showSF calls.
            clearAnimationInfo(pagedContent);
            assert.isFalse(isInViewText(view, firstField.path));
            view.ui.first.click();
            return null;
          });
      }
      it("show the first page, when not already on it", () =>
         moveToFirst().then(
           () => waitForView(view, () => isInViewText(view, firstField.path))));

      it("animate the content, when it can move", () =>
         moveToFirst().then(
           () => waitForView(view, () => wasAnimated(view.ui.pagedContent[0]))));

      it("be a noop when already on it", () =>
         waitForView(view, () => isInViewText(view, firstField.path))
         .then(() => {
           view.ui.first.click();
           return waitForView(view, () => isInViewText(view, firstField.path));
         })
         .then(() => {
           assert.isFalse(wasAnimated(view.ui.pagedContent[0]));
         }));
    });

    describe("the previous page should", () => {
      function moveToPrevious() {
        view._showSF(undefined, secondUrl);
        view._showSF(undefined, thirdUrl);
        return waitForView(view, () => isInViewText(view, thirdField.path))
          .then(() => {
            // One of the tests needs this. It does not harm other tests.
            // It was animated from previous _showSF calls.
            clearAnimationInfo(view.ui.pagedContent[0]);
            assert.isFalse(isInViewText(view, secondField.path));
            view.ui.previous.click();
            return null;
          });
      }

      it("show the previous page, when possible", () =>
         moveToPrevious().then(
           () => waitForView(view, () => isInViewText(view, secondField.path))));

      it("animate the content, when it can move", () =>
         moveToPrevious().then(
           () => waitForView(view, () => wasAnimated(view.ui.pagedContent[0]))));

      it("be a noop if we are already on the first page", () =>
         waitForView(view, () => isInViewText(view, firstField.path))
         .then(() => {
           view.ui.previous.click();
           return waitForView(view, () => isInViewText(view, firstField.path));
         })
         .then(() => {
           assert.isFalse(wasAnimated(view.ui.pagedContent[0]));
         }));
    });


    describe("the last page should", () => {
      function moveToLast() {
        view._showSF(undefined, secondUrl);
        view._showSF(undefined, thirdUrl);
        return waitForView(view, () => isInViewText(view, thirdField.path))
          .then(() => {
            assert.isFalse(isInViewText(view, firstField.path));
            view.ui.first.click();
            return waitForView(view, () => isInViewText(view, firstField.path))
              .then(() => {
                // One of the tests needs this. It does not harm other tests.
                // It was animated from previous navigation.
                clearAnimationInfo(view.ui.pagedContent[0]);
                view.ui.last.click();
                return null;
              });
          });
      }

      it("show the last page, when not already on it", () =>
        moveToLast().then(
          () => waitForView(view, () => isInViewText(view, thirdField.path))));

      it("animate the content, when it can move", () =>
        moveToLast().then(
          () => waitForView(view, () => wasAnimated(view.ui.pagedContent[0]))));

      it("be a noop, when already on it", () =>
         waitForView(view, () => isInViewText(view, firstField.path)).then(() => {
           view.ui.last.click();
           return waitForView(view, () => isInViewText(view, firstField.path));
         })
         .then(() => {
           assert.isFalse(wasAnimated(view.ui.pagedContent[0]));
         }));
    });

    describe("the next page should", () => {
      function moveToNext() {
        view._showSF(undefined, secondUrl);
        view._showSF(undefined, thirdUrl);
        return waitForView(view, () => isInViewText(view, thirdField.path))
          .then(() => {
            assert.isFalse(isInViewText(view, firstField.path));
            view.ui.first.click();
            return waitForView(view, () => isInViewText(view, firstField.path))
              .then(() => {
                // One of the tests needs this. It does not harm other tests.
                // It was animated from previous navigation.
                clearAnimationInfo(view.ui.pagedContent[0]);
                view.ui.next.click();
                return null;
              });
          });
      }

      it("show the next page, when possible", () =>
         moveToNext().then(
           () => waitForView(view,
                             () => isInViewText(view, secondField.path))));

      it("animate the content, when it can move", () =>
         moveToNext().then(
           () => waitForView(view,
                             () => wasAnimated(view.ui.pagedContent[0]))));

      it("be a noop if there is no next page", () =>
         waitForView(view, () => isInViewText(view, firstField.path))
         .then(() => {
           view.ui.next.click();
           return waitForView(view, () => isInViewText(view, firstField.path));
         })
         .then(() => {
           assert.isFalse(wasAnimated(view.ui.pagedContent[0]));
         }));
    });
  });

  it("clicking to close the navigator should emit navigator:close", () =>
     waitForView(view, () => isInViewText(view, firstField.path)).then(() => {
       const p = view.makeEventPromise("navigator:close");
       view.ui.closeNavigator.click();
       return p;
     }));

  it("clicking to close all navigators should emit navigator:closeAll", () =>
     waitForView(view, () => isInViewText(view, firstField.path)).then(() => {
       const p = view.makeEventPromise("navigator:closeAll");
       view.ui.closeAllNavigators.click();
       return p;
     }));

  it("clicking on a semantic field should show the field", () =>
     waitForView(view, () => isInViewText(view, firstField.path)).then(() => {
       const button = view.el.querySelector(`[href='${secondField.url}']`);
       button.click();
       return waitForView(view, () => isInViewText(view, secondField.path));
     }));
});
