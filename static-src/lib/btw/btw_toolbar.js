define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var domutil = require("wed/domutil");
var action = require("wed/action");
var btw_tr = require("./btw_tr");
var log = require("wed/log");
var oop = require("wed/oop");

function Toolbar(editor) {
    this._editor = editor;
    this._buttons = [
        new UndoAction(editor),
        new RedoAction(editor),
        new btw_tr.RemoveMixedTr(editor),
        new btw_tr.SetTextLanguageTr(editor, "Sanskrit"),
        new btw_tr.SetTextLanguageTr(editor, "Pāli"),
        new btw_tr.SetTextLanguageTr(editor, 'Latin'),
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

Toolbar.prototype.getTopElement = function () {
    // There's no point in hiding this value.
    return this.$top[0];
};

Toolbar.prototype._click = log.wrap(function (ev) {
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
});

function UndoAction(editor) {
    action.Action.call(this, editor, "Undo", "Undo",
                       "<i class='icon-undo'></i>");
}

oop.inherit(UndoAction, action.Action);

UndoAction.prototype.execute = function (data) {
    this._editor.undo();
};

function RedoAction(editor) {
    action.Action.call(this, editor, "Redo", "Redo",
                       "<i class='icon-repeat'></i>");
}

oop.inherit(RedoAction, action.Action);

RedoAction.prototype.execute = function (data) {
    this._editor.redo();
};


exports.Toolbar = Toolbar;

});
