define(function (require, exports, module) {
'use strict';

function IDManager(prefix) {
    this._ids = Object.create(null);
    this._prefix = prefix;
    this._next_number = 0;
}

IDManager.prototype.generate = function () {
    var ret;

    do {
        ret = this._prefix + this._next_number++;
    }
    while (this._ids[ret]);

    this._ids[ret] = true;
    return ret;
};

IDManager.prototype.seen = function (id, fail) {
    if (id.lastIndexOf(this._prefix, 0) !== 0)
        throw new Error("id with incorrect prefix: " + id);

    if (fail && this._ids[id])
        throw new Error("id already seen: " + id);

    this._ids[id] = true;
};

exports.IDManager = IDManager;

});
