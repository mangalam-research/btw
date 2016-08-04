/* global chai */
import Bb from "backbone";
import Promise from "bluebird";
const assert = chai.assert;

export class BoneBreaker {
  constructor(Bb, Mn, options) { // eslint-disable-line no-shadow
    this.Bb = Bb;
    this.Mn = Mn;
    options = options || {};
    this.options = options;

    const origModelInit = this.origModelInit = Bb.Model.prototype.initialize;

    const capturedModels = this.capturedModels = [];
    this.modelInit = Bb.Model.prototype.initialize = function capture() {
      capturedModels.push(this);
      return origModelInit.apply(this, arguments);
    };

    const origCollectionInit = this.origCollectionInit =
            Bb.Collection.prototype.initialize;

    const capturedCollections = this.capturedCollections = [];
    this.collectionInit = Bb.Collection.prototype.initialize =
      function capture() {
        capturedCollections.push(this);
        return origCollectionInit.apply(this, arguments);
      };

    if (options.traceViewDestroy) {
      const origViewDestroy = this.origViewDestroy = Mn.View.prototype.destroy;
      this.viewDestroy = Mn.View.prototype.destroy = function destroy() {
        console.log("DESTROYING VIEW:", this);
        return origViewDestroy.apply(this, arguments);
      };
    }
  }

  neutralize() {
    this.capturedModels.forEach((x) => {
      x.sync = function sync() {
        return new XMLHttpRequest();
      };
      x.parse = function parse() {
        return this.attributes;
      };
      x.set = function set() {};
    });

    this.capturedModels = [];

    this.capturedCollections.forEach((x) => {
      x.sync = function sync() {
        return new XMLHttpRequest();
      };
      x.set = function set() {};
      x.parse = function parse() {
        return [];
      };
    });

    this.capturedCollections = [];
  }

  uninstall() {
    // eslint-disable-next-line no-shadow
    const Bb = this.Bb;
    const Mn = this.Mn;

    if (Bb.Collection.prototype.initialize !== this.collectionInit) {
      throw new Error("Backbone.Collection.prototype.initialize has been " +
                      "clobbered; cannot uninstall");
    }

    if (Bb.Model.prototype.initialize !== this.modelInit) {
      throw new Error("Backbone.Model.prototype.initialize has been " +
                      "clobbered; cannot uninstall");
    }

    Bb.Model.prototype.initialize = this.modelInit;
    Bb.Collection.prototype.initialize = this.collectionInit;

    if (this.origViewDestroy) {
      if (Mn.View.prototype.destroy !== this.viewDestroy) {
        throw new Error("Marionette.View.prototype.destroy has been " +
                        "clobbered; cannot uninstall");
      }

      Mn.View.prototype.destroy = this.origViewDestroy;
    }
  }

}

export function assertCollectionViewLength(view, length) {
  assert.equal(view.collection.length, length);
  assert.equal(view.children.length, length);
}

export function isInViewText(view, text) {
  return view.el.textContent.indexOf(text) !== -1;
}

export function makeFakeApplication() {
  return {
    channels: {
      global: "__test:global",
    },
  };
}

export function waitForEventOn(item, eventName, fn) {
  return new Promise((resolve) => {
    item.once(eventName, (...rest) => {
      resolve(rest);
    });
    if (fn) {
      fn();
    }
  });
}

export function doAndWaitForRadio(view, eventName, fn) {
  const fakeApp = makeFakeApplication();
  view._cachedApplication = fakeApp;
  if (view.application !== view._cachedApplication) {
    throw new Error("your view does not seem to have the communication " +
                    "getters and setters");
  }
  const global = Bb.Radio.channel(fakeApp.channels.global);
  return new Promise((resolve) => {
    global.once(eventName, (...args) => resolve(args));
    fn();
  });
}
