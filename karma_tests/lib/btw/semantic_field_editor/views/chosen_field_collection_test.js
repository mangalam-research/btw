/* global chai describe afterEach beforeEach before after it */
/* eslint-env module */
import velocity from "velocity";
import Promise from "bluebird";
import ChosenFieldCollectionView
from "btw/semantic_field_editor/views/chosen_field_collection";
import Field from "btw/semantic_field_editor/models/field";
import { SFFetcher } from "btw/semantic-field-fetcher";
import { BoneBreaker, isInViewText } from "testutils/backbone";
import { waitFor } from "testutils/util";
import { Server } from "testutils/server";
// eslint-disable-next-line import/no-extraneous-dependencies
import Bb from "backbone";
import Mn from "marionette";
import URI from "urijs/URI";
// eslint-disable-next-line import/no-extraneous-dependencies
import _ from "lodash";

const { assert } = chai;

const ChosenFieldCollection = Bb.Collection.extend({
  Model: Field,
});

const fetcherUrl = "/en-us/semantic-fields/semanticfield/";
const fetcherUrlRe = /^\/en-us\/semantic-fields\/semanticfield\/(.*)$/;

class TestServer extends Server {
  constructor(options) {
    super(_.omit(options, ["fetcherUrl"]));
    this.fetcherUrl = options.fetcherUrl;
  }

  setChangeRecords(changeRecords) {
    this.changeRecords = changeRecords;
  }

  respond(request) {
    super.respond(request);
    // Already responded.
    if (request.status === 200) {
      return;
    }

    // No match.
    if (request.method === "GET" && this.fetcherUrl.test(request.url)) {
      const query = new URI(request.url).query(true);
      const paths = query.paths.split(";");
      const response = paths.map(
        path => ({
          path,
          heading: "semantic field foo",
          heading_for_display: "semantic field foo",
          parent: undefined,
          changerecords: this.changeRecords,
        }));
      request.respond(200, { "Content-Type": "application/json" },
                      JSON.stringify(response));
    }
  }
}

describe("ChosenFieldCollectionView", () => {
  let view = null;
  let server;
  let renderDiv;
  let breaker;
  // We want to be able to just modify ``keep`` in tests, so.
  // eslint-disable-next-line prefer-const
  let keep = false;
  const verboseServer = false;


  before(() => {
    breaker = new BoneBreaker(Bb, Mn);

    // Make all animations be instantaneous so that we don't spend
    // seconds waiting for them to happen.
    velocity.mock = true;
    server = new TestServer({
      fetcherUrl: fetcherUrlRe,
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

  function makeView(options) {
    const newView = new ChosenFieldCollectionView(options);
    newView.setElement(renderDiv);
    newView.render();
    newView.triggerMethod("show");
    return newView;
  }

  function makeAndWaitForRender(paths, canDelete = true) {
    if (view !== null) {
      throw new Error("overwriting view!");
    }
    const fetcher = new SFFetcher(fetcherUrl, undefined);
    return fetcher.fetch(paths).then((resolved) => {
      // Deliberate leak to global space!
      view = makeView({
        collection: new ChosenFieldCollection(_.values(resolved)),
        fetcher,
        canDelete,
      });

      return Promise.map(paths, path => waitFor(() => isInViewText(view, path)))
        .return(view);
    });
  }

  it("shows the elements passed to it at initialization",
     () => makeAndWaitForRender(["01.01.06.01aj", "01.01.06.01.01aj"]));

  it("deletes a model from the collection on sf:delete from a child",
     () => makeAndWaitForRender(["01.01.06.01aj", "01.01.06.01.01aj"])
    .then(() => {
      assert.equal(view.collection.length, 2);
      const model = view.collection.at(0);
      const childView = view.getChildView("body");
      const modelView = childView.children.findByModel(model);
      modelView.triggerMethod("sf:delete", model);
      assert.equal(view.collection.length, 1);
      assert.isUndefined(view.collection.get(model));
    }));

  it("deletes from the collection the model whose delete button is pressed",
     () => makeAndWaitForRender(["01.01.06.01aj", "01.01.06.01.01aj"])
    .then(() => {
      assert.equal(view.collection.length, 2);
      const model = view.collection.at(0);
      const childView = view.getChildView("body");
      const modelView = childView.children.findByModel(model);
      modelView.ui.deleteButton.click();
      assert.equal(view.collection.length, 1);
      assert.isUndefined(view.collection.get(model));
    }));

  it("does not show a delete button if not requested",
     () => makeAndWaitForRender(["01.01.06.01aj", "01.01.06.01.01aj"], false)
    .then(() => {
      const model = view.collection.at(0);
      const childView = view.getChildView("body");
      const modelView = childView.children.findByModel(model);
      assert.isUndefined(modelView.ui.deleteButton[0]);
    }));

  it("reorders a model when it is dragged and dropped",
     () => makeAndWaitForRender(["01.01.06.01aj", "01.01.06.01.01aj"])
     .then(() => {
       const childView = view.getChildView("body");
       const originalOrder = childView.collection.models.slice();

       const sourceModelView = childView.children.findByIndex(0);
       let ev = new MouseEvent("mousedown", {
         which: 1,
         bubbles: true,
       });
       sourceModelView.el.dispatchEvent(ev);

       const destinationModelView = childView.children.findByIndex(1);
       const destinationRect = destinationModelView.el.getBoundingClientRect();
       const clientX = destinationRect.right - 10;
       const clientY = destinationRect.bottom - 10;

       ev = new MouseEvent("mousemove", {
         bubbles: true,
         clientX,
         clientY,
       });
       destinationModelView.el.dispatchEvent(ev);

       ev = new MouseEvent("mousemove", {
         bubbles: true,
         clientX: clientX + 1,
         clientY: clientY + 1,
       });
       destinationModelView.el.dispatchEvent(ev);

       ev = new MouseEvent("mouseup", {
         which: 1,
         bubbles: true,
         clientX,
         clientY,
       });
       sourceModelView.el.dispatchEvent(ev);

       // We've effectively reversed the elements.
       originalOrder.reverse();
       assert.sameMembers(childView.collection.models, originalOrder);
     }));
});
