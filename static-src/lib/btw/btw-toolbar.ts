/**
 * Toolbar for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import "bootstrap";
import * as $ from "jquery";

import { Action } from "wed/action";

import { Mode } from "./btw-mode";
import * as btwTr from "./btw-tr";

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
type Editor = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

class UndoAction extends Action<{}> {
  constructor(editor: Editor) {
    super(editor, "Undo", "Undo", "<i class='fa fa-undo'></i>");
  }

  execute(): void {
    this.editor.undo();
  }
}

class RedoAction extends Action<{}> {
  constructor(editor: Editor) {
    super(editor, "Redo", "Redo", "<i class='fa fa-repeat'></i>");
  }

  execute(): void {
    this.editor.redo();
  }
}

class QuitAction extends Action<{}> {
  constructor(editor: Editor) {
    super(editor, "Save and quit", "Save and quit",
          "<i class='fa fa-sign-out' style='color: green'></i>");
  }

  execute(): void {
    const $form = this.editor.$gui_root.parents("form").first();
    this.editor.save((err) => {
      if (!err) {
        $form.submit();
      }
    });
  }
}

class QuitWithoutSavingAction extends Action<{}> {
  constructor(editor: Editor) {
    super(editor, "Quit without saving", "Quit without saving",
          "<i class='fa fa-ban' style='color: red'></i>");
  }

  execute(): void {
    const $form = this.editor.$gui_root.parents("form").first();
    $form.submit();
  }
}

class SaveAction extends Action<{}> {
  constructor(editor: Editor) {
    super(editor, "Save", "Save", "<i class='fa fa-cloud-upload'></i>");
  }

  execute(): void {
    this.editor.save();
  }
}

export class Toolbar {
  private readonly buttons: ReadonlyArray<{ name: string, action: Action<{}>,
                                            extraClass?: string }>;
  private readonly nameToAction: Record<string, Action<{}>>;

  /** The top DOM element of the toolbar. */
  readonly top: Element;

  constructor(mode: Mode, private readonly editor: Editor) {
    this.buttons = [
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

    this.nameToAction = Object.create(null);

    this.top = document.createElement("div");
    this.top.id = "toolbar";
    this.top.className = "ui-widget-header ui-corner-all";
    const boundClick = this.click.bind(this);
    for (const spec of this.buttons) {
      const name = spec.name;
      const specAction = spec.action;
      const icon = specAction.getIcon();
      const button = document.createElement("button");
      const extraClass = spec.extraClass !== undefined ?
        ` ${spec.extraClass}` : "";
      button.className = `btn btn-default${extraClass}`;
      button.name = name;
      // tslint:disable-next-line:no-inner-html
      button.innerHTML = icon || specAction.getAbbreviatedDescription()!;
      const $button = $(button);
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
      this.nameToAction[name] = specAction;
    }
  }

  private click(ev: JQueryMouseEventObject): boolean {
    ev.stopImmediatePropagation();
    ev.preventDefault();
    const selection = this.editor.caretManager.sel;
    // tslint:disable-next-line:no-any
    const name = (ev.delegateTarget as any).name as string;
    const act = this.nameToAction[name];
    if (act instanceof btwTr.SetTextLanguageTr) {
      // Don't execute if there is no selection. Otherwise, wed will raise an
      // error that there is no caret when fireTransformation is run.
      if (selection && !selection.collapsed) {
        act.execute();
      }
    }
    else if (act instanceof Action) {
      act.execute({});
    }
    else {
      throw new Error("broken toolbar");
    }

    return false;
  }
}
