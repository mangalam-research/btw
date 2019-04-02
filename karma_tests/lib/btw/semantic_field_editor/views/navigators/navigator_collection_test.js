/* global chai describe afterEach beforeEach before after it */
/* eslint-env module */
import sinon from "sinon";
import velocity from "velocity";
import Promise from "bluebird";
import { assertAnimated, clearAnimationInfo } from "testutils/velocity_util";
import { BoneBreaker, assertCollectionViewLength } from "testutils/backbone";
// eslint-disable-next-line import/no-extraneous-dependencies
import Bb from "backbone";
import NavigatorCollectionView
from "btw/semantic_field_editor/views/navigators/navigator_collection";

const { assert } = chai;

function promiseFromBbEvent(item, event) {
  return new Promise((resolve) => {
    item.once(event, (...args) => resolve(args.slice()));
  });
}

describe("NavigatorCollectionView", () => {
  let view;
  let server;
  let renderDiv;
  let breaker;

  function setServer() {
    server = sinon.fakeServer.create();
    server.respondWith("GET", /^\/one\?.*/,
                       [200, { "Content-Type": "application/json" },
                        JSON.stringify({ heading: "one" })]);
    server.respondWith("GET", /^\/two\?.*/,
                       [200, { "Content-Type": "application/json" },
                        JSON.stringify({ heading: "two" })]);

    server.autoRespond = true;
    server.autoRespondAfter = 1;
  }

  before(() => {
    // Make all animations be instantaneous so that we don't spend
    // seconds waiting for them to happen.
    velocity.mock = true;

    breaker = new BoneBreaker(Bb);

    setServer();
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

    view = new NavigatorCollectionView();
    view.setElement(renderDiv);
    view.render();
  });

  afterEach(() => {
    breaker.neutralize();
    // $(renderDiv, "*").velocity("stop", true);
    view.destroy();
    // Yep, we add back bunk data to prevent a failure.
    // $(renderDiv, "velocity-animating").data("velocity", {});
    if (renderDiv && renderDiv.parentNode) {
      renderDiv.parentNode.removeChild(renderDiv);
    }
  });

  it("constructs a view with an empty collection", () => {
    assertCollectionViewLength(view, 0);
    return Promise.resolve(1);
  });

  describe("#closeAllNavigators", () => {
    it("works when the collection is empty",
       () => view.closeAllNavigators()
       .then(() => assertCollectionViewLength(view, 0)));

    it("empties the collection",
       () => Promise.each(["/one", "/two"], x => view.openUrl(x))
       .then(() => {
         assertCollectionViewLength(view, 2);
         return view.closeAllNavigators();
       })
       .then(() => assertCollectionViewLength(view, 0)));

    it("can be called more than once",
       () => Promise.each(["/one", "/two"], x => view.openUrl(x))
        .then(() => {
          assertCollectionViewLength(view, 2);
          return view.closeAllNavigators();
        })
        .then(() => {
          assertCollectionViewLength(view, 0);
          return view.closeAllNavigators();
        })
        .then(() => assertCollectionViewLength(view, 0)));

    it("should return a promise that resolves to the object " +
       "on which it was called",
       () => assert.eventually.equal(
         Promise.each(["/one", "/two"], x => view.openUrl(x))
           .then(() => view.closeAllNavigators()), view));
  });

  describe("#openUrl", () => {
    it("should add a new Navigator to the collection", () => {
      assertCollectionViewLength(view, 0);
      return view.openUrl("/one").then(() => {
        assertCollectionViewLength(view, 1);
        return view.closeAllNavigators();
      });
    });

    it("should animate the new Navigator added",
       () => view.openUrl("/one").then(
         nav => assertAnimated(nav.el, "the new Navigator")));

    it("should add a new Navigator when the URL is not already shown", () => {
      assertCollectionViewLength(view, 0);
      return view.openUrl("/one").then(() => {
        assertCollectionViewLength(view, 1);
        return view.openUrl("/two");
      }).then(() => assertCollectionViewLength(view, 2));
    });

    it("should not add a new Navigator when the URL is already shown", () => {
      assertCollectionViewLength(view, 0);
      return view.openUrl("/one").then(() => {
        assertCollectionViewLength(view, 1);
        return view.openUrl("/one");
      }).then(() => assertCollectionViewLength(view, 1));
    });

    it("should scroll into view the Navigator that already displays the URL",
       () => {
         assertCollectionViewLength(view, 0);
         return view.openUrl("/one").then((nav) => {
           assertCollectionViewLength(view, 1);
           const mocked = sinon.mock(nav.el);
           mocked.expects("scrollIntoView").once();
           return view.openUrl("/one").then(() => {
             assertCollectionViewLength(view, 1);
             mocked.verify();
           }).finally(() => mocked.restore());
         });
       });

    it("should animate the Navigator that already shows the URL",
       () => view.openUrl("/one").then((nav) => {
         clearAnimationInfo(nav.el);
         return view.openUrl("/one");
       }).then(nav => assertAnimated(nav.el, "the Navigator")));

    it("should create a Navigator whose url is the one passed",
       () => assert.eventually.equal(
         view.openUrl("/one").get("model").call("getCurrentUrl"),
         "/one",
         "the url of the Navigator should be the one passed"));

    it("should display the URL's content", () => {
      assert.isTrue(view.el.textContent.indexOf("one") === -1);
      return view.openUrl("/one").then(
        () => assert.isTrue(view.el.textContent.indexOf("one") !== -1));
    });
  });

  describe("#closeNavigator()", () => {
    let first;

    beforeEach(
      () => view.openUrl("/one").then((nav) => {
        first = nav;
      }));

    it("should return a promise that resolves to the closed Navigator",
       () => assert.eventually.equal(
         view.closeNavigator(first), first,
         "the resolved value should be the Navigator being closed"));

    it("should be callable multiple times",
       () => assert.eventually.equal(
         view.closeNavigator(first).then(() => view.closeNavigator(first)),
         first, "the resolved value should be the Navigator being closed"));

    it("should remove the Navigator from the DOM", () => {
      assert.isNotNull(first.el.parentNode, "the view should be in the DOM");
      return assert.eventually.isNull(
        view.closeNavigator(first).get("el").get("parentNode"),
        "the view should no longer be in the DOM");
    });

    it("should trigger ``dom:removed`` on the Navigator", () => {
      const p = promiseFromBbEvent(first, "dom:removed");
      return Promise.all([p, view.closeNavigator(first)]);
    });
  });

  describe("clicking the close navigator button should", () => {
    it("remove the navigator",
       () => view.openUrl("/one").then(() => {
         assertCollectionViewLength(view, 1);
         const firstNavigatorView = view.children.findByIndex(0);
         firstNavigatorView.ui.closeNavigator.click();
         assertCollectionViewLength(view, 0);
         // Ignore the promise that was created in the click handler.
         return null;
       }));

    it("calls #closeNavigator with the closed navigator",
       () => view.openUrl("/one").then(() => {
         assertCollectionViewLength(view, 1);
         const firstNavigatorView = view.children.findByIndex(0);
         const mocked = sinon.mock(view);
         try {
           mocked.expects("closeNavigator").once().withArgs(firstNavigatorView);
           firstNavigatorView.ui.closeNavigator.click();
           mocked.verify();
         }
         finally {
           mocked.restore();
         }
         // Ignore the promise that was created in the click handler.
         return null;
       }));
  });

  describe("clicking the close all navigators button should", () => {
    it("remove all navigator",
       () => Promise.each(["/one", "/two"], view.openUrl.bind(view))
       .then(() => {
         assertCollectionViewLength(view, 2);
         const firstNavigatorView = view.children.findByIndex(0);
         firstNavigatorView.ui.closeAllNavigators.click();
         assertCollectionViewLength(view, 0);
         // Ignore the promise that was created in the click handler.
         return null;
       }));

    it("call #closeAllNavigators",
       () => Promise.each(["/one", "/two"], view.openUrl.bind(view)).then(() => {
         assertCollectionViewLength(view, 2);
         const firstNavigatorView = view.children.findByIndex(0);
         const mocked = sinon.mock(view);
         try {
           mocked.expects("closeAllNavigators").once();
           firstNavigatorView.ui.closeAllNavigators.click();
           mocked.verify();
         }
         finally {
           mocked.restore();
         }
         // Ignore the promise that was created in the click handler.
         return null;
       }));
  });
});
