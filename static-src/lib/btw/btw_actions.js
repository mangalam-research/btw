define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var oop = require("wed/oop");
var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;
var btw_util = require("./btw_util");
var transformation = require("wed/transformation");
var Action = require("wed/action").Action;
var domutil = require("wed/domutil");
var key_constants = require("wed/key_constants");
// Yep, Bloodhound is provided by typeahead.
var Bloodhound = require("typeahead");

function SensePtrDialogAction() {
    Action.apply(this, arguments);
}

oop.inherit(SensePtrDialogAction, Action);

SensePtrDialogAction.prototype.execute = function (data) {
    var editor = this._editor;

    var doc = editor.gui_root.ownerDocument;
    var senses = editor.gui_root.querySelectorAll(
        util.classFromOriginalName("btw:sense"));
    var labels = [];
    var radios = [];
    for(var i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        var data_node = $.data(sense, "wed_mirror_node");
        var term_nodes = btw_util.termsForSense(sense);
        var terms = [];
        for(var tix = 0, term_node; (term_node = term_nodes[tix]) !== undefined;
            ++tix)
            terms.push($.data(term_node, "wed_mirror_node").textContent);
        terms = terms.join(", ");
        var sense_label = editor.decorator._refmans.getSenseLabel(sense);

        var span = doc.createElement("span");
        span.textContent = " [" + sense_label + "] " + terms;
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
        for(var ssix = 0, subsense; (subsense = subsenses[ssix]) !== undefined;
            ++ssix) {
            data_node = $.data(subsense, "wed_mirror_node");
            var subsense_label = editor.decorator._refmans.getSubsenseLabel(subsense);
            var child = data_node.firstElementChild;
            var explanation;
            while (child) {
                if (child.tagName === "btw:explanation") {
                    explanation = child;
                    break;
                }
                child = child.nextElementSibling;
            }

            span = doc.createElement("span");
            span.textContent = " [" + subsense_label + "] " +
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

    var hyperlink_modal = editor.mode._hyperlink_modal;
    var primary = hyperlink_modal.getPrimary()[0];
    var body = doc.createElement("div");
    var el;
    for(i = 0; (el = labels[i]) !== undefined; ++i)
        body.appendChild(el);
    $(radios).on('click.wed', function () {
        primary.disabled = false;
        primary.classList.remove('disabled');
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlink_modal.setBody(body);
    hyperlink_modal.modal(function () {
        var clicked = hyperlink_modal.getClickedAsText();
        if (clicked === "Insert") {
            var id = body.querySelector('input[type="radio"]:checked')
                    .nextElementSibling.getAttribute("data-wed-id");
            data.target = id;
            editor.mode.insert_ptr_tr.execute(data);
        }
    });
};

exports.SensePtrDialogAction = SensePtrDialogAction;

function ExamplePtrDialogAction() {
    Action.apply(this, arguments);
}

oop.inherit(ExamplePtrDialogAction, Action);

ExamplePtrDialogAction.prototype.execute = function (data) {
    var editor = this._editor;

    var doc = editor.gui_root.ownerDocument;
    var examples = editor.gui_root.querySelectorAll(domutil.toGUISelector(
        "btw:example, btw:example-explained"));
    var labels = [];
    var radios = [];
    for(var i = 0, example; (example = examples[i]) !== undefined; ++i) {
        var data_node = $.data(example, "wed_mirror_node");
        var child = data_node.firstElementChild;
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
        if (!abbr)
            continue;

        abbr = abbr.cloneNode(true);
        child = abbr.firstElementChild;
        while(child) {
            var next = child.nextElementSibling;
            if (child.classList.contains("_gui"))
                abbr.removeChild(child);
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

    var hyperlink_modal = editor.mode._hyperlink_modal;
    var primary = hyperlink_modal.getPrimary()[0];
    var body = doc.createElement('div');
    var el;
    for(i = 0; (el = labels[i]) !== undefined; ++i)
        body.appendChild(el);
    $(radios).on('click.wed', function () {
        primary.disabled = false;
        primary.classList.remove('disabled');
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlink_modal.setBody(body);
    hyperlink_modal.modal(function () {
        var clicked = hyperlink_modal.getClickedAsText();
        if (clicked === "Insert") {
            var id = body.querySelector('input[type="radio"]:checked')
                    .nextElementSibling.getAttribute("data-wed-id");
            data.target = id;
            editor.mode.insert_ptr_tr.execute(data);
        }
    });
};

exports.ExamplePtrDialogAction = ExamplePtrDialogAction;

function InsertBiblPtrAction() {
    Action.apply(this, arguments);
}

oop.inherit(InsertBiblPtrAction, Action);

InsertBiblPtrAction.prototype.execute = function (data) {
    var editor = this._editor;
    var range = editor.getSelectionRange();

    if (range && range.collapsed)
        range = undefined;

    if (range) {
        var nodes = range.getNodes();
        var non_text = false;
        for (var i = 0, node; !non_text && (node = nodes[i]); ++i) {
            if (node.nodeType !== Node.TEXT_NODE)
                non_text = true;
        }

        // The selection must contain only text.
        if (non_text) {
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
        local: []
    };

    var cited_engine = new Bloodhound(options);
    var zotero_engine = new Bloodhound(options);

    cited_engine.sorter = btw_util.biblSuggestionSorter;
    zotero_engine.sorter = btw_util.biblSuggestionSorter;

    cited_engine.initialize();
    zotero_engine.initialize();

    function renderSuggestion(obj) {
        var data = "";
        var item = obj;
        if (obj.reference_title) {
            data = obj.reference_title + " --- ";
            item = obj.item;
        }

        var creators = item.creators;
        var first_creator = "***ITEM HAS NO CREATORS***";
        if (creators)
            first_creator = creators.split(",")[0];

        data += first_creator + ", " + item.title;
        var date = item.date;
        if (date)
            data += ", " + date;

        return "<p><span style='white-space: nowrap'>" +
            data + "</span></p>";
    }

    var ta_options = {
        options: {
            autoselect: true,
            hint: true,
            highlight: true,
            minLength: 1
        },
        datasets: [{
            name: 'cited',
            displayKey: btw_util.biblDataToReferenceText,
            source: cited_engine.ttAdapter(),
            templates: {
                header: "Cited",
                suggestion: renderSuggestion,
                empty: " does not contain a match."
            }
        }, {
            name: 'zotero',
            displayKey: btw_util.biblDataToReferenceText,
            source: zotero_engine.ttAdapter(),
            templates: {
                header: "Zotero",
                suggestion: renderSuggestion,
                empty: " does not contain a match."
            }

        }]
    };

    var pos = editor.computeContextMenuPosition(undefined, true);
    var ta = editor.displayTypeaheadPopup(pos.left, pos.top, 600, "Reference",
                                 ta_options, function (obj) {
        if (!obj)
            return;

        data.target = obj.url;
        if (range)
            editor.mode.replace_selection_with_ref_tr.execute(data);
        else
            editor.mode.insert_ref_tr.execute(data);
    });

    editor.mode._getBibliographicalInfo().then(function (info) {
        var all_values = [];
        var keys = Object.keys(info);
        var i, key;
        for (i = 0; (key = keys[i]); ++i) {
            all_values.push(info[key]);
        }

        var cited_values = [];
        var refs = editor.gui_root.querySelectorAll("._real.ref");
        var ref;
        for (i = 0; (ref = refs[i]); ++i) {
            var orig_target = ref.getAttribute(util.encodeAttrName("target"));
            if (orig_target.lastIndexOf("/bibliography/", 0) !== 0)
                continue;

            cited_values.push(info[orig_target]);
        }

        zotero_engine.add(all_values);
        cited_engine.add(cited_values);
        if (range)
            ta.setValue(text);
        ta.hideSpinner();
    });
};

exports.InsertBiblPtrAction = InsertBiblPtrAction;

var BIBL_SELECTION_MODAL_KEY = "btw_mode.btw_actions.bibl_selection_modal";
function getBiblSelectionModal(editor) {
    var modal = editor.getModeData(BIBL_SELECTION_MODAL_KEY);
    if (modal)
        return modal;

    modal = editor.makeModal();
    modal.setTitle("Invalid Selection");
    modal.setBody(
        "<p>The selection should contain only text. The current " +
            "selection contains elements.</p>");
    modal.addButton("Ok", true);
    editor.setModeData(BIBL_SELECTION_MODAL_KEY, modal);

    return modal;
}



});
