/**
 * A facility for producing BTW-specific editor instances.
 * @author Louis-Dominique Dubeau
 */
import { Action, EditorAPI, EditorInstance, makeEditor as stockMakeEditor,
         Options, Runtime } from "wed";

export class QuitAction extends Action<{}> {
  constructor(editor: EditorAPI) {
    super(editor, "Save and quit", "Save and quit",
          "<i class='fa fa-sign-out' style='color: green'></i>");
  }

  execute(): void {
    const $form = this.editor.$guiRoot.parents("form").first();
    this.editor.save().then(() => {
      $form.submit();
    });
  }
}

export class QuitWithoutSavingAction extends Action<{}> {
  constructor(editor: EditorAPI) {
    super(editor, "Quit without saving", "Quit without saving",
          "<i class='fa fa-ban' style='color: red'></i>");
  }

  execute(): void {
    const $form = this.editor.$guiRoot.parents("form").first();
    $form.submit();
  }
}

export function makeEditor(widget: HTMLElement,
                           options: Options | Runtime): EditorInstance {
  const editor = stockMakeEditor(widget, options);
  editor.addToolbarAction(QuitAction, { prepend: true });
  editor.addToolbarAction(QuitWithoutSavingAction, { right: true });
  return editor;
}
