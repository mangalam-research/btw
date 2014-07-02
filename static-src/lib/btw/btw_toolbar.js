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
        {name: "quit", action: new QuitAction(editor)},
        {name: "save", action: new SaveAction(editor)},
        {name: "undo", action: new UndoAction(editor)},
        {name: "redo", action: new RedoAction(editor)},
        {name: "remove", action: new btw_tr.RemoveMixedTr(editor)},
        {name: "sanskrit",
         action: new btw_tr.SetTextLanguageTr(editor, "Sanskrit")},
        {name: "pali",
         action: new btw_tr.SetTextLanguageTr(editor, "Pāli")},
        {name: "latin",
         action: new btw_tr.SetTextLanguageTr(editor, 'Latin')},
    ];

    this._name_to_action = Object.create(null);

    this.$top = $('<div id="toolbar" class="ui-widget-header ui-corner-all">');
    for(var button_ix = 0, button;
        (button = this._buttons[button_ix]) !== undefined; button_ix++) {
        var name = button.name;
        var action = button.action;
        var $button;
        var icon = action.getIcon();
        $button = $("<button class='btn btn-default' name='" + name + "'>" +
                    (icon || action.getAbbreviatedDescription()) +
                    "</button>");
        if (icon || action.getAbbreviatedDescription() !==
            action.getDescription())
            $button.tooltip({title: action.getDescription(),
                             container: "body",
                             placement: "auto"});
        $button.click(this._click.bind(this));
        // Prevents acquiring the focus.
        $button.mousedown(false);
	this.$top.append($button);
        this._name_to_action[name] = action;
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
    var name = $(ev.delegateTarget).attr("name");
    var act = this._name_to_action[name];
    if (act instanceof btw_tr.SetTextLanguageTr) {
        // Don't execute if there is no range. Otherwise, wed will
        // raise an error that there is no caret when
        // fireTransformation is run.
        if (range && !range.collapsed)
            act.execute();
    }
    else if (act instanceof action.Action)
        act.execute();
    else
        throw new Error("broken toolbar");
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


function QuitAction(editor) {
    action.Action.call(this, editor, "Save and quit", "Save and quit",
                       "<i class='icon-ban-circle' style='color: red'></i>");
}

oop.inherit(QuitAction, action.Action);

QuitAction.prototype.execute = function (data) {
    var $form = this._editor.$gui_root.parents("form").first();
    this._editor.save(function (err) {
        if (!err)
            $form.submit();
    });
};

function SaveAction(editor) {
    action.Action.call(this, editor, "Save", "Save",
                       "<i class='icon-cloud-upload'></i>");
}

oop.inherit(SaveAction, action.Action);

SaveAction.prototype.execute = function (data) {
    this._editor.save();
};


exports.Toolbar = Toolbar;

});
