/* global chai describe it */
/* eslint-env module */

import ChosenFieldCollection
from "btw/semantic_field_editor/collections/chosen_field";
import Field from "btw/semantic_field_editor/models/field";

const assert = chai.assert;

describe("ChosenFieldCollection", () => {
  it("does not allow duplicate fields", () => {
    const col = new ChosenFieldCollection();
    const f1 = new Field({ url: "1", heading: "Foo" });
    const f2 = new Field({ url: "2", heading: "bar" });
    const f3 = new Field({ url: "1", heading: "bwip" });
    col.add(f1);
    assert.equal(col.length, 1);
    col.add(f2);
    assert.equal(col.length, 2);
    col.add(f3);
    assert.equal(col.length, 2);
    return Promise.resolve();
  });
});
