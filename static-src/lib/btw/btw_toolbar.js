/**
 * @module wed/modes/btw/btw_toolbar
 * @desc Toolbar for BTWMode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_toolbar */ function btwToolbar(
  require,
  exports,
  _module) {
  "use strict";

  var $ = require("jquery");
  var action = require("wed/action");
  var btwTr = require("./btw_tr");
  var log = require("wed/log");
  var oop = require("wed/oop");

  function Toolbar(mode, editor) {
    this._mode = mode;
    this._editor = editor;
    /* eslint-disable no-use-before-define */
    this._buttons = [
      { name: "quit", action: new QuitAction(editor) },
      { name: "save", action: new SaveAction(editor) },
      { name: "undo", action: new UndoAction(editor) },
      { name: "redo", action: new RedoAction(editor) },
      { name: "remove", action: new btwTr.RemoveMixedTr(editor) },
      { name: "sanskrit",
       action: new btwTr.SetTextLanguageTr(editor, "Sanskrit") },
      { name: "pali",
       action: new btwTr.SetTextLanguageTr(editor, "Pāli") },
      { name: "latin",
       action: new btwTr.SetTextLanguageTr(editor, "Latin") },
      { name: "reference", action: mode.insertBiblPtr },
      { name: "quitnosave", action: new QuitWithoutSavingAction(editor),
        extraClass: "pull-right" },
    ];

    this._name_to_action = Object.create(null);

    this.top = document.createElement("div");
    this.top.id = "toolbar";
    this.top.className = "ui-widget-header ui-corner-all";
    var boundClick = this._click.bind(this);
    for (var buttonIx = 0; buttonIx < this._buttons.length; buttonIx++) {
      var spec = this._buttons[buttonIx];
      var name = spec.name;
      var specAction = spec.action;
      var icon = specAction.getIcon();
      var button = document.createElement("button");
      button.className = "btn btn-default" +
        (spec.extraClass ? " " + spec.extraClass : "");
      button.name = name;
      button.innerHTML = icon || specAction.getAbbreviatedDescription();
      var $button = $(button);
      if (icon || specAction.getAbbreviatedDescription() !==
          specAction.getDescription()) {
        $button.tooltip({ title: specAction.getDescription(),
                          container: "body",
                          placement: "auto",
                          trigger: "hover" });
      }
      $button.click(boundClick);
      // Prevents acquiring the focus.
      $button.mousedown(false);
      this.top.appendChild(button);
      this._name_to_action[name] = specAction;
    }
  }

  Toolbar.prototype.getTopElement = function getTopElement() {
    // There's no point in hiding this value.
    return this.top;
  };

  Toolbar.prototype._click = log.wrap(function click(ev) {
    ev.stopImmediatePropagation();
    ev.preventDefault();
    var range = this._editor.getSelectionRange();
    var name = ev.delegateTarget.name;
    var act = this._name_to_action[name];
    if (act instanceof btwTr.SetTextLanguageTr) {
      // Don't execute if there is no range. Otherwise, wed will
      // raise an error that there is no caret when
      // fireTransformation is run.
      if (range && !range.collapsed) {
        act.execute();
      }
    }
    else if (act instanceof action.Action) {
      act.execute();
    }
    else {
      throw new Error("broken toolbar");
    }
    return false;
  });

  function UndoAction(editor) {
    action.Action.call(this, editor, "Undo", "Undo",
                       "<i class='fa fa-undo'></i>");
  }

  oop.inherit(UndoAction, action.Action);

  UndoAction.prototype.execute = function execute(_data) {
    this._editor.undo();
  };

  function RedoAction(editor) {
    action.Action.call(this, editor, "Redo", "Redo",
                       "<i class='fa fa-repeat'></i>");
  }

  oop.inherit(RedoAction, action.Action);

  RedoAction.prototype.execute = function execute(_data) {
    this._editor.redo();
  };


  function QuitAction(editor) {
    action.Action.call(this, editor, "Save and quit", "Save and quit",
                       "<i class='fa fa-sign-out' style='color: green'></i>");
  }

  oop.inherit(QuitAction, action.Action);

  QuitAction.prototype.execute = function execute(_data) {
    var $form = this._editor.$gui_root.parents("form").first();
    this._editor.save(function saved(err) {
      if (!err) {
        $form.submit();
      }
    });
  };

  function QuitWithoutSavingAction(editor) {
    action.Action.call(this, editor, "Quit without saving",
                       "Quit without saving",
                       "<i class='fa fa-ban' style='color: red'></i>");
  }

  oop.inherit(QuitWithoutSavingAction, action.Action);

  QuitWithoutSavingAction.prototype.execute = function execute(_data) {
    var $form = this._editor.$gui_root.parents("form").first();
    $form.submit();
  };


  function SaveAction(editor) {
    action.Action.call(this, editor, "Save", "Save",
                       "<i class='fa fa-cloud-upload'></i>");
  }

  oop.inherit(SaveAction, action.Action);

  SaveAction.prototype.execute = function execute(_data) {
    this._editor.save();
  };


  exports.Toolbar = Toolbar;
});
