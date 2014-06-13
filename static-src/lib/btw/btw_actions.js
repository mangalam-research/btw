define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var oop = require("wed/oop");
var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;
var btw_util = require("./btw_util");
var transformation = require("wed/transformation");
var Action = require("wed/action").Action;
var jqutil = require("wed/jqutil");

function SensePtrDialogAction() {
    Action.apply(this, arguments);
}

oop.inherit(SensePtrDialogAction, Action);

SensePtrDialogAction.prototype.execute = function (data) {
    var editor = this._editor;

    var $senses =
            editor.$gui_root.find(util.classFromOriginalName("btw:sense"));
    var labels = [];
    $senses.each(function () {
        var $this = $(this);
        var $data_node = $($this.data("wed_mirror_node"));
        var $terms = btw_util.termsForSense($data_node);
        var terms = [];
        $terms.each(function () {
            terms.push($(this).text());
        });
        terms = terms.join(", ");
        var sense_label = editor.decorator._getSenseLabel(this);
        var $div = $("<span>").data("wed-id", $this.attr("id")).
            append(" [" + sense_label + "] ").
            append(terms);
        labels.push($div);

        $this.find(util.classFromOriginalName("btw:subsense")).each(
            function () {
            var $this = $(this);
            var $data_node = $($this.data("wed_mirror_node"));
            var subsense_label = editor.decorator._getSubsenseLabel(this);
            var $explanation = $data_node.find(
                util.classFromOriginalName("btw:explanation"));
            var $div = $("<span>").data("wed-id", $this.attr("id")).
                append(" [" + subsense_label + "] ").
                append($explanation.text());
            labels.push($div);
        });
    });

    var hyperlink_modal = editor.mode._hyperlink_modal;
    var $primary = hyperlink_modal.getPrimary();
    var $body = $('<div>');
    $body.append(labels);
    $body.children().wrap('<div></div>');
    $body.children().prepend('<input type="radio" name="sense-radio"/>');
    $body.find(":radio").on('click.wed', function () {
        $primary.prop('disabled', false).removeClass('disabled');
    });
    $primary.prop("disabled", true).addClass("disabled");
    hyperlink_modal.setBody($body);
    hyperlink_modal.modal(function () {
        var clicked = hyperlink_modal.getClickedAsText();
        if (clicked === "Insert") {
            var id = $body.find(':radio:checked').next().data("wed-id");
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

    var $examples =
            editor.$gui_root.find(jqutil.toDataSelector(
                "btw:example, btw:example-explained"));
    var labels = [];
    $examples.each(function () {
        var $this = $(this);
        var $data_node = $($this.data("wed_mirror_node"));
        var $cit = $data_node.children(util.classFromOriginalName("btw:cit"));
        var $abbr = $this.find(util.classFromOriginalName("ref"))
            .first().clone();
        $abbr.children("._gui").remove();
        var $div = $("<span>").data("wed-id", $this.attr("id")).
            append(" " + $abbr.text() + " " + $cit.text());
        labels.push($div);
    });

    var hyperlink_modal = editor.mode._hyperlink_modal;
    var $primary = hyperlink_modal.getPrimary();
    var $body = $('<div>');
    $body.append(labels);
    $body.children().wrap('<div></div>');
    $body.children().prepend('<input type="radio" name="sense-radio"/>');
    $body.find(":radio").on('click.wed', function () {
        $primary.prop('disabled', false).removeClass('disabled');
    });
    $primary.prop("disabled", true).addClass("disabled");
    hyperlink_modal.setBody($body);
    hyperlink_modal.modal(function () {
        var clicked = hyperlink_modal.getClickedAsText();
        if (clicked === "Insert") {
            var id = $body.find(':radio:checked').next().data("wed-id");
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
