define(function (require, exports, module) {
'use strict';

var Decorator = require("wed/decorator").Decorator;
var refmans = require("./btw_refmans");
var oop = require("wed/oop");
var $ = require("jquery");
var util = require("wed/util");
var jqutil = require("wed/jqutil");
var log = require("wed/log");
var input_trigger_factory = require("wed/input_trigger_factory");
var key_constants = require("wed/key_constants");
var key = require("wed/key");
var domutil = require("wed/domutil");
var transformation = require("wed/transformation");
var Transformation = transformation.Transformation;
var updater_domlistener = require("wed/updater_domlistener");
var btw_util = require("./btw_util");
var context_menu = require("wed/gui/context_menu");

var _indexOf = Array.prototype.indexOf;

function BTWDecorator(mode, meta) {
    Decorator.apply(this, Array.prototype.slice.call(arguments, 2));

    this._gui_root = this._editor.gui_root;
    this._$gui_root = $(this._gui_root);
    this._gui_domlistener =
        new updater_domlistener.Listener(this._gui_root, this._gui_updater);
    this._mode = mode;
    this._meta = meta;
    this._sense_refman = new refmans.SenseReferenceManager();
    this._example_refman = new refmans.ExampleReferenceManager();
    this._section_heading_specs = [ {
        selector: "btw:definition",
        heading: "definition"
    }, {
        selector: "btw:sense",
        heading: "SENSE",
        label_f: this._getSenseLabelForHead.bind(this)
    }, {
        selector: "btw:english-renditions",
        heading: "English renditions"
    }, {
        selector: "btw:english-rendition",
        heading: "English rendition"
    }, {
        selector: "btw:semantic-fields",
        heading: "semantic categories"
    }, {
        selector: "btw:etymology",
        heading: "etymology"
    }, {
        selector: "btw:classical-renditions",
        heading: "classical renditions"
    }, {
        selector: "btw:modern-renditions",
        heading: "modern renditions"
    }, {
        selector: "btw:explanation",
        heading: "brief explanation of sense",
        label_f: this._getSubsenseLabel.bind(this)
    }, {
        selector: "btw:citations",
        heading: "selected citations for sense",
        label_f: this._getSubsenseLabel.bind(this)
    }, {
        selector: "btw:contrastive-section",
        heading: "contrastive section for sense",
        label_f: this._getSenseLabel.bind(this)
    }, {
        selector: "btw:antonyms",
        heading: "antonyms"
    }, {
        selector: "btw:cognates",
        heading: "cognates related to sense",
        label_f: this._getSenseLabel.bind(this)
    }, {
        selector: "btw:conceptual-proximates",
        heading: "conceptual proximates"
    }, {
        selector: "btw:sense>btw:other-citations",
        heading: "other citations for sense ",
        label_f: this._getSenseLabel.bind(this)
    }, {
        selector: "btw:other-citations",
        heading: "other citations"
    }];

    // Convert the selectors to actual selectors.
    for (var s_ix = 0, spec;
         (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        spec.selector = jqutil.toDataSelector(spec.selector);
}

oop.inherit(BTWDecorator, Decorator);

BTWDecorator.prototype.init = function ($root) {
    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:sense"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.includedSenseHandler($el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:subsense"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.includedSubsenseHandler($el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("*"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.refreshElement($root, $el);
    }.bind(this));


    this._domlistener.addHandler(
        "children-changed",
        util.classFromOriginalName("*"),
        function ($root, $added, $removed, $prev, $next, $el) {
        if ($added.is("._real, ._phantom_wrap") ||
            $removed.is("._real, ._phantom_wrap") ||
            $added.filter(jqutil.textFilter).length +
            $removed.filter(jqutil.textFilter).length > 0) {
            this.refreshElement($root, $el);
        }
    }.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "included-sense",
        this.includedSenseTriggerHandler.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "included-subsense",
        this.includedSubsenseTriggerHandler.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "refresh-sense-ptrs",
        this.refreshSensePtrsHandler.bind(this));

    // Handlers for our gui_domlistener

    this._gui_domlistener.addHandler("included-element",
                                     ".head",
                                     function () {
        this._gui_domlistener.trigger("refresh-navigation-trigger");
    }.bind(this));

    this._gui_domlistener.addHandler("excluded-element",
                                     ".head",
                                     function () {
        this._gui_domlistener.trigger("refresh-navigation-trigger");
    }.bind(this));

    this._gui_domlistener.addHandler("trigger",
                                    "refresh-navigation-trigger",
                                     this._refreshNavigationHandler.bind(this));
    this._gui_domlistener.startListening();

    Decorator.prototype.init.apply(this, arguments);
    input_trigger_factory.makeSplitMergeInputTrigger(
        this._editor,
        util.classFromOriginalName("p"),
        key_constants.ENTER,
        key_constants.BACKSPACE,
        key_constants.DELETE);

    input_trigger_factory.makeSplitMergeInputTrigger(
        this._editor,
        util.classFromOriginalName("btw:sf"),
        key.makeKey(";"),
        key_constants.BACKSPACE,
        key_constants.DELETE);


};

BTWDecorator.prototype.refreshElement = function ($root, $el) {
    var no_default_decoration = [
        util.classFromOriginalName("btw:entry"),
        util.classFromOriginalName("btw:lemma"),
        util.classFromOriginalName("btw:overview"),
        util.classFromOriginalName("btw:definition"),
        util.classFromOriginalName("btw:sense-discrimination"),
        util.classFromOriginalName("btw:sense"),
        util.classFromOriginalName("btw:subsense"),
        util.classFromOriginalName("btw:english-renditions"),
        util.classFromOriginalName("btw:english-rendition"),
        util.classFromOriginalName("term"),
        util.classFromOriginalName("btw:english-term"),
        util.classFromOriginalName("btw:semantic-fields"),
        util.classFromOriginalName("btw:sf"),
        util.classFromOriginalName("btw:explanation"),
        util.classFromOriginalName("btw:citations"),
        util.classFromOriginalName("p"),
        util.classFromOriginalName("ptr"),
        util.classFromOriginalName("foreign"),
        util.classFromOriginalName("btw:renditions-and-discussions"),
        util.classFromOriginalName("btw:historico-semantical-data"),
        util.classFromOriginalName("btw:etymology"),
        util.classFromOriginalName("btw:classical-renditions"),
        util.classFromOriginalName("btw:modern-renditions"),
        util.classFromOriginalName("btw:lang"),
        util.classFromOriginalName("btw:occurrence"),
        util.classFromOriginalName("ref"),
        util.classFromOriginalName("btw:sense-emphasis"),
        util.classFromOriginalName("btw:lemma-instance"),
        util.classFromOriginalName("btw:antonym-instance"),
        util.classFromOriginalName("btw:cognate-instance"),
        util.classFromOriginalName("btw:conceptual-proximate-instance"),
        util.classFromOriginalName("btw:contrastive-section"),
        util.classFromOriginalName("btw:antonyms"),
        util.classFromOriginalName("btw:cognates"),
        util.classFromOriginalName("btw:conceptual-proximates"),
        util.classFromOriginalName("btw:other-citations")
    ].join(", ");

    // Skip elements which would already have been removed from
    // the tree. Unlikely but...
    if ($el.closest($root).length === 0)
        return;

    var klass = this._meta.getAdditionalClasses($el.get(0));
    if (klass.length > 0)
        $el.addClass(klass);

    var name = util.getOriginalName($el.get(0));
    switch(name) {
    case "btw:overview":
    case "btw:sense-discrimination":
    case "btw:renditions-and-discussions":
    case "btw:historico-semantical-data":
        unitHeadingDecorator($root, $el, this._gui_updater);
        break;
    case "btw:definition":
    case "btw:english-renditions":
    case "btw:english-rendition":
    case "btw:etymology":
    case "btw:contrastive-section":
    case "btw:antonyms":
    case "btw:cognates":
    case "btw:conceptual-proximates":
    case "btw:other-citations":
        this.sectionHeadingDecorator($root, $el, this._gui_updater);
        break;
    case "btw:semantic-fields":
    case "btw:classical-renditions":
    case "btw:modern-renditions":
        this.sectionHeadingDecorator($root, $el, this._gui_updater);
        this.listDecorator($el.get(0), "; ");
        break;
    case "btw:lang":
        includedBTWLangHandler($el);
        break;
    case "ptr":
        this.ptrDecorator($root, $el);
        break;
    case "foreign":
        languageDecorator($el);
        break;
    case "btw:authority":
        this.listDecorator($el.get(0), ", ");
        var target = $el.attr(util.encodeAttrName('target'));
        var label = target.split("/").slice(-1)[0];
        $el.prepend("<div class='_text _phantom'>" + label +
                    " </div>");
        break;
    case "ref":
        this.refDecorator($root, $el);
        break;
    case "btw:occurrence":
        $el.children("._text._phantom._occurrence_space").remove();
        var $ref = $el.children(util.classFromOriginalName("ref"));
        if ($ref.length > 0)
            $ref.before("<div class='_text _phantom _occurrence_space'> </div>");
        break;
    case "btw:example":
        this.idDecorator($el[0]);
        this.elementDecorator($root, $el);
        break;
    case "btw:cit":
        this.citDecorator($root, $el);
        break;
    case "btw:tr":
        this.trDecorator($root, $el);
        break;
    default:
        if ($el.is(no_default_decoration))
            return;
        this.elementDecorator($root, $el);
    }
};

BTWDecorator.prototype.elementDecorator = function ($root, $el) {
    Decorator.prototype.elementDecorator.call(
        this, $root, $el,
        log.wrap(this._contextMenuHandler.bind(this, true)),
        log.wrap(this._contextMenuHandler.bind(this, false)));
};

BTWDecorator.prototype.citDecorator = function ($root, $el) {
    this.elementDecorator($root, $el);
    var $ref = $el.children(util.classFromOriginalName("ref"));
    $ref.after('<div class="_phantom _text"> </div>');
};

BTWDecorator.prototype.trDecorator = function ($root, $el) {
    this.elementDecorator($root, $el);
    var $ref = $el.children(util.classFromOriginalName("ref"));
    $ref.after('<div class="_phantom _text"> </div>');
};

BTWDecorator.prototype.idDecorator = function (el) {
    var $el = $(el);
    var name = util.getOriginalName(el);
    var id = $el.attr(util.encodeAttrName("xml:id"));

    // The idDecorator is not responsible for assigning ids to
    // elements that don't have them.
    if (id === undefined)
        return;

    var wed_id = "BTW-" + id;
    $el.attr("id", wed_id);
    var refman;
    switch(name) {
    case "btw:sense":
        refman = this._sense_refman;
        break;
    case "btw:subsense":
        refman = this._getSubsenseRefman(el);
        break;
    case "btw:example":
        break;
    default:
        throw new Error("unknown element: " + name);
    }

    if (refman)
        refman.allocateLabel(wed_id);

    this._domlistener.trigger("refresh-sense-ptrs");
};

BTWDecorator.prototype.refreshSensePtrsHandler = function ($root) {
    var dec = this;
    $root.find(util.classFromOriginalName("ptr")).each(function () {
        dec.linkingDecorator($root, $(this), true);
    });
};


BTWDecorator.prototype.includedSenseHandler = function ($el) {
    var id = $el.attr(util.encodeAttrName("xml:id"));
    if (id === undefined) {
        // Give it an id.
        id = this._sense_refman.nextNumber();
        $el.attr(util.encodeAttrName("xml:id"), "S." + id);
    }
    this.idDecorator($el[0]);
    this._domlistener.trigger("included-sense");
};

BTWDecorator.prototype.includedSubsenseHandler = function ($el) {
    var id = $el.attr(util.encodeAttrName("xml:id"));
    if (id === undefined) {
        // Give it an id.
        var parent_wed_id = $el.parent().attr("id");
        var subsense_refman =
                this._sense_refman.idToSubsenseRefman(parent_wed_id);
        id = subsense_refman.nextNumber();
        $el.attr(util.encodeAttrName("xml:id"), parent_wed_id + "." + id);
    }
    this.idDecorator($el[0]);
    this._domlistener.trigger("included-subsense");
};


BTWDecorator.prototype.includedSenseTriggerHandler = function ($root) {
    var dec = this;
    this._sense_refman.deallocateAll();
    $root.find(util.classFromOriginalName("btw:sense")).each(function () {
        var $this = $(this);
        dec.idDecorator($this.get(0));
        dec.sectionHeadingDecorator($root, $this, dec._gui_updater);
    });
    this._domlistener.trigger("included-subsense");
};

BTWDecorator.prototype.includedSubsenseTriggerHandler = function ($root) {
    var dec = this;
    $root.find(util.classFromOriginalName("btw:subsense")).each(function () {
        var $subsense = $(this);
        dec.idDecorator($subsense.get(0));
        $subsense.children(util.classFromOriginalName("btw:explanation")).each(
            function () {
            var $this = $(this);
            $this.children("._phantom._text._explanation_number").remove();
            var refman = dec._getSubsenseRefman(this);
            var sublabel = refman.idToSublabel($subsense.attr("id"));
            dec._gui_updater.insertNodeAt(
                $this.get(0), 0,
                $("<div class='_phantom _text _explanation_number'>" +
                  sublabel + ". </div>").get(0));

            dec.sectionHeadingDecorator($root, $this, dec._gui_updater);
        });
        $subsense.children(util.classFromOriginalName("btw:citations")).each(
            function () {
            dec.sectionHeadingDecorator($root, $(this), dec._gui_updater);
        });
    });
};

BTWDecorator.prototype._getSenseLabelForHead = function (el) {
    var $el = $(el);
    var id = $el.attr("id");
    if (!id)
        throw new Error("element does not have an id: " + $el.get(0));
    return this._sense_refman.idToLabelForHead(id);
};

BTWDecorator.prototype._getSenseLabel = function (el) {
    var $el = $(el);
    var id = $el.closest(util.classFromOriginalName("btw:sense")).attr("id");

    if (!id)
        throw new Error("element does not have sense parent with an id: " +
                        $el.get(0));
    return this._sense_refman.idToLabel(id);
};

BTWDecorator.prototype._getSubsenseLabel = function (el) {
    var $el = $(el);
    var refman = this._getSubsenseRefman(el);

    var id = $el.closest(util.classFromOriginalName("btw:subsense")).attr("id");
    if (!id)
        throw new Error("element does not have subsense parent with an id: "
                        + $el.get(0));
    var label = refman.idToLabelForHead(id);
    return label;
};

BTWDecorator.prototype._getSubsenseRefman = function (el) {
    var $el = $(el);
    var $parent =
            $el.parents(util.classFromOriginalName("btw:sense")).first();
    var parent_wed_id = $parent.attr("id");

    return this._sense_refman.idToSubsenseRefman(parent_wed_id);
};

BTWDecorator.prototype._getRefmanForElement = function ($root, $el) {
    var name = util.getOriginalName($el.get(0));
    switch(name) {
    case "ptr":
    case "ref":
        // Find the target and return its value

        // Slice to drop the #.
        var target_id = $el.attr(util.encodeAttrName("target")).slice(1);
        var $target = $root.find('[' + util.encodeAttrName("xml:id") + '="' +
                                 target_id + '"]');
        return ($target.length === 0) ? null :
            this._getRefmanForElement($root, $target);
    case "btw:sense":
        return this._sense_refman;
    case "btw:subsense":
        var $sense = $el.
            parents(util.classFromOriginalName("btw:sense")).first();
        var id = $sense.attr("id");
        return this._sense_refman.idToSubsenseRefman(id);
    case "btw:example":
        return this._example_refman;
    default:
        throw new Error("unexpected element: " + $el);
    }
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

var next_head = 0;
function allocateHeadID() {
    return "BTW-H-" + ++next_head;
}

var unit_heading_map = {
    "btw:overview": "UNIT 1: OVERVIEW",
    "btw:sense-discrimination": "UNIT 2: SENSE DISCRIMINATION",
    "btw:historico-semantical-data": "UNIT 3: HISTORICO-SEMANTICAL DATA",
    "btw:renditions-and-discussions": "UNIT 4: RENDITIONS AND DISCUSSIONS"
};

function unitHeadingDecorator($root, $el, gui_updater) {
    $el.children('.head').remove();
    var name = util.getOriginalName($el.get(0));
    var head = unit_heading_map[name];
    if (head === undefined)
        throw new Error("found an element with name " + name +
                        ", which is not handled");

    var $head = $('<div class="head _phantom">' + head + "</div>");
    $head.attr('id', allocateHeadID());

    gui_updater.insertNodeAt($el.get(0), 0, $head.get(0));
}

BTWDecorator.prototype.sectionHeadingDecorator = function ($root, $el,
                                                           gui_updater, head) {
    $el.children('.head').remove();
    if (head === undefined) {
        var name = util.getOriginalName($el.get(0));
        for(var s_ix = 0, spec;
            (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix) {
            if ($el.is(spec.selector))
                break;
        }
        if (spec === undefined)
            throw new Error("found an element with name " + name +
                            ", which is not handled");
        var label_f = spec.label_f;
        head = (label_f) ? spec.heading + " " + label_f($el.get(0)) :
            spec.heading;
    }

    var $head = $('<div class="head _phantom">[' + head + "]</div>");
    $head.attr('id', allocateHeadID());

    gui_updater.insertNodeAt($el.get(0), 0, $head.get(0));
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
            $(this).before(sep.clone().attr('data-wed--separator-for',
                                            util.getOriginalName(el)));
        else
            first = false;
    });
}

BTWDecorator.prototype.linkingDecorator = function ($root, $el, is_ptr) {
    var dec = this;
    var orig_target = $.trim($el.attr(util.encodeAttrName("target")));
    if (orig_target === undefined)
        throw new Error("ptr element without target");

    var target;
    if (orig_target.lastIndexOf("#", 0) === 0) {
        // Internal target
        // Add BTW in front because we want the target used by wed.
        target = orig_target.replace(/#(.*)$/,'#BTW-$1');

        var $text = $('<div class="_text _phantom _linking_deco">');
        var $a = $("<a>", {"class": "_phantom", "href": target});
        $text.append($a);
        if (is_ptr) {
            // _linking_deco is used locally to make this function idempotent

            $el.children('._linking_deco').each(function () {
                dec._gui_updater.removeNode(this);
            });
            var refman = this._getRefmanForElement($root, $el);

            // Find the referred element.
            var $target = $(jQuery_escapeID(target));

            // An undefined or null refman can happen when first
            // decorating the document.
            var label;
            if (refman) {
                if (refman.name === "sense" || refman.name === "subsense") {
                    label = refman.idToLabel(target.slice(1));
                    label = label && "[" + label + "]";
                }
                else {
                    // An empty target can happen when first
                    // decorating the document.
                    if ($target.length) {
                        var data_el = this._editor.toDataNode($el[0]);
                        var data_target = this._editor.toDataNode($target[0]);
                        label = refman.getPositionalLabel($(data_el),
                                                          $(data_target),
                                                          target.slice(1));
                    }
                }
            }

            if (label === undefined)
                label = target;

            $a.text(label);

            // A ptr contains only attributes, no text, so we can just append.
            this._gui_updater.insertBefore($el.get(0), $text.get(0), null);

            if ($target.length > 0) {
                var target_name = util.getOriginalName($target.get(0));

                // Reduce the target to something sensible for tooltip text.
                if (target_name === "btw:sense")
                    $target =
                    $target.find(jqutil.toDataSelector(
                        "btw:english-rendition>btw:english-term"));
                else if (target_name === "btw:subsense")
                    $target = $target.find(util.classFromOriginalName("btw:explanation"));
                else if (target_name === "btw:example")
                    $target = $target.find(util.classFromOriginalName("ref")).first();


                $target = $target.clone();
                $target.find(".head").remove();
                $target = $("<div/>").append($target);
                $text.tooltip({"title": $target.html(), "html":
                               true, "container": "body"});
            }
        }
        else
            throw new Error("internal error: ref with unexpected target");
    }
    else {
        // External target
        var bibl_prefix = "/bibl/";
        if (orig_target.lastIndexOf(bibl_prefix, 0) === 0) {
            // Bibliographical reference...
            if (is_ptr)
                throw new Error("internal error: bibliographic "+
                                "reference recorded as ptr");

            target = orig_target.slice(bibl_prefix.length);
            $el.children("._text._phantom._ref_abbr").remove();
            $.ajax({url: this._mode._bibl_abbrev_url.replace(/<itemKey>/,
                                                             target)
                   }).done(function (data) {
                       dec._gui_updater.insertAt(
                           $el.get(0), 1,
                           $('<div class="_text _phantom _ref_abbr">' +
                             data + '</div>').get(0));
                   });
        }
    }

    if (!is_ptr) {
        $el.children("._text._phantom._ref_paren").remove();
        $el.prepend("<div class='_text _phantom _ref_paren'>(</div>");
        $el.append("<div class='_text _phantom _ref_paren'>)</div>");
    }
};

BTWDecorator.prototype.ptrDecorator = function ($root, $el) {
    this.linkingDecorator($root, $el, true);
};

BTWDecorator.prototype.refDecorator = function ($root, $el) {
    this.linkingDecorator($root, $el, false);
};

function languageDecorator($el) {
    var lang = $el.attr(util.encodeAttrName("xml:lang"));
    var prefix = lang.slice(0, 2);
    if (prefix !== "en") {
        $el.addClass("_btw_foreign");
        // $el.css("background-color", "#DFCFAF");
        // // Chinese is not commonly italicized.
        if (prefix !== "zh")
            //$el.css("font-style", "italic");
            $el.addClass("_btw_foreign_italics");

        var label = btw_util.languageCodeToLabel(lang);
        if (label === undefined)
            throw new Error("unknown language: " + lang);
        label = label.split("; ")[0];
        $el.tooltip({"title": label, "container": "body"});
    }
}


function addedIdHandler($root, $parent, $previous_sibling, $next_sibling,
                        $element) {
    var $parent = $element.parent();
    if ($parent.is(util.classFromOriginalName("sense"))) {
        var $start = $parent.children("._gui._start_button");
        $start.nextUntil($element).addBack().add($element).wrapAll("<span class='_gui _button_and_id _phantom'>");
    }
}

function includedBTWLangHandler($el) {
    var lang = $el.attr(util.encodeAttrName('btw:lang'));
    var label = btw_util.languageCodeToLabel(lang);
    if (label === undefined)
        throw new Error("unknown language: " + lang);
    // We want the abbreviation
    label = label.split("; ", 2)[1] + " ";
    $el.prepend("<div class='_text _phantom'>" + label + "</div>");
    heterogeneousListItemDecorator($el.get(0), ", ");
}


BTWDecorator.prototype._refreshNavigationHandler = function () {
    var prev_at_depth = [];
    prev_at_depth[0] = $("<li></li>");

    function getParent(depth) {
        var $parent = prev_at_depth[depth];
        if (!$parent) {
            $parent = $("<li></li>");
            prev_at_depth[depth] = $parent;
            var $grandparent = getParent(depth - 1);
            $grandparent.append($parent);
        }
        return $parent;
    }

    var $heads = this._$gui_root.find(".head");
    $heads.each(function (x, el) {
        var $el = $(el);
        // This is the list of DOM parents that do have a head
        // child, i.e. which participate in navigation.
        var $parents =
            $el.parentsUntil(this._$gui_root).filter(":has(> .head)");

        // This will never be less than 1 because the current
        // element's parent satisfies the selectors above.
        var my_depth = $parents.length;

        var $parent = $el.parent();
        var orig_name = util.getOriginalName($parent.get(0));

        var $li = $("<li class='btw-navbar-item'>"+
                    "<a class='navbar-link' href='#" + el.id +
                    "'>" + $(el).text() +
                    "</a></li>");

        // Add contextmenu handlers depending on the type of parent
        // we are dealing with.
        var $a = $li.children("a");
        $li.attr('data-wed-for', orig_name);

        // getContextualActions needs to operate on the data tree.
        var data_parent = $parent.data("wed_mirror_node");

        if (orig_name === "btw:sense" ||
            orig_name === "btw:english-rendition") {
            $a.on("contextmenu", {node: data_parent},
                  this._navigationContextMenuHandler.bind(this));
        }

        getParent(my_depth - 1).append($li);
        prev_at_depth[my_depth] = $li;

    }.bind(this));

    this._editor.$navigation_list.empty();
    this._editor.$navigation_list.append(prev_at_depth[0].children());
};

BTWDecorator.prototype._navigationContextMenuHandler = log.wrap(function (ev) {
    var node = ev.data.node;
    var orig_name = util.getOriginalName(node);
    var items = [];
    var container = node.parentNode;
    var offset = _indexOf.call(container.childNodes, node);
    var actions = this._mode.getContextualActions("insert", orig_name,
                                                  container, offset);

    var data = {element_name: orig_name};
    var triples = [];
    for(var act_ix = 0, act; (act = actions[act_ix]) !== undefined;
        ++act_ix)
        triples.push([act, data, act.getLabelFor(data) +
                      " before this one</a>"]);

    var $this_li = $(ev.currentTarget).closest("li");
    var $sense_links = $this_li.parent().find('li[data-wed-for="' + orig_name +
                                              '"]');

    if ($sense_links.length > 1) {
        // Don't add swap with prev if we are the link for the first
        // sense.
        data = {element_name: orig_name, node: node};
        if ($sense_links.first().findAndSelf(ev.currentTarget).length === 0)
            triples.push(
                [this._mode.swap_with_prev_tr, data,
                 this._mode.swap_with_prev_tr.getLabelFor(data)]);

        // Don't add swap with next if we are the link for the next
        // sense.
        if ($sense_links.last().findAndSelf(ev.currentTarget).length === 0)
            triples.push(
                [this._mode.swap_with_next_tr, data,
                 this._mode.swap_with_next_tr.getLabelFor(data)]);
    }

    for(var tix = 0, triple; (triple = triples[tix]) !== undefined; ++tix) {
        var $a = $("<a tabindex='0' href='#'>" + triple[2] + "</a>");
        $a.click(triple[1],
                 transformation.moveDataCaretFirst(this._editor,
                                                   [container, offset],
                                                   triple[0]));
        items.push($("<li></li>").append($a).get(0));
    }

    new context_menu.ContextMenu(this._editor.my_window.document,
                                 ev.pageX, ev.pageY, "none", items);

    return false;
});


exports.BTWDecorator = BTWDecorator;

});
