define(function (require, exports, module) {
'use strict';

var domutil = require("wed/domutil");
var splitTextNode = domutil.splitTextNode;

var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;

var transformation = require("wed/transformation");
var insertElement = transformation.insertElement;
var isWellFormedRange = transformation.isWellFormedRange;
var nodePairFromRange = transformation.nodePairFromRange;
var makeElement = transformation.makeElement;
var insertIntoText = transformation.insertIntoText;
var Transformation = transformation.Transformation;

var tr = new transformation.TransformationRegistry();

function insertSense(editor, parent, index, contents) {
    return insertElement(editor, parent, index, "sense", {"xml:id": "S." + sense_refs.nextNumber()}, contents);
}

tr.addTagTransformations(
    "insert",
    "sense", 
    new Transformation(
        "Create new sense",
        function (editor, node) {
            var caret = editor.getCaret();
            insertSense(editor, caret[0], caret[1]);
        }
    )
);


tr.addTagTransformations(
    "wrap",
    "sense", 
    new Transformation(
        "Wrap in sense",
        function (editor, node) {
            var range = domutil.getSelectionRange().cloneRange();
            if (!isWellFormedRange(range))
                throw new Error("invalid range.");

            // We capture this information because splitting text nodes
            // will trash our range object;
            var saved = domutil.getSelectionRange();

            var pair = nodePairFromRange(range);
            if (saved.startContainer.nodeType === Node.TEXT_NODE) {
                // We need to split the start and end Text nodes and
                // grab the stuff between them...
                pair[0] = splitTextNode(saved.startContainer, 
                                        saved.startOffset)[1];
                
                // The end container must change because we've just
                // split it!
                if (saved.endContainer === saved.startContainer) {
                    saved.endContainer = pair[0];
                    saved.endOffset = saved.endOffset - saved.startOffset;
                }
            }
            

            if (saved.endContainer.nodeType === Node.TEXT_NODE) {
                pair[1] = splitTextNode(saved.endContainer, 
                                        saved.endOffset)[0];

                // The start container must change because we've just split it!
                if (pair[0] === saved.endContainer)
                    pair[0] = pair[1];
            }

            var parent = pair[0].parentNode;
            var index = Array.prototype.indexOf.call(parent.childNodes, pair[0]);
            var end_index = Array.prototype.indexOf.call(parent.childNodes, pair[1]);
            var contents = Array.prototype.slice.call(parent.childNodes, index, end_index + 1);
            insertSense(editor, parent, index, contents);
        }
    )
);

tr.addTagTransformations(
    "insert",
    "ptr", 
    [new Transformation(
        "Create new sense hyperlink",
        function (editor, node) {
            var caret = editor.getCaret();
            var parent = caret[0];
            var index = caret[1];
            var $senses =  $(editor.widget).find('.sense').clone();

            $senses.find('._gui').remove();

            var $hyperlink_modal = editor.$hyperlink_modal;
            $hyperlink_modal.find('h3').text("Insert hyperlink");
            $hyperlink_modal.find('.modal-body').empty();
            $hyperlink_modal.find('.modal-body').append($('<div class="btn-group" data-toggle="buttons-radio">').append($senses));
            $senses.wrap('<label class="radio">');
            $senses.before('<input type="radio" name="sense-radio"/>');
            $hyperlink_modal.find(":radio").on('click.wed', function () {
                $hyperlink_modal.find('.btn-primary').prop('disabled', false).removeClass('disabled');
            });
            $hyperlink_modal.find('.btn-primary').prop("disabled", true).addClass("disabled");
            $hyperlink_modal.on('click.wed', '.btn', function () {
                $(this).addClass('modal-clicked');
                return true;
            });
            $hyperlink_modal.on('hide.wed', function () {
                $hyperlink_modal.off('.wed');
                var $clicked = $hyperlink_modal.find('.modal-clicked');
                var id = $hyperlink_modal.find(':radio:checked').next('.sense').attr(util.encodeAttrName('xml:id'));
                $hyperlink_modal.find('.modal-body').empty();
                if ($clicked.length > 0 && $clicked.hasClass('btn-primary')) {
                    $clicked.removeClass('modal-clicked');
                    // Find which radio is selected
                    var $ptr = makeElement('ptr', 
                                           {'target': "#" + id},
                                          true);
                    switch(parent.nodeType) {
                    case Node.TEXT_NODE:
                        insertIntoText(parent, index, $ptr.get(0));
                        break;
                    case Node.ELEMENT_NODE:
                        $(parent.childNodes[index]).before($ptr);
                        break;
                    default:
                        throw new Error("unexpected node type: " + parent.nodeType);
                    }
                    
                }
            });
            $hyperlink_modal.modal();
        }
    )]
);

tr.addTagTransformations(
    "delete",
    "orth", 
    [new Transformation(
        "Delete orthography",
        function (editor, node) {
            var element = editor.getCaret()[0];
            var $element = $((element.nodeType === Node.ELEMENT_NODE)? element: element.parentNode);
            if ($element.hasClass("orth"))
                $element.remove();
        }
    )]
);

tr.addTagTransformations(
    "merge-with-next",
    "orth", 
    [new Transformation(
        "Merge orthography with next",
        function (editor, node) {
            var element = editor.getCaret()[0];
            var $element = $((element.nodeType === Node.ELEMENT_NODE)? element: element.parentNode);
            var $after = $element.nextAll("._real").first();
            if ((util.getOriginalName($element.get(0)) === "orth") &&
                (util.getOriginalName($after.get(0)) === "orth"))
            {
                $element.append($after.contents());
                $after.remove();
            }
        }
    )]
);

tr.addTagTransformations(
    "merge-with-previous",
    "orth", 
    [new Transformation(
        "Merge orthography with previous",
        function (editor, node) {
            var element = editor.getCaret()[0];
            var $element = $((element.nodeType === Node.ELEMENT_NODE)? element: element.parentNode);
            var $before = $element.prevAll("._real").first();
            if ((util.getOriginalName($element.get(0)) === "orth") &&
                (util.getOriginalName($before.get(0)) === "orth"))
            {
                $before.append($element.contents());
                $element.remove();
            }
        }
    )]
);

function insertXr(editor, parent, index) {
    var $new = insertElement(editor, parent, index, "xr", undefined, undefined);
    // Our new element has no contents so it contains only the placeholder.
    var $ph = $new.children('._placeholder');
    $ph.replaceWith(makeElement("term", {"xml:lang": "sa-Latn"}, false));

    return $new;
}

tr.addTagTransformations(
    "append",
    "xr", 
    new Transformation(
        "Add new related term after this one",
        function (editor, node) {
            var parent = node.parentNode;
            var index = Array.prototype.indexOf.call(parent.childNodes, node) + 1;
            insertXr(editor, parent, index);
        }
    )
);

tr.addTagTransformations(
    "prepend",
    "xr", 
    new Transformation(
        "Add new related term before this one",
        function (editor, node) {
            var parent = node.parentNode;
            var index = Array.prototype.indexOf.call(parent.childNodes, node);
            insertXr(editor, parent, index);
        }
    )
);

exports.tr = tr;


});
