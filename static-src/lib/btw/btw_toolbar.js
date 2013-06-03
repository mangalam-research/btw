define(function (require, exports, module) {
'use strict';

var domutil = require("wed/domutil");
var transformation = require("wed/transformation");

var buttons = [
    'save',
    'undo',
    'redo',
    'sanskrit',
    { name: 'pālī', id: 'pali' } ,
    'tibetan',
    'chinese',
    'foreign'
];

function Toolbar() {
    this.$top = $('<div id="toolbar" class="ui-widget-header ui-corner-all">');
    for(var button_ix = 0, button; 
        (button = buttons[button_ix++]) !== undefined;) {
	var name = button;
	var id = name;
        if (typeof name !== "string") {
            id = name.id;
            name = name.name;
        }
	var $button = $("<button class='btn' id='" + id + "'>" + name + "</button>");
        $button.click(this._click.bind(this));
	this.$top.append($button);
    }
}

(function () {
    
    this.getTopElement = function () {
	// There's no point in hiding this value.
	return this.$top.get(0);
    };

    this._click = function (ev) {
        var range = domutil.getSelectionRange();

        if (range === undefined)
            return false;

        if (range.startContainer !== range.endContainer)
            return false;
        
        var $new_element;
        if ($(ev.target).attr("id") === "sanskrit")
            $new_element = transformation.wrapTextInElement(range.startContainer, range.startOffset, range.endOffset, "term", {"xml:lang": "sa-Latn"});

        return false;
    };

}).call(Toolbar.prototype);

exports.Toolbar = Toolbar;    

});
