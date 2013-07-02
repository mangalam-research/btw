define(function (require, exports, module) {
'use strict';

var Decorator = require("wed/decorator").Decorator;
var oop = require("wed/oop");
var $ = require("jquery");
var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;

function BTWDecorator(mode) {
    Decorator.apply(this, Array.prototype.slice.call(arguments, 1));

    this._mode = mode;
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("sense"),
                           this.includedSenseHandler.bind(this, this._domlistener));
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("form"),
                           this.includeListHandler.bind(this, " / "));
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("div") + ", " +
                           util.classFromOriginalName("btw:translation"),
                           headingDecorator);
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("btw:related"),
                           this.includedRelatedHandler.bind(this));
    this._domlistener.addHandler(["added-element", "removed-element"],
                           util.classFromOriginalName("orth"),
                           this.addRemListElementHandler.bind(this, " / "));
    this._domlistener.addHandler(["added-element", "removed-element"],
                           util.classFromOriginalName("xr"),
                           this.addRemListElementHandler.bind(this, ", "));
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("term"),
                           languageDecorator);
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("ptr"),
                           ptrDecorator);
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("btw:translation") +
                           "[" + util.encodeAttrName("type") + "= 'classical']",
                           this.includeListHandler.bind(this, "; "));
    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("btw:translation") +
                           "[" + util.encodeAttrName("type") + "= 'contemporary-translations']",
                           this.includeListHandler.bind(this, $('<br/>')));

    this._domlistener.addHandler("included-element",
                           util.classFromOriginalName("btw:lang"),
                           includedBTWLangHandler);

    this._domlistener.addHandler("included-element",
                           "[" + util.encodeAttrName("xml\\:lang") + "]:not(" + util.classFromOriginalName("btw:lang") + ")",
                           languageDecorator);

    this._domlistener.addHandler("included-element",
                           [util.classFromOriginalName("cit"),
                            util.classFromOriginalName("quote"),
                            util.classFromOriginalName("btw:example"),
                            util.classFromOriginalName("btw:cit"),
                            util.classFromOriginalName("btw:tr"),
                            util.classFromOriginalName("note"),
                            util.classFromOriginalName("lbl"),
                            util.classFromOriginalName("pron")].join(", "),
                           this.elementDecorator.bind(this));
    this._domlistener.addHandler("added-element",
                           "._id_decoration",
                           addedIdHandler);

    this._domlistener.addHandler("trigger",
                           "ids",
                           idsTriggerHandler);
}

oop.inherit(BTWDecorator, Decorator);

(function () {
    this.includedRelatedHandler = function($root, $el) {
        headingDecorator($root, $el, "related terms");
        $el.children("._real").each(function (x, child) {
            relatedChildDecorator(child);
            this.listDecorator(child, ", ");
        }.bind(this));
    };

    this.includedSenseHandler = function (listener, $root, $element) {
        $element.remove("._button_and_id._phantom");
        this.elementDecorator($root, $element);

        listener.trigger("ids");
    };

    // Override
    this.contentDecoratorInclusionHandler = function ($root,
                                                      $element) {
        var pair =
            this._mode.nodesAroundEditableContents($element.get(0));

        this._contentDecorator($root, $element, $(pair[0]), $(pair[1]));
    };

}).call(BTWDecorator.prototype);

function jQuery_escapeID(id) {
    return id.replace(/\./g, '\\.');
}

function idsTriggerHandler($root) {
    sense_refs.deallocateAll();
    $root.find("[" + util.encodeAttrName("xml:id") + "]").each(function (x, el) {
        idDecorator(el);
    });

    $root.find('.ptr').each(function (x, el) {
        ptrDecorator($root, $(el));
    });

    $root.find('.ref').each(function (x, el) {
        refDecorator($root, $(el));
    });
}


var next_head = 0;
function allocateHeadID() {
    return "BTW.H." + ++next_head;
}

var type_to_heading_map = {
    "definition": "definition",
    "classical-examples": "classical examples",
    "semantic-fields": "semantic fields",
    "etymology": "etymology",
    "contemporary-translations": "equivalents, translation and paraphrases in contemporary scholarship",
    "classical": "classical equivalents",
    "other-sample-contexts": "other sample contexts",
    "discussions": "discussions in dictionaries and secondary literature" ,
    "linguistic-considerations": "linguistic considerations"
};

function headingDecorator($root, $el, head) {
    if (head === undefined) {
        var type = $el.attr(util.encodeAttrName('type'));
        if (type === undefined)
            throw new Error("can't get type");
        head = type_to_heading_map[type];
        if (head === undefined)
            throw new Error("found an element with type: " + type + ", which is not handled");
    }

    head = $('<div class="head _phantom">[' + head + "]</div>");
    head.attr('id', allocateHeadID());

    $el.prepend(head);
}

/**
 * This function adds a separator between each child element of the
 * element passed as <code>el</code>. The function only considers
 * _real elements. This function accepts non-homogeneous lists.
 *
 */
function beforeListItemDecorator(el, child_name, sep) {
    // First drop all children that are separators
    $(el).children('[data-wed--separator-for]').remove();

    // If sep is a string, create an appropriate div.
    if (typeof sep === "string")
        sep = $('<div class="_text">' + sep + "</div>");

    $(sep).addClass('_phantom');
    $(sep).attr('data-wed--separator-for', child_name);

    var first = true;
    $(el).children('.' + child_name + '._real').each(function () {
        if (!first)
            $(this).before(sep.clone());
        else
            first = false;
    });
}

/**
 * This function adds a separator between each child element of the
 * element passed as <code>el</code>. The function only considers
 * _real elements. This function accepts non-homogeneous lists.
 *
 */
function heterogeneousListItemDecorator(el, sep) {
    // First drop all children that are separators
    $(el).children('[data-wed--separator-for]').remove();

    // If sep is a string, create an appropriate div.
    if (typeof sep === "string")
        sep = $('<div class="_text">' + sep + "</div>");

    $(sep).addClass('_phantom');

    var first = true;
    $(el).children('._real').each(function () {
        if (!first)
            $(this).before(sep.clone().attr('data-wed--separator-for', util.getOriginalName(el)));
        else
            first = false;
    });
}

function idDecorator(el) {
    var $el = $(el);
    var id = $el.attr(util.encodeAttrName("xml:id"));
    $el.attr("id", "BTW." + id);
    // Remove the old one before putting in the new one.
    if (id.indexOf("S.") === 0) {
        var label = $('<div class="_text _phantom _id_decoration" data-wed--for="'+ id + '">');
        label.append("(" + sense_refs.allocateLabel(id) + ") ");

        var old_label = $el.find("[data-wed--for='" + id + "']");

        if (old_label.length === 0) {
            var last = el.firstChild;
            // Skip over start gui elements
            while (last !== null &&
                   $(last).hasClass("_gui") &&
                   $(last).hasClass("_start_button"))
                last = last.nextSibling;
            if (last !== null)
                $(last).before(label);
            else
                $el.prepend(label);
        }
        else
            old_label.replaceWith(label);
    }
    else if (id.indexOf("LBL.") === 0) {
        // nothing required
    }
    else
        throw new Error("unknown type of id: " + id);
}

function linkingDecorator($el, is_ptr) {
    var orig_target = $.trim($el.attr(util.encodeAttrName("target")));
    if (orig_target === undefined)
        throw new Error("ptr element without target");

    var target = orig_target.replace(/#(.*)$/,'#BTW.$1');

    var $text = $('<div class="_text _phantom _linking_deco">');
    var $a = $("<a>", {"class": "_phantom", "href": target});
    $text.append($a);
    if (is_ptr) {
        // _linking_deco is used locally to make this function idempotent
        $el.children().remove("._linking_deco");
        if (orig_target.indexOf("#S.") === 0) {
            var label = sense_refs.idToLabel(orig_target.slice(1));

            // In other words, if we do not have a label yet, just
            // return silently. This can happen when a document is
            // first initialized. There is no guarantee that IDs will
            // have been assigned by the time this code is
            // called. There is, however, a guarantee that once IDs
            // are assigned, this code will be called.
            if (label === undefined)
                return;


            $a.text(label + ")");
            $a.toggleClass("_sense_ptr");
            $text.append(" ");
            // A ptr contains only attributes, no text, so we can just append.
            $el.append($text);

            // Find the referred element.
            var $target = $(jQuery_escapeID(target));
            $text.tooltip({"title": $target.html(), "html": true, "container": "body"});
        }
        else
            throw new Error("unknown type of target: " + orig_target);

    }
    else {
        $el.find("a").children().unwrap().unwrap();
        var inner_text = $('<div class="_real _text">');
        $a.append(inner_text);
        $el.contents().wrapAll($text);

        // Wrap all essentially creates a new element out of
        // text, so we have to find it again.
        $text = $el.children("._text._phantom");
        $text.tooltip({"title": "*** Place holder. Function not implemented yet. TODO.***",
                   "html": true, "container": "body"});
    }
}

function ptrDecorator($root, $el) {
    linkingDecorator($el, true);
}

function refDecorator($root, $el) {
    linkingDecorator($el, false);
}

var lang_to_label = {
    "sa-Latn": "Sanskrit; Skt",
    "pi-Latn": "Pāli; Pāli",
    "bo-Latn": "Tibetan; Tib",
    "zh-Hant": "Chinese; Ch",
    "x-gandhari-Latn": "Gāndhārī; Gāndh",
    "en": "English; Eng",
    "fr": "French; Fr",
    "de": "German; Ger",
    "it": "Italian; It",
    "es": "Spanish; Sp",
    // Additional languages
    "la": "Latin; Lat",
    "zh-Latn-pinyin": "Chinese Pinyin; Ch Pin",
    "x-bhs-Latn": "Buddhist Hybrid Sanskrit; BHSkt",
}

function languageDecorator($root, $el) {
    var lang = $el.attr(util.encodeAttrName("xml:lang"));
    var prefix = lang.slice(0, 2);
    if (prefix !== "en") {
        $el.css("background-color", "#CCFF66")
        // Chinese is not commonly italicized.
        if (prefix !== "zh")
            $el.css("font-style", "italic");

        var label = lang_to_label[lang];
        if (label === undefined)
            throw new Error("unknown language: " + lang);
        label = label.split("; ")[0];
        $el.tooltip({"title": label, "container": "body"});
    }
}


function addedIdHandler($root, $parent, $previous_sibling, $next_sibling, $element) {
    var $parent = $element.parent();
    if ($parent.is(util.classFromOriginalName("sense"))) {
        var $start = $parent.children("._gui._start_button");
        $start.nextUntil($element).addBack().add($element).wrapAll("<span class='_gui _button_and_id _phantom'>");
    }
}

function relatedChildDecorator(child) {
    var name_to_text = {
        "btw:synonym": "synonyms",
        "btw:cognate": "cognates",
        "btw:analogic": "analogic",
        "btw:contrastive": "contrastive",
        "btw:cp": undefined // Special
    };
    var $child = $(child);
    $child.children().remove('._head');
    var orig_name = util.getOriginalName(child);
    var head = name_to_text[orig_name];
    var header;
    if (orig_name === 'btw:cp') // special
        header = $('<div class="_text _phantom _head"><div class="abbr _phantom" data-wed-corresp="/abbr/Cp">Cp.</div> also </div>');

    else
        header = $('<div class="_text _phantom _head">' + head + ': </div>');
    $child.prepend(header);
}

function includedBTWLangHandler($root, $el) {
    var lang = $el.attr(util.encodeAttrName('xml:lang'));
    var label = lang_to_label[lang];
    if (label === undefined)
        throw new Error("unknown language: " + lang);
    // We want the abbreviation
    label = label.split("; ", 2)[1] + " ";
    $el.prepend("<div class='_text _phantom'>" + label + "</div>");
    heterogeneousListItemDecorator($el.get(0), ", ");
}

exports.BTWDecorator = BTWDecorator;

});
