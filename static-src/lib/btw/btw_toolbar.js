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
        {name: "quitnosave", action: new QuitWithoutSavingAction(editor),
         extraClass: "pull-right"}
    ];

    this._name_to_action = Object.create(null);

    this.top = document.createElement("div");
    this.top.id = "toolbar";
    this.top.className = "ui-widget-header ui-corner-all";
    var bound_click = this._click.bind(this);
    for(var button_ix = 0, spec;
        (spec = this._buttons[button_ix]) !== undefined; button_ix++) {
        var name = spec.name;
        var action = spec.action;
        var icon = action.getIcon();
        var button = document.createElement("button");
        button.className = "btn btn-default" +
            (spec.extraClass ? " " + spec.extraClass: "");
        button.name = name;
        button.innerHTML = icon || action.getAbbreviatedDescription();
        var $button = $(button);
        if (icon || action.getAbbreviatedDescription() !==
            action.getDescription())
            $button.tooltip({title: action.getDescription(),
                             container: "body",
                             placement: "auto"});
        $button.click(bound_click);
        // Prevents acquiring the focus.
        $button.mousedown(false);
	this.top.appendChild(button);
        this._name_to_action[name] = action;
    }
}

Toolbar.prototype.getTopElement = function () {
    // There's no point in hiding this value.
    return this.top;
};

Toolbar.prototype._click = log.wrap(function (ev) {
    ev.stopImmediatePropagation();
    ev.preventDefault();
    var range = this._editor.getSelectionRange();
    var name = ev.delegateTarget.name;
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
                       "<i class='fa fa-undo'></i>");
}

oop.inherit(UndoAction, action.Action);

UndoAction.prototype.execute = function (data) {
    this._editor.undo();
};

function RedoAction(editor) {
    action.Action.call(this, editor, "Redo", "Redo",
                       "<i class='fa fa-repeat'></i>");
}

oop.inherit(RedoAction, action.Action);

RedoAction.prototype.execute = function (data) {
    this._editor.redo();
};


function QuitAction(editor) {
    action.Action.call(this, editor, "Save and quit", "Save and quit",
                       "<i class='fa fa-sign-out' style='color: green'></i>");
}

oop.inherit(QuitAction, action.Action);

QuitAction.prototype.execute = function (data) {
    var $form = this._editor.$gui_root.parents("form").first();
    this._editor.save(function (err) {
        if (!err)
            $form.submit();
    });
};

function QuitWithoutSavingAction(editor) {
    action.Action.call(this, editor, "Quit without saving",
                       "Quit without saving",
                       "<i class='fa fa-ban' style='color: red'></i>");
}

oop.inherit(QuitWithoutSavingAction, action.Action);

QuitWithoutSavingAction.prototype.execute = function (data) {
    var $form = this._editor.$gui_root.parents("form").first();
    $form.submit();
};


function SaveAction(editor) {
    action.Action.call(this, editor, "Save", "Save",
                       "<i class='fa fa-cloud-upload'></i>");
}

oop.inherit(SaveAction, action.Action);

SaveAction.prototype.execute = function (data) {
    this._editor.save();
};


exports.Toolbar = Toolbar;

});
