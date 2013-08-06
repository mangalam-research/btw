define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var domutil = require("wed/domutil");
var action = require("wed/action");
var btw_tr = require("./btw_tr");

function Toolbar(editor) {
    this._editor = editor;
    this._buttons = [
        $("<button class='btn btn-default'><i class='icon-undo'></i> Undo</button>"),
        $("<button class='btn btn-default'><i class='icon-repeat'></i> Redo</button>"),
        new btw_tr.RemoveMixedTr(editor),
        new btw_tr.SetTextLanguageTr(editor, "Sanskrit"),
        'pālī',
        'tibetan',
        'chinese',
        'foreign'
    ];

    this.$top = $('<div id="toolbar" class="ui-widget-header ui-corner-all">');
    for(var button_ix = 0, button;
        (button = this._buttons[button_ix]) !== undefined; button_ix++) {
        var name = button;
        var $button;
        if (name instanceof $) {
            $button = name;
            $button.attr('id', button_ix);
        }
        else if (name instanceof action.Action) {
            var icon = name.getIcon();
            $button = $("<button class='btn btn-default' id='" + button_ix + "'>" +
                        (icon || name.getAbbreviatedDescription()) + "</button>");
            if (icon || name.getAbbreviatedDescription() !==
                name.getDescription())
                $button.tooltip({title: name.getDescription(),
                                container: "body"});
        }
        else
            $button = $("<button class='btn btn-default' id='" + button_ix +
                        "'>" + name + "</button>");
        $button.click(this._click.bind(this));
	this.$top.append($button);
    }
}

(function () {

    this.getTopElement = function () {
	// There's no point in hiding this value.
	return this.$top.get(0);
    };

    this._click = function (ev) {
        ev.stopImmediatePropagation();
        ev.preventDefault();
        var range = this._editor.getSelectionRange();
        var button_ix = $(ev.delegateTarget).attr("id");
        var button = this._buttons[button_ix];
        if (button instanceof action.Action)
            button.execute();
        else
            throw new Error("XXX broken toolbar");
        return false;
    };

}).call(Toolbar.prototype);

exports.Toolbar = Toolbar;

});
