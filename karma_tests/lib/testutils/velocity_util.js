/* global chai */
import $ from "jquery";
const assert = chai.assert;

export function wasAnimated(el) {
  return !!$.data(el, "velocity");
}

export function assertAnimated(el, desc) {
  assert.isTrue(wasAnimated(el), `${desc} should have been animated`);
}

export function clearAnimationInfo(el) {
  $.removeData(el, "velocity");
}
