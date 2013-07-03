define(function (require, exports, module) {
'use strict';

var Decorator = require("wed/decorator").Decorator;
var refmans = require("./btw_refmans");
var oop = require("wed/oop");
var $ = require("jquery");
var util = require("wed/util");
var jqutil = require("wed/jqutil");

function BTWDecorator(mode, meta) {
    Decorator.apply(this, Array.prototype.slice.call(arguments, 2));

    this._mode = mode;
    this._meta = meta;
    this._sense_refman = new refmans.SenseReferenceManager();
    this._section_heading_map = {
        "btw:definition": ["definition", null],
        "btw:sense": ["SENSE", this._sense_refman],
        "btw:english-renditions": ["English renditions", null],
        "btw:english-rendition": ["English rendition", null],
        "btw:semantic-fields": ["semantic categories", null]
    };
}

oop.inherit(BTWDecorator, Decorator);

BTWDecorator.prototype.init = function ($root) {
    var no_default_decoration = [
        util.classFromOriginalName("btw:entry"),
        util.classFromOriginalName("btw:lemma"),
        util.classFromOriginalName("btw:overview"),
        util.classFromOriginalName("btw:definition"),
        util.classFromOriginalName("btw:sense-discrimination"),
        util.classFromOriginalName("btw:sense"),
        util.classFromOriginalName("btw:english-renditions"),
        util.classFromOriginalName("btw:english-rendition"),
        util.classFromOriginalName("term"),
        util.classFromOriginalName("btw:semantic-fields"),
        util.classFromOriginalName("btw:sf")
    ].join(", ");

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("*"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
            var name = util.getOriginalName($el.get(0));
            switch(name) {
            case "btw:overview":
            case "btw:sense-discrimination":
                unitHeadingDecorator($root, $el);
                break;
            case "btw:definition":
            case "btw:english-renditions":
            case "btw:english-rendition":
            case "btw:semantic-fields":
                this.sectionHeadingDecorator($root, $el);
                break;
            default:
                if ($el.is(no_default_decoration))
                    return;
                this.elementDecorator($root, $el);
            }

            if (name === "btw:semantic-fields")
                this.listDecorator($el.get(0), "; ");
        }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("*"),
        function ($root, $tree, $parent, $prev, $next, $el) {
            // Skip elements which would already have been removed from
            // the tree. Unlikely but...
            if ($el.closest($root).length === 0)
                return;

            var klass = this._meta.getAdditionalClasses($el.get(0));
            if (klass.length > 0)
                $el.addClass(klass);
        }.bind(this));

    this._domlistener.addHandler(
        "children-changed",
        util.classFromOriginalName("*"),
        function ($root, $added, $removed, $prev, $next, $el) {
            if ($el.is(no_default_decoration))
                return;

            if ($added.is("._real, ._phantom_wrap") ||
                $removed.is("._real, ._phantom_wrap") ||
                $added.filter(jqutil.textFilter).length +
                $removed.filter(jqutil.textFilter).length > 0) {
                this.elementDecorator($root, $el);
                if (util.getOriginalName($el.get(0)) ===
                    "btw:semantic-fields")
                    this.listDecorator($el.get(0), "; ");
            }

        }.bind(this));

    this._domlistener.addHandler(
        "text-changed",
        util.classFromOriginalName("*"),
        function ($root, $el) {
            if ($el.is(no_default_decoration))
                return;

            this.elementDecorator($root, $el.parent());

            if (util.getOriginalName($el.get(0)) ===
                "btw:semantic-fields")
                this.listDecorator($el.get(0), "; ");
        }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:sense"),
        this.includedSenseHandler.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "included-sense",
        this.includedSenseTriggerHandler.bind(this));

    Decorator.prototype.init.apply(this, arguments);
};

BTWDecorator.prototype.elementDecorator = function ($root, $el) {
    Decorator.prototype.elementDecorator.call(
        this, $root, $el,
        util.eventHandler(this._contextMenuHandler.bind(this, true)),
        util.eventHandler(this._contextMenuHandler.bind(this, false)));
};

BTWDecorator.prototype._contextMenuHandler = function (at_start, ev, jQthis) {
    return false;
};

BTWDecorator.prototype.includedRelatedHandler = function ($root, $el) {
    headingDecorator($root, $el, "related terms");
    $el.children("._real").each(function (x, child) {
        relatedChildDecorator(child);
        this.listDecorator(child, ", ");
    }.bind(this));
};

BTWDecorator.prototype.idDecorator = function (el) {
    var $el = $(el);
    var id = $el.attr(util.encodeAttrName("xml:id"));
    var btw_id = "BTW." + id;
    $el.attr("id", btw_id);
    // Remove the old one before putting in the new one.
    if (id.indexOf("S.") === 0)
        this._sense_refman.allocateLabel(btw_id);
    else
        throw new Error("unknown type of id: " + id);
};


BTWDecorator.prototype.includedSenseHandler = function (
    $root, $tree, $parent, $prev, $next, $el) {
    var id = $el.attr(util.encodeAttrName("xml:id"));
    if (id === undefined) {
        // Give it an id.
        id = this._sense_refman.nextNumber();
        $el.attr(util.encodeAttrName("xml:id"), "S." + id);
    }
    this._domlistener.trigger("included-sense");
};

BTWDecorator.prototype.includedSenseTriggerHandler = function ($root) {
    var dec = this;
    $root.find(util.classFromOriginalName("btw:sense")).each(function () {
        var $this = $(this);
        dec.idDecorator($this);
        dec.sectionHeadingDecorator($root, $this);
    });
};

    // Override
BTWDecorator.prototype.contentDecoratorInclusionHandler = function ($root,
                                                                    $element) {
    var pair = this._mode.nodesAroundEditableContents($element.get(0));

    this._contentDecorator($root, $element, $(pair[0]), $(pair[1]));
};



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

var unit_heading_map = {
    "btw:overview": "UNIT 1: OVERVIEW",
    "btw:sense-discrimination": "UNIT 2: SENSE DISCRIMINATION"
};

function unitHeadingDecorator($root, $el) {
    var name = util.getOriginalName($el.get(0));
    var head = unit_heading_map[name];
    if (head === undefined)
        throw new Error("found an element with name " + name +
                        ", which is not handled");

    head = $('<div class="head _phantom">' + head + "</div>");
    head.attr('id', allocateHeadID());

    $el.prepend(head);
}

BTWDecorator.prototype.sectionHeadingDecorator = function ($root, $el, head) {
    if (head === undefined) {
        var name = util.getOriginalName($el.get(0));
        var head_spec = this._section_heading_map[name];
        if (head_spec === undefined)
            throw new Error("found an element with name " + name +
                            ", which is not handled");
        var refman = head_spec[1];
        if (refman) {
            // Our object must have an assigned id and a label.
            var id = $el.attr("id");
            if (!id)
                throw new Error("sectionHeadingDecorator called on element " +
                                "that does not have an id: " + $el.get(0));
            var label = refman.idToLabelForHead(id);
            head = head_spec[0] + " " + label;
        }
        else
            head = head_spec[0];
    }

    head = $('<div class="head _phantom">[' + head + "]</div>");
    head.attr('id', allocateHeadID());

    $el.prepend(head);
};

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
