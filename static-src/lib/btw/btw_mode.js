define(function (require, exports, module) {
'use strict';

var util = require("wed/util");
var Mode = require("wed/mode").Mode;
var oop = require("wed/oop");
var BTWDecorator = require("./btw_decorator").BTWDecorator;
var tr = require("./btw_tr").tr;
var transformation = require("wed/transformation");
var Toolbar = require("./btw_toolbar").Toolbar;
var rangy = require("rangy");

var prefix_to_uri = {
    "btw": "http://lddubeau.com/ns/btw-storage",
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "": "http://www.tei-c.org/ns/1.0"
};

function BTWMode () {
    Mode.call(this);
    this._resolver = new util.NameResolver();
    Object.keys(prefix_to_uri).forEach(function (k) {
        this._resolver.definePrefix(k, prefix_to_uri[k]);
    }.bind(this));
    this._toolbar = new Toolbar();
    // This happens to be constant for this mode
    this._contextual_menu_items = [
        ["Create abbreviation",
         this._createAbbreviation.bind(this)]
    ];
}

oop.inherit(BTWMode, Mode);

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

    this._createAbbreviation = function () {
        this._editor.dismissMenu();
        var $hyperlink_modal = this._editor.$hyperlink_modal;
        var $body = $hyperlink_modal.find('.modal-body');
        $body.empty();

        var $typeahead = $("<input type='text' autocomplete='off'>");
        $typeahead.typeahead({
            'source': ["fem. -- feminine", "nt. -- neuter"] 
            });

        $body.append($typeahead);
        $hyperlink_modal.on('hide.wed', function () {
            $hyperlink_modal.off('.wed');
            /// XXX continue here.
        });

        $hyperlink_modal.modal();

    };

    this.getAbsoluteResolver = function () {
        return this._resolver;
    };

    this.makeDecorator = function () {
        var obj = Object.create(BTWDecorator.prototype);
        BTWDecorator.apply(obj, arguments);
        return obj;
    };

    this.getTransformationRegistry = function () {
        return tr;
    };

    this.getContextualMenuItems = function () {
        return this._contextual_menu_items;
    };

}).call(BTWMode.prototype);

exports.Mode = BTWMode;

});

