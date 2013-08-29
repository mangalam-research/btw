define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var oop = require("wed/oop");
var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;
var btw_util = require("./btw_util");
var transformation = require("wed/transformation");
var Action = require("wed/action").Action;

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
        var $terms = btw_util.termsForSense($this);
        var terms = [];
        $terms.each(function () {
            terms.push($(this).text());
        });
        terms = terms.join(", ");
        var sense_label = editor.decorator._getSenseLabel(this);
        var $div = $("<span>").attr(util.encodeAttrName("xml:id"),
                                   $this.attr(util.encodeAttrName("xml:id"))).
            append(" [" + sense_label + "] ").
            append(terms);
        labels.push($div);

        $this.find(util.classFromOriginalName("btw:subsense")).each(
            function () {
            var $this = $(this);
            var subsense_label = editor.decorator._getSubsenseLabel(this);
            var $explanation = $this.find(util.classFromOriginalName("btw:explanation")).clone();
            $explanation.find("._gui, ._phantom").remove();
            var $div = $("<span>").attr(util.encodeAttrName("xml:id"),
                                       $this.attr(util.encodeAttrName("xml:id"))).
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
            var id = $body.find(':radio:checked').next()
                    .attr(util.encodeAttrName('xml:id'));
            data.target = "#" + id;
            editor.mode.insert_ptr_tr.execute(data);
        }
    });
};

exports.SensePtrDialogAction = SensePtrDialogAction;

function InsertBiblPtrDialogAction() {
    Action.apply(this, arguments);
}

oop.inherit(InsertBiblPtrDialogAction, Action);

InsertBiblPtrDialogAction.prototype.execute = function (data) {
    var editor = this._editor;

    var modal = editor.mode._bibliography_modal;
    var $primary = modal.getPrimary();
    var $body = $('<div>');
    $body.load('/search/', function() {
        // The element won't exist until the load is performed so we
        // have to put this in the callback. (Or we could use
        // delegation but delegation is not strictly speaking
        // necessary here.)
        $body.find("#result_list").on('bibsearch-refresh-results',
                                       function () {
            $primary.prop('disabled', true).addClass('disabled');
        });
    });
    $primary.prop("disabled", true).addClass("disabled");
    $body.on('click.wed', ':radio', function () {
        $primary.prop('disabled', false).removeClass('disabled');
    });

    modal.setBody($body);
    modal.modal(function () {
        var clicked = modal.getClickedAsText();
        if (clicked === "Insert") {
            var item_key = $body.find(':radio:checked').val();
            data.target = "/bibl/" + item_key;
            editor.mode.insert_ref_tr.execute(data);
        }
    });
};

exports.InsertBiblPtrDialogAction = InsertBiblPtrDialogAction;

});
