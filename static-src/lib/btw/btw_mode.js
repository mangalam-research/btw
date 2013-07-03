define(function (require, exports, module) {
'use strict';

var util = require("wed/util");
var Mode = require("wed/modes/generic/generic").Mode;
var oop = require("wed/oop");
var BTWDecorator = require("./btw_decorator").BTWDecorator;
var transformation = require("wed/transformation");
var Toolbar = require("./btw_toolbar").Toolbar;
var rangy = require("rangy");
var btw_meta = require("./btw_meta");

var prefix_to_uri = {
    "btw": "http://mangalamresearch.org/ns/btw-storage",
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "": "http://www.tei-c.org/ns/1.0"
};

function BTWMode () {
    Mode.call(this, {meta: btw_meta});
    Object.keys(prefix_to_uri).forEach(function (k) {
        this._resolver.definePrefix(k, prefix_to_uri[k]);
    }.bind(this));
    this._meta = new btw_meta.Meta();
    this._toolbar = new Toolbar();
}

oop.inherit(BTWMode, Mode);

BTWMode.optionResolver = function (options, callback) {
    callback(options);
};


(function () {
    this.init = function (editor) {
        Mode.prototype.init.call(this, editor);
        $(editor.widget).prepend(this._toolbar.getTopElement());
        $(editor.widget).on(
            'keydown', 
            util.eventHandler(this._keyHandler.bind(this)));
    };

    this._keyHandler = function (e, jQthis) {
        if (!e.ctrlKey && !e.altKey && e.which === 32)
            return this._assignLanguage(e);
    };

    // XXX This function needs to be contextual: don't assign
    // languages in locations where language are already
    // assigned. e.g. citations of primary sources.
    this._assignLanguage = function (e) {
        var caret = this._editor.getCaret();
        
        if (caret === undefined)
            return true;
        
        // XXX we do not work with anything else than text nodes.
        if (caret[0].nodeType !== Node.TEXT_NODE)
            return true;

        // Find the previous word
        var offset = caret[0].nodeValue.slice(0, caret[1]).search(/\w+$/);

        // This could happen if the user enters spaces at the start of
        // an element for instance.
        if (offset === -1)
            return true;

        var word = caret[0].nodeValue.slice(offset, caret[1]);
        
        // XXX hardcoded
        var $new_element;
        if (word === "Abhidharma") {
            $new_element = transformation.wrapTextInElement(caret[0], offset, caret[1], "term", {"xml:lang": "sa-Latn"});
            // Simulate a link
            if ($new_element !== undefined)
                $new_element.contents().wrapAll("<a href='fake'>");
        }

        if ($new_element !== undefined) {
            // Place the caret after the element we just wrapped.
            rangy.getNativeSelection().collapse($new_element.get(0).nextSibling, 0);
            this._editor._caretChangeEmitter(e);
        }
        
        return true;
    };

    this.makeDecorator = function () {
        var obj = Object.create(BTWDecorator.prototype);
        // Make arg an array and add our extra argument(s).
        var args = Array.prototype.slice.call(arguments);
        args = [this, this._meta].concat(args);
        BTWDecorator.apply(obj, args);
        return obj;
    };

    this.getTransformationRegistry = function () {
        return this._tr;
    };

    this.getContextualMenuItems = function () {
        return this._contextual_menu_items;
    };

    this.getStylesheets = function () {
        return [require.toUrl("./btw.css")];
    };

    this.nodesAroundEditableContents = function (parent) {
        var ret = [null, null];
        var start = parent.childNodes[0];
        if ($(start).is("._gui"))
            ret[0] = start;
        var end = parent.childNodes[parent.childNodes.length - 1];
        if ($(end).is("._gui"))
            ret[1] = end;
        return ret;
    };
}).call(BTWMode.prototype);

exports.Mode = BTWMode;

});

