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
        var sense_label = editor.decorator._getSenseLabel(sense);

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
            var subsense_label = editor.decorator._getSubsenseLabel(subsense);
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
        if (abbr) {
            abbr = abbr.cloneNode(true);
            child = abbr.firstElementChild;
            while(child) {
                var next = child.nextElementSibling;
                if (child.classList.contains("_gui"))
                    abbr.removeChild(child);
                child = next;
            }
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

function InsertBiblPtrDialogAction() {
    Action.apply(this, arguments);
}

oop.inherit(InsertBiblPtrDialogAction, Action);

InsertBiblPtrDialogAction.prototype.execute = function (data) {
    var editor = this._editor;

    var modal = editor.mode._bibliography_modal;
    var $primary = modal.getPrimary();
    var $body = $('<div>');
    $body.load(editor.mode._bibl_search_url, function() {
        // The element won't exist until the load is performed so we
        // have to put this in the callback. (Or we could use
        // delegation but delegation is not strictly speaking
        // necessary here.)
        var $table = $body.find("#bibliography-table");
        $table.on('refresh-results',
                  function () {
            $primary.prop('disabled', true).addClass('disabled');
        });
        $table.on('selected-row', function () {
            $primary.prop('disabled', false).removeClass('disabled');
        });
    });
    $primary.prop("disabled", true).addClass("disabled");

    modal.setBody($body);
    modal.modal(function () {
        var clicked = modal.getClickedAsText();
        if (clicked === "Insert") {
            var url = $body.find('.selected-row').data('item-url');
            data.target = url;
            editor.mode.insert_ref_tr.execute(data);
        }
    });
};

exports.InsertBiblPtrDialogAction = InsertBiblPtrDialogAction;

});
