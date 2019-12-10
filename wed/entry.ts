/**
 * Entry point for creating a wed bundle.
 */
import { Container } from "inversify";

// tslint:disable-next-line:no-submodule-imports
import { action, bindEditor, EditorAPI,
         Options } from "@wedxml/core/dev/lib/wed";

import Action = action.Action;

// tslint:disable-next-line:no-submodule-imports no-implicit-dependencies
import { SAVER_OPTIONS } from "@wedxml/base-saver/tokens";
import { ActionCtor, EditorInstance } from "@wedxml/client-api";
import { EDITOR_INSTANCE, EDITOR_OPTIONS, EDITOR_WIDGET, GRAMMAR_LOADER,
// tslint:disable-next-line:no-submodule-imports no-implicit-dependencies
         RUNTIME, SAVER } from "@wedxml/common/tokens";
import { DefaultRuntime } from "@wedxml/default-runtime";
import { AjaxSaver, Options as SaverOptions } from "@wedxml/ajax-saver";
import { TrivialGrammarLoader } from "@wedxml/trivial-grammar-loader";

const BTW_MODE_ORIGIN = "https://github.com/mangalam-research/btw";

export class QuitAction extends Action<{}> {
  constructor(editor: EditorAPI) {
    super(BTW_MODE_ORIGIN, editor, "Save and quit", {
      abbreviatedDesc: "Save and quit",
      icon: "<i class='fa fa-sign-out' style='color: green'></i>",
    });
  }

  execute(): void {
    const $form = this.editor.$guiRoot.parents("form").first();
    // tslint:disable-next-line:no-floating-promises
    this.editor.save().then(() => {
      $form.submit();
    });
  }
}

export class QuitWithoutSavingAction extends Action<{}> {
  constructor(editor: EditorAPI) {
    super(BTW_MODE_ORIGIN, editor, "Quit without saving", {
      abbreviatedDesc: "Quit without saving",
      icon: "<i class='fa fa-ban' style='color: red'></i>",
    });
  }

  execute(): void {
    const $form = this.editor.$guiRoot.parents("form").first();
    $form.submit();
  }
}

export async function load(widget: Element,
                           options: Options,
                           saverOptions: SaverOptions,
                           text: string): Promise<EditorInstance> {
  await new Promise((resolve) => $(resolve));

  const container = new Container({ defaultScope: "Singleton" });
  container.bind(SAVER).to(AjaxSaver);
  container.bind(GRAMMAR_LOADER).to(TrivialGrammarLoader);
  container.bind(EDITOR_OPTIONS).toConstantValue(options);
  container.bind(SAVER_OPTIONS).toConstantValue(saverOptions);
  container.bind(EDITOR_WIDGET).toConstantValue(widget);
  container.bind(RUNTIME).to(DefaultRuntime);
  bindEditor(container);
  const editor = (window as any).wed_editor =
    container.get<EditorInstance>(EDITOR_INSTANCE);
  editor.addToolbarAction(QuitAction as ActionCtor,
                          { prepend: true });
  editor.addToolbarAction(QuitWithoutSavingAction as ActionCtor,
                          { right: true });
  await editor.init(text);
  return editor;
}

export * from "@wedxml/core/dev/lib/wed";
