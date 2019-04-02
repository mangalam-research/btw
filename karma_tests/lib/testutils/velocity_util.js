/* global chai */
// eslint-disable-next-line import/no-extraneous-dependencies
import $ from "jquery";

const { assert } = chai;

export function wasAnimated(el) {
  return !!$.data(el, "velocity");
}

export function assertAnimated(el, desc) {
  assert.isTrue(wasAnimated(el), `${desc} should have been animated`);
}

export function clearAnimationInfo(el) {
  $.removeData(el, "velocity");
}
