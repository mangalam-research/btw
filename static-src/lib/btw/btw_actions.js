/**
 * @module wed/modes/btw/btw_actions
 * @desc Actions for BTWMode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_actions */ function btwTr(require,
                                                                     exports,
                                                                     _module) {
  "use strict";

  var $ = require("jquery");
  var _ = require("lodash");
  var oop = require("wed/oop");
  var util = require("wed/util");
  var btwUtil = require("./btw_util");
  var Action = require("wed/action").Action;
  var domutil = require("wed/domutil");
  // Yep, Bloodhound is provided by typeahead.
  var Bloodhound = require("typeahead");
  var SFEditor = require("./semantic_field_editor/app");
  var sfUtil = require("semantic-fields/util");

  function SensePtrDialogAction() {
    Action.apply(this, arguments);
  }

  oop.inherit(SensePtrDialogAction, Action);

  SensePtrDialogAction.prototype.execute = function execute(data) {
    var editor = this._editor;

    var doc = editor.gui_root.ownerDocument;
    var senses = editor.gui_root.querySelectorAll(
      util.classFromOriginalName("btw:sense"));
    var labels = [];
    var radios = [];
    for (var i = 0; i < senses.length; ++i) {
      var sense = senses[i];
      var dataNode = $.data(sense, "wed_mirror_node");
      var termNodes = btwUtil.termsForSense(sense);
      var terms = [];
      for (var tix = 0; tix < termNodes.length; ++tix) {
        terms.push($.data(termNodes[tix], "wed_mirror_node").textContent);
      }
      terms = terms.join(", ");
      var senseLabel = editor.decorator._refmans.getSenseLabel(sense);

      var span = doc.createElement("span");
      span.textContent = " [" + senseLabel + "] " + terms;
      span.setAttribute("data-wed-id", sense.id);

      var radio = doc.createElement("input");
      radio.type = "radio";
      radio.name = "sense";

      var div = doc.createElement("div");
      div.appendChild(radio);
      div.appendChild(span);

      labels.push(div);
      radios.push(radio);

      var subsenses = domutil.childrenByClass(sense, "btw:subsense");
      for (var ssix = 0; ssix < subsenses.length; ++ssix) {
        var subsense = subsenses[ssix];
        dataNode = $.data(subsense, "wed_mirror_node");
        var subsenseLabel = editor.decorator._refmans.getSubsenseLabel(subsense);
        var child = dataNode.firstElementChild;
        var explanation;
        while (child) {
          if (child.tagName === "btw:explanation") {
            explanation = child;
            break;
          }
          child = child.nextElementSibling;
        }

        span = doc.createElement("span");
        span.textContent = " [" + subsenseLabel + "] " +
          explanation.textContent;
        span.setAttribute("data-wed-id", subsense.id);

        radio = doc.createElement("input");
        radio.type = "radio";
        radio.name = "sense";

        div = doc.createElement("div");
        div.appendChild(radio);
        div.appendChild(span);

        labels.push(div);
        radios.push(radio);
      }
    }

    var hyperlinkModal = editor.mode._hyperlinkModal;
    var primary = hyperlinkModal.getPrimary()[0];
    var body = doc.createElement("div");
    for (var labelIx = 0; labelIx < labels.length; ++labelIx) {
      body.appendChild(labels[labelIx]);
    }
    $(radios).on("click.wed", function click() {
      primary.disabled = false;
      primary.classList.remove("disabled");
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlinkModal.setBody(body);
    hyperlinkModal.modal(function finished() {
      var clicked = hyperlinkModal.getClickedAsText();
      if (clicked === "Insert") {
        var id = body.querySelector("input[type='radio']:checked")
              .nextElementSibling.getAttribute("data-wed-id");
        data.target = id;
        editor.mode.insertPtrTr.execute(data);
      }
    });
  };

  exports.SensePtrDialogAction = SensePtrDialogAction;

  function ExamplePtrDialogAction() {
    Action.apply(this, arguments);
  }

  oop.inherit(ExamplePtrDialogAction, Action);

  ExamplePtrDialogAction.prototype.execute = function execute(data) {
    var editor = this._editor;

    var doc = editor.gui_root.ownerDocument;
    var examples = editor.gui_root.querySelectorAll(domutil.toGUISelector(
      "btw:example, btw:example-explained"));
    var labels = [];
    var radios = [];
    for (var i = 0; i < examples.length; ++i) {
      var example = examples[i];
      var dataNode = $.data(example, "wed_mirror_node");
      var child = dataNode.firstElementChild;
      var cit;
      while (child) {
        if (child.tagName === "btw:cit") {
          cit = child;
          break;
        }
        child = child.nextElementSibling;
      }

      var abbr = example.querySelector(util.classFromOriginalName("ref"));
      // We skip those examples that do not have a ref in them yet,
      // as links to them are meaningless.
      if (!abbr) {
        continue;
      }

      abbr = abbr.cloneNode(true);
      child = abbr.firstElementChild;
      while (child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("_gui")) {
          abbr.removeChild(child);
        }
        child = next;
      }

      var span = doc.createElement("span");
      span.setAttribute("data-wed-id", example.id);
      span.textContent = " " + (abbr ? abbr.textContent + " " : "") +
        cit.textContent;

      var radio = doc.createElement("input");
      radio.type = "radio";
      radio.name = "example";

      var div = doc.createElement("div");
      div.appendChild(radio);
      div.appendChild(span);

      labels.push(div);
      radios.push(radio);
    }

    var hyperlinkModal = editor.mode._hyperlinkModal;
    var primary = hyperlinkModal.getPrimary()[0];
    var body = doc.createElement("div");
    for (var labelIx = 0; labelIx < labels.length; ++labelIx) {
      body.appendChild(labels[labelIx]);
    }

    $(radios).on("click.wed", function click() {
      primary.disabled = false;
      primary.classList.remove("disabled");
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlinkModal.setBody(body);
    hyperlinkModal.modal(function finished() {
      var clicked = hyperlinkModal.getClickedAsText();
      if (clicked === "Insert") {
        var id = body.querySelector("input[type='radio']:checked")
              .nextElementSibling.getAttribute("data-wed-id");
        data.target = id;
        editor.mode.insertPtrTr.execute(data);
      }
    });
  };

  exports.ExamplePtrDialogAction = ExamplePtrDialogAction;

  var BIBL_SELECTION_MODAL_KEY = "btw_mode.btw_actions.bibl_selection_modal";
  function getBiblSelectionModal(editor) {
    var modal = editor.getModeData(BIBL_SELECTION_MODAL_KEY);
    if (modal) {
      return modal;
    }

    modal = editor.makeModal();
    modal.setTitle("Invalid Selection");
    modal.setBody(
      "<p>The selection should contain only text. The current " +
        "selection contains elements.</p>");
    modal.addButton("Ok", true);
    editor.setModeData(BIBL_SELECTION_MODAL_KEY, modal);

    return modal;
  }

  function InsertBiblPtrAction() {
    Action.apply(this, arguments);
  }

  oop.inherit(InsertBiblPtrAction, Action);

  InsertBiblPtrAction.prototype.execute = function execute(data) {
    var editor = this._editor;
    var range = editor.getSelectionRange();

    if (range && range.collapsed) {
      range = undefined;
    }

    if (range) {
      var nodes = range.getNodes();
      var nonText = false;
      for (var i = 0; !nonText && i < nodes.length; ++i) {
        if (nodes[i].nodeType !== Node.TEXT_NODE) {
          nonText = true;
        }
      }

      // The selection must contain only text.
      if (nonText) {
        getBiblSelectionModal().modal();
        return;
      }
    }

    var text = range && range.toString();

    // The nonword tokenizer provided by bloodhound.
    var nw = Bloodhound.tokenizers.nonword;
    function tokenizeItem(item) {
      return nw(item.title).concat(nw(item.creators), nw(item.date));
    }

    function tokenizePS(ps) {
      return tokenizeItem(ps.item).concat(nw(ps.reference_title));
    }

    function datumTokenizer(datum) {
      return datum.item ? tokenizePS(datum) : tokenizeItem(datum);
    }

    var options = {
      datumTokenizer: datumTokenizer,
      queryTokenizer: nw,
      local: [],
    };

    var citedEngine = new Bloodhound(options);
    var zoteroEngine = new Bloodhound(options);

    citedEngine.sorter = btwUtil.biblSuggestionSorter;
    zoteroEngine.sorter = btwUtil.biblSuggestionSorter;

    citedEngine.initialize();
    zoteroEngine.initialize();

    function renderSuggestion(obj) {
      var rendered = "";
      var item = obj;
      if (obj.reference_title) {
        rendered = obj.reference_title + " --- ";
        item = obj.item;
      }

      var creators = item.creators;
      var firstCreator = "***ITEM HAS NO CREATORS***";
      if (creators) {
        firstCreator = creators.split(",")[0];
      }

      rendered += firstCreator + ", " + item.title;
      var date = item.date;
      if (date) {
        rendered += ", " + date;
      }

      return "<p><span style='white-space: nowrap'>" +
        rendered + "</span></p>";
    }

    var taOptions = {
      options: {
        autoselect: true,
        hint: true,
        highlight: true,
        minLength: 1,
      },
      datasets: [{
        name: "cited",
        displayKey: btwUtil.biblDataToReferenceText,
        source: citedEngine.ttAdapter(),
        templates: {
          header: "Cited",
          suggestion: renderSuggestion,
          empty: " does not contain a match.",
        },
      }, {
        name: "zotero",
        displayKey: btwUtil.biblDataToReferenceText,
        source: zoteroEngine.ttAdapter(),
        templates: {
          header: "Zotero",
          suggestion: renderSuggestion,
          empty: " does not contain a match.",
        },
      }],
    };

    var pos = editor.computeContextMenuPosition(undefined, true);
    var ta = editor.displayTypeaheadPopup(
      pos.left, pos.top, 600, "Reference",
      taOptions,
      function executeTypeahead(obj) {
        if (!obj) {
          return;
        }

        data.target = obj.abstract_url;
        if (range) {
          editor.mode.replaceSelectionWithRefTr.execute(data);
        }
        else {
          editor.mode.insertRefTr.execute(data);
        }
      });

    editor.mode._getBibliographicalInfo().then(function then(info) {
      var allValues = [];
      var keys = Object.keys(info);
      for (var keyIx = 0; keyIx < keys.length; ++keyIx) {
        allValues.push(info[keys[keyIx]]);
      }

      var citedValues = [];
      var refs = editor.gui_root.querySelectorAll("._real.ref");
      for (var refIx = 0; refIx < refs.length; ++refIx) {
        var ref = refs[refIx];
        var origTarget = ref.getAttribute(util.encodeAttrName("target"));
        if (origTarget.lastIndexOf("/bibliography/", 0) !== 0) {
          continue;
        }

        citedValues.push(info[origTarget]);
      }

      zoteroEngine.add(allValues);
      citedEngine.add(citedValues);
      if (range) {
        ta.setValue(text);
      }
      ta.hideSpinner();
    });
  };

  exports.InsertBiblPtrAction = InsertBiblPtrAction;

  var EDIT_SF_MODAL_KEY = "btw_mode.btw_actions.edit_sf_modal";
  function getEditSemanticFieldModal(editor) {
    var modal = editor.getModeData(EDIT_SF_MODAL_KEY);
    if (modal) {
      return modal;
    }

    modal = editor.makeModal({
      resizable: true,
      draggable: true,
    });
    modal.setTitle("Edit Semantic Fields");
    modal.addButton("Commit", true);
    modal.addButton("Cancel");
    var body = modal.getTopLevel()[0]
      .getElementsByClassName("modal-body")[0];
    body.classList.add("sf-editor-modal-body");
    editor.setModeData(EDIT_SF_MODAL_KEY, modal);

    return modal;
  }

  function EditSemanticFieldsAction() {
    Action.apply(this, arguments);
  }

  oop.inherit(EditSemanticFieldsAction, Action);

  EditSemanticFieldsAction.prototype.execute = function execute(data) {
    var editor = this._editor;
    var dataCaret = editor.getDataCaret(true);
    var guiCaret = editor.fromDataLocation(dataCaret);
    var guiSfsContainer = domutil.closestByClass(guiCaret.node,
                                                 "btw:semantic-fields",
                                                 editor.gui_root);
    if (!guiSfsContainer) {
      throw new Error("unable to acquire btw:semantic-fields");
    }

    var sfsContainer = editor.toDataNode(guiSfsContainer);
    var sfs = domutil.dataFindAll(sfsContainer, "btw:sf");

    if (sfs.length === 0) {
      throw new Error("unable to acquire btw:sf");
    }

    var paths = sfs.map(function map(sf) {
      return sf.textContent;
    });

    var modal = getEditSemanticFieldModal(editor);
    var mode = editor.mode;
    var fetcher = editor.decorator._sfFetcher;

    function fieldToPath(f) {
      return f.get("path");
    }

    var sfEditor;
    var primary = modal.getPrimary()[0];
    primary.classList.add("disabled");
    modal.setBody("<i class='fa fa-spinner fa-2x fa-spin'></i>");

    modal.modal(function dismiss() {
      var clicked = modal.getClicked()[0];
      if (clicked && clicked === primary) {
        if (!sfEditor) {
          throw new Error("modal dismissed with primary button " +
                          "while sfEditor is non-existent");
        }

        data.newPaths = sfEditor.getChosenFields().map(fieldToPath);
        editor.mode.replaceSemanticFields.execute(data);
      }
    });

    fetcher.fetch(paths).then(function then(resolved) {
      var fields = _.values(resolved);

      // We grab the list of paths from the resolved fields because initially we
      // may have unknown fields, and the list of resolve fields may be shorter
      // than ``paths``.
      // Reminder: fields are plain old JS objects.
      var initialPaths = _.map(fields, "path");

      // Clear it before the editor is started.
      modal.setBody("");
      sfEditor = new SFEditor({
        container: modal.getTopLevel()[0]
          .getElementsByClassName("modal-body")[0],
        fields: fields,
        fetcher: fetcher,
        searchUrl: mode._semanticFieldFetchUrl,
      });
      sfEditor.start();

      sfEditor.on("sf:chosen:change", function change() {
        var newPaths = sfEditor.getChosenFields().map(fieldToPath);
        var method = _.isEqual(initialPaths, newPaths) ? "add" : "remove";
        primary.classList[method]("disabled");
      });
    });
  };

  exports.EditSemanticFieldsAction = EditSemanticFieldsAction;

});
