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
var id_manager = require("./id_manager");
var context_menu = require("wed/gui/context_menu");
var validate = require("salve/validate");
var makeDLoc = require("wed/dloc").makeDLoc;
require("./jquery.selectIn");

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
    this._sense_subsense_id_manager = new id_manager.IDManager("S.");

    this._senses_for_refresh_subsenses = [];

    // We bind them here so that we have a unique function to use.
    this._bound_getSenseLabel = this._getSenseLabel.bind(this);
    this._bound_getSubsenseLabel = this._getSubsenseLabel.bind(this);

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
        selector: "btw:sense>btw:explanation",
        heading: "brief explanation of sense",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:subsense>btw:explanation",
        heading: "brief explanation of sense",
        label_f: this._bound_getSubsenseLabel
    }, {
        selector: "btw:sense>btw:citations",
        heading: "citations for sense",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:subsense>btw:citations",
        heading: "citations for sense",
        label_f: this._bound_getSubsenseLabel
    }, {
        selector:
        "btw:antonym>btw:citations," +
            "btw:cognate>btw:citations," +
            "btw:conceptual-proximate>btw:citations",
        heading: "citations"
    },{
        selector: "btw:contrastive-section",
        heading: "contrastive section for sense",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:antonyms",
        heading: "antonyms"
    }, {
        selector: "btw:cognates",
        heading: "cognates related to sense",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:conceptual-proximates",
        heading: "conceptual proximates"
    }, {
        selector: "btw:sense>btw:other-citations",
        heading: "other citations for sense ",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:other-citations",
        heading: "other citations"
    }];

    // Convert the selectors to actual selectors.
    for (var s_ix = 0, spec;
         (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        spec.selector = jqutil.toDataSelector(spec.selector);

    this._label_levels = {};
    [
        "btw:entry",
        "btw:lemma",
        "btw:overview",
        "btw:definition",
        "btw:sense-discrimination",
        "btw:sense",
        "btw:subsense",
        "btw:english-renditions",
        "btw:english-rendition",
        "term",
        "btw:english-term",
        "btw:semantic-fields",
        "btw:sf",
        "btw:explanation",
        "btw:citations",
        "p",
        "ptr",
        "foreign",
        "btw:historico-semantical-data",
        "btw:etymology",
        "ref",
        "btw:sense-emphasis",
        "btw:lemma-instance",
        "btw:antonym-instance",
        "btw:cognate-instance",
        "btw:conceptual-proximate-instance",
        "btw:contrastive-section",
        "btw:antonyms",
        "btw:cognates",
        "btw:conceptual-proximates",
        "btw:other-citations",
        "btw:none"
    ].forEach(function (x) {
        this._label_levels[x] = 2;
    }.bind(this));

    /**
     * @private
     * @typedef VisibleAbsenceSpec
     * @type {Object}
     * @property {String} parent A jQuery selector indicating the
     * parent(s) for which to create visible absences.
     * @property {Array.<VisibleAbsenceSpecChild>} children An array
     * indicating the children for which to create visible absences.
     */

    /**
     * @private
     * @typedef VisibleAbsenceSpecChild
     * @type {Object}
     * @property {String} name The name of the child element.
     * @property {String} selector A jQuery selector corresponding to `name`.
     */

    // The following array is going to be transformed into the data
    // structure just described above.
    this._visible_absence_specs = [
        {
            parent: jqutil.toDataSelector("btw:sense"),
            children: ["btw:subsense", "btw:explanation", "btw:citations"]
        },
        {
            parent: jqutil.toDataSelector("btw:citations"),
            children: ["btw:example"]
        }
    ];

    function mapf(child) {
        return {
            name: child,
            selector: jqutil.toDataSelector(child)
        };
    }
    this._visible_absence_specs.forEach(function (spec) {
        spec.children = spec.children.map(mapf);
    });
}

oop.inherit(BTWDecorator, Decorator);

BTWDecorator.prototype.addHandlers = function () {
    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:sense"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.includedSenseHandler($el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:sense"),
        function ($root, $tree, $parent, $prev, $next, $el) {
        this.excludedSenseHandler($el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:subsense"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.includedSubsenseHandler($root, $el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:subsense"),
        function ($root, $tree, $parent, $prev, $next, $el) {
        this.excludedSubsenseHandler($root, $el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("*"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        this.refreshElement($root, $el);
    }.bind(this));

    // This is needed to handle cases when an btw:cit acquires or
    // loses Pāli text.
    this._domlistener.addHandler(
        "excluded-element",
        jqutil.toDataSelector("btw:cit foreign"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        var $cit = $el.closest(util.classFromOriginalName("btw:cit"));
        // Refresh after the element is removed.
        var dec = this;
        setTimeout(function () {
            dec.refreshElement($root, $cit);
            dec.refreshElement($root, $cit.prevAll(
                util.classFromOriginalName("btw:explanation")));
        }, 0);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        jqutil.toDataSelector("btw:cit foreign"),
        function ($root, $tree, $parent,
                  $prev, $next, $el) {
        var $cit = $el.closest(util.classFromOriginalName("btw:cit"));
        this.refreshElement($root, $cit);
        this.refreshElement($root, $cit.prevAll(
            util.classFromOriginalName("btw:explanation")));
    }.bind(this));


    this._domlistener.addHandler(
        "children-changed",
        util.classFromOriginalName("*"),
        function ($root, $added, $removed, $prev, $next, $el) {
        var removed = $removed.is("._real, ._phantom_wrap") ||
            $removed.filter(jqutil.textFilter).length;

        if ($added.is("._real, ._phantom_wrap") ||
            $added.filter(jqutil.textFilter).length && !removed)
            this.refreshElement($root, $el);

        // Refresh the element **after** the data is removed.
        if (removed)
            setTimeout(function () {
                this.refreshElement($root, $el);
            }.bind(this), 0);

    }.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "included-sense",
        this.includedSenseTriggerHandler.bind(this));

    this._domlistener.addHandler(
        "trigger",
        "refresh-subsenses",
        this.refreshSubsensesTriggerHandler.bind(this));

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

    Decorator.prototype.addHandlers.apply(this, arguments);
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

BTWDecorator.prototype.startListening = function ($root) {
    //
    // Perform general checks before we start decorating anything.
    //
    var $data_el = $($root.data("wed_mirror_node"));
    var $senses_subsenses = $data_el.find(jqutil.toDataSelector(
        "btw:sense, btw:subsense"));
    for(var i = 0, limit = $senses_subsenses.length; i < limit; ++i) {
        var $s = $senses_subsenses.eq(i);
        var id = $s.attr(util.encodeAttrName("xml:id"));
        if (id)
            this._sense_subsense_id_manager.seen(id, true);
    }

    // Call the overriden method
    Decorator.prototype.startListening.apply(this, arguments);
};

BTWDecorator.prototype.refreshElement = function ($root, $el) {
    // Skip elements which would already have been removed from
    // the tree. Unlikely but...
    if ($el.closest($root).length === 0)
        return;

    this.refreshVisibleAbsences($root, $el);

    var klass = this._meta.getAdditionalClasses($el[0]);
    if (klass.length > 0)
        $el.addClass(klass);

    var name = util.getOriginalName($el[0]);
    switch(name) {
    case "btw:overview":
    case "btw:sense-discrimination":
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
    case "btw:citations":
        this.sectionHeadingDecorator($root, $el, this._gui_updater);
        break;
    case "btw:semantic-fields":
        this.sectionHeadingDecorator($root, $el, this._gui_updater);
        this.listDecorator($el[0], "; ");
        break;
    case "ptr":
        this.ptrDecorator($root, $el);
        break;
    case "foreign":
        languageDecorator($el);
        break;
    case "ref":
        this.refDecorator($root, $el);
        break;
    case "btw:example":
        this.idDecorator($el[0]);
        break;
    case "btw:cit":
        this.citDecorator($root, $el);
        return; // citDecorator calls elementDecorator
    case "btw:tr":
        this.trDecorator($root, $el);
        return; // trDecorator calls elementDecorator
    case "btw:explanation":
        this.explanationDecorator($root, $el);
        return; // explanationDecorator calls elementDecorator
    case "btw:none":
        this.noneDecorator($root, $el);
        return; // THIS ELEMENT DOES NOT GET THE REGULAR DECORATION.
    }

    this.elementDecorator($root, $el);
};

BTWDecorator.prototype.elementDecorator = function ($root, $el) {
    var orig_name = util.getOriginalName($el[0]);
    Decorator.prototype.elementDecorator.call(
        this, $root, $el, this._label_levels[orig_name] || 1,
        log.wrap(this._contextMenuHandler.bind(this, true)),
        log.wrap(this._contextMenuHandler.bind(this, false)));
};

BTWDecorator.prototype.noneDecorator = function ($root, $el) {
    this._gui_updater.removeNodes($el.children().toArray());
    var $text = $('<div class="_phantom _text">ø</div>');
    this._gui_updater.insertBefore($el[0], $text[0], null);
};

BTWDecorator.prototype.refreshVisibleAbsences = function ($root, $el) {
    var me = this;
    $el.children("._va_instantiator").each(function () {
        me._gui_updater.removeNode(this);
    });

    var found;
    for(var i = 0, limit = this._visible_absence_specs.length; i < limit;
        ++i) {
        var spec = this._visible_absence_specs[i];
        if ($el.is(spec.parent)) {
            found = spec;
            break;
        }
    }

    if (found) {
        var node = this._editor.toDataNode($el[0]);
        var orig_errors = this._editor.validator.getErrorsFor(node);

        // Create a hash table that we can use for later tests.
        var orig_strings = Object.create(null);
        for(var oe_ix = 0, oe_limit = orig_errors.length; oe_ix < oe_limit;
            ++oe_ix)
            orig_strings[orig_errors[oe_ix].error.toString()] = true;

        var children = found.children;
        for(var child_ix = 0, child_limit = children.length;
            child_ix < child_limit; ++child_ix) {
            var child = children[child_ix];

            // We want to present controls only for children that are
            // absent!
            if ($el.children(child.selector).length)
                continue;

            var ename = this._mode._resolver.resolveName(child.name);
            var locations = this._editor.validator.possibleWhere(
                node, new validate.Event("enterStartTag", ename.ns,
                                         ename.name));

            // Narrow it down to locations where adding the element
            // won't cause a subsequent problem.
            locations = locations.filter(function (l) {
                var $clone = $(node).clone();
                var clone = $clone[0];
                var $root = $("<div>");
                $root.append(clone);
                clone.insertBefore(
                    transformation.makeElement(child.name)[0],
                    clone.childNodes[l] || null);

                var errors =
                    this._editor.validator.speculativelyValidateFragment(
                    node.parentNode,
                    _indexOf.call(node.parentNode.childNodes, node),
                    $root[0]);

                // What we are doing here is reducing the errors only
                // to those that indicate that the added element would
                // be problematic.
                errors = errors.filter(function (err) {
                    var err_msg = err.error.toString();
                    return err.node === clone &&
                        // We want only errors that were not
                        // originally present.
                        !orig_strings[err_msg] &&
                        // And that are about a tag not being allowed.
                    err_msg.lastIndexOf("tag not allowed here: ", 0) ===
                        0;
                });

                return errors.length === 0;
            }.bind(this));

            // No suitable location.
            if (!locations.length)
                continue;

            var data_loc = makeDLoc(this._editor.data_root, node,
                                    locations[0]);
            var data = {element_name: child.name,
                        move_caret_to: data_loc};
            var gui_loc = this._gui_updater.fromDataLocation(data_loc);

            // We purposely don't use getContextualActions.
            var tuples = [];
            this._mode._tr.getTagTransformations(
                "insert", child.name).forEach(
                    function (act) {
                    tuples.push([act, data, act.getLabelFor(data)]);
                });

            var $control = $(
                '<button class="_gui _phantom _va_instantiator btn btn-instantiator btn-xs" href="#">');
            // Get tooltips from the current mode
            var self = this;
            var options = {
                title: function (name) {
                    if (!self._editor.preferences.get("tooltips"))
                        return undefined;
                    return self._editor.mode.shortDescriptionFor(name);
                }.bind(undefined, child.name),
                container: $control,
                delay: { show: 1000 },
                placement: "auto top"
            };
            $control.tooltip(options);

            if (tuples.length > 1) {
                $control.html(' + ' + child.name);

                // Convert the tuples to actual menu items.
                var items = [];
                for(var tix = 0, tup; (tup = tuples[tix]) !== undefined; ++tix) {
                    var $a = $("<a tabindex='0' href='#'>" + tup[2] + "</a>");
                    $a.click(tup[1], tup[0].bound_handler);
                    $a.mousedown(false);
                    items.push($("<li></li>").append($a)[0]);
                }

                $control.click(function (ev) {
                    new context_menu.ContextMenu(
                        this._editor.my_window.document,
                        ev.clientX, ev.clientY,
                        items);
                    return false;
                }.bind(this));
            }
            else if (tuples.length === 1) {
                $control.html(tuples[0][2]);
                $control.mousedown(false);
                $control.click(tuples[0][1], function (ev) {
                    tuples[0][0].bound_terminal_handler(ev);
                    this.refreshElement($root, $el);
                }.bind(this));
            }
            this._gui_updater.insertNodeAt(gui_loc, $control[0]);
        }
    }
};

var WHEEL = "☸";

BTWDecorator.prototype.citDecorator = function ($root, $el) {
    this.elementDecorator($root, $el);
    var $ref = $el.children(util.classFromOriginalName("ref"));
    $ref.after('<div class="_phantom _text"> </div>');

    this._gui_updater.removeNodeNF(
        $el.children("._phantom._text._cit_bullet")[0]);
    if ($el.find("*[" + util.encodeAttrName("xml:lang") +
                 "='pi-Latn']").length) {
        this._gui_updater.insertNodeAt(
            $el[0], 0,
            $("<div class='_phantom _text _cit_bullet' " +
              "style='position: absolute; left: -1em'>"  +
              WHEEL + "</div>")[0]);
        $el.css("position", "relative");
    }
};

BTWDecorator.prototype.trDecorator = function ($root, $el) {
    this.elementDecorator($root, $el);
    var $ref = $el.children(util.classFromOriginalName("ref"));
    $ref.after('<div class="_phantom _text"> </div>');
};

BTWDecorator.prototype.idDecorator = function (el) {
    var $el = $(el);
    var name = util.getOriginalName(el);

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

    if (refman) {
        var wed_id = $el.attr("id");
        if (!wed_id) {
            var id = $el.attr(util.encodeAttrName("xml:id"));
            wed_id = "BTW-" + (id ||
                               this._sense_subsense_id_manager.generate());
            $el.attr("id", wed_id);
        }
        refman.allocateLabel(wed_id);
    }

    this._domlistener.trigger("refresh-sense-ptrs");
};

BTWDecorator.prototype.refreshSensePtrsHandler = function ($root) {
    var dec = this;
    $root.find(util.classFromOriginalName("ptr")).each(function () {
        dec.linkingDecorator($root, $(this), true);
    });
};


BTWDecorator.prototype.includedSenseHandler = function ($el) {
    this.idDecorator($el[0]);
    this._domlistener.trigger("included-sense");
};

BTWDecorator.prototype.excludedSenseHandler = function ($el) {
    var dec = this;
    var id = $el.attr(util.encodeAttrName("xml:id"));
    var selectors = ["*[" + util.encodeAttrName("target") + "='#" + id + "']"];

    var $subsense_links =
            $el.find(util.classFromOriginalName("btw:subsense")).each(
        function () {
        var id = $(this).attr(util.encodeAttrName("xml:id"));
        selectors.push("*[" + util.encodeAttrName("target") + "='#" + id +
                       "']");
    });

    var $links = this._editor.$data_root.find(selectors.join(","));
    for(var i = 0; i < $links.length; ++i)
        this._editor.data_updater.removeNode($links[i]);

    // Yep, we trigger the included-sense trigger.
    this._domlistener.trigger("included-sense");
};



BTWDecorator.prototype.includedSubsenseHandler = function ($root, $el) {
    var $parent = $el.parent();
    this.idDecorator($el[0]);
    this.refreshSubsensesForSense($root, $parent);
};


BTWDecorator.prototype.excludedSubsenseHandler = function ($root, $el) {
    var id = $el.attr(util.encodeAttrName("xml:id"));
    var $links = this._editor.$data_root.find(
        "*[" + util.encodeAttrName("target") + "='#" + id + "']");
    for(var i = 0; i < $links.length; ++i)
        this._editor.data_updater.removeNode($links[i]);

    var $parent = $el.parent();
    this.refreshSubsensesForSense($root, $parent);
};

BTWDecorator.prototype.includedSenseTriggerHandler = function ($root) {
    var dec = this;
    function decorateSubheader () {
        /* jshint validthis: true */
        dec.sectionHeadingDecorator($root, $(this),
                                    dec._gui_updater);
    }

    this._sense_refman.deallocateAll();
    $root.find(util.classFromOriginalName("btw:sense")).each(function () {
        var $sense = $(this);
        dec.idDecorator($sense[0]);
        dec.sectionHeadingDecorator($root, $sense, dec._gui_updater);
        // Refresh the headings that use the sense label.
        for (var s_ix = 0, spec;
             (spec = dec._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        {
            if (spec.label_f === dec._bound_getSenseLabel)
                $sense.selectIn(spec.selector).each(decorateSubheader);
        }
        dec.refreshSubsensesForSense($root, $sense);
    });
};

BTWDecorator.prototype.refreshSubsensesForSense = function ($root, $sense) {
    var sense = $sense[0];
    // The indexOf search ensures we don't put duplicates in the list.
    if (this._senses_for_refresh_subsenses.indexOf(sense) === -1) {
        this._senses_for_refresh_subsenses.push(sense);
        this._domlistener.trigger("refresh-subsenses");
    }
};

BTWDecorator.prototype.refreshSubsensesTriggerHandler = function ($root,
                                                                  $sense) {
    // Grab the list before we try to do anything.
    var senses = this._senses_for_refresh_subsenses;
    this._senses_for_refresh_subsenses = [];
    senses.forEach(function (sense) {
        this._refreshSubsensesForSense($root, $(sense));
    }.bind(this));
};

BTWDecorator.prototype._refreshSubsensesForSense = function ($root, $sense) {
    var dec = this;
    function decorateSubheader () {
        /* jshint validthis: true */
        dec.sectionHeadingDecorator($root, $(this), dec._gui_updater);
    }

    var refman = this._getSubsenseRefman($sense[0]);
    refman.deallocateAll();

    // This happens if the sense was removed from the document.
    if (!$sense.closest(this._editor.$gui_root).length)
        return;

    $sense.find(util.classFromOriginalName("btw:subsense")).each(function () {
        var $subsense = $(this);
        dec.idDecorator(this);
        dec.explanationDecorator(
            $root,
            $subsense.children(util.classFromOriginalName("btw:explanation")));

        // Refresh the headings that use the subsense label.
        for (var s_ix = 0, spec;
             (spec = dec._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        {
            if (spec.label_f === dec._bound_getSubsenseLabel)
                $subsense.selectIn(spec.selector).each(decorateSubheader);
        }
    });
};

BTWDecorator.prototype.explanationDecorator = function ($root, $el) {
    // Handle explanations that are in btw:example-explained.
    if ($el.parent(util.classFromOriginalName("btw:example-explained"))
        .length) {

        this._gui_updater.removeNodeNF(
            $el.children("._phantom._decoration_text._explanation_bullet")[0]);

        // If the next btw:cit element contains Pāli text.
        if ($el.nextAll(util.classFromOriginalName("btw:cit"))
            .find("*[" + util.encodeAttrName("xml:lang") +
                     "='pi-Latn']").length) {
            this._gui_updater.insertNodeAt(
                $el[0], 0,
                $("<div class='_phantom _decoration_text _explanation_bullet' " +
                  "style='position: absolute; left: -1em'>"  +
                  WHEEL + "</div>")[0]);
            $el.css("position", "relative");
        }
        this.elementDecorator($root, $el);
        return;
    }

    this.elementDecorator($root, $el);
    var $subsense = $el.parent(util.classFromOriginalName("btw:subsense"));
    var label;
    if ($subsense.length) {
        var refman = this._getSubsenseRefman($el[0]);
        label = refman.idToSublabel($subsense.attr("id"));
    }
    else {
        var $sense = $el.parent(util.classFromOriginalName("btw:sense"));
        label = this._sense_refman.idToLabel($sense.attr("id"));
    }
    this._gui_updater.removeNodeNF($el.children("._explanation_number")[0]);

    // We want to insert it after the start label.
    var $start = $el.children(".__start_label");
    this._gui_updater.insertBefore(
        $el[0],
        $("<div class='_phantom _decoration_text _explanation_number " +
          "_start_wrapper'>" + label + ". </div>")[0],
        $start[0] ? $start[0].nextSibling : null);

    this.sectionHeadingDecorator($root, $el, this._gui_updater);
};

BTWDecorator.prototype._getSenseLabelForHead = function (el) {
    var $el = $(el);
    var id = $el.attr("id");
    if (!id)
        throw new Error("element does not have an id: " + $el[0]);
    return this._sense_refman.idToLabelForHead(id);
};

BTWDecorator.prototype._getSenseLabel = function (el) {
    var $el = $(el);
    var id = $el.closest(util.classFromOriginalName("btw:sense")).attr("id");

    if (!id)
        throw new Error("element does not have sense parent with an id: " +
                        $el[0]);
    return this._sense_refman.idToLabel(id);
};

BTWDecorator.prototype._getSubsenseLabel = function (el) {
    var $el = $(el);
    var refman = this._getSubsenseRefman(el);

    var id = $el.closest(util.classFromOriginalName("btw:subsense")).attr("id");
    if (!id)
        // This can happen during the decoration of the tree because
        // there is in general no guarantee about the order in which
        // elements are decorated. A second pass will ensure that the
        // label is not undefined.
        return undefined;
    var label = refman.idToLabelForHead(id);
    return label;
};


/**
 * @param {Node} el The element for which we want the subsense
 * reference manager. This element must be a child of a btw:sense
 * element or a btw:sense element.
 * @returns {module:btw_refmans~SubsenseReferenceManager} The subsense
 * reference manager.
 */
BTWDecorator.prototype._getSubsenseRefman = function (el) {
    var $el = $(el);
    var $sense = $el.is(util.classFromOriginalName("btw:sense")) ?
            $el :
            $el.parents(util.classFromOriginalName("btw:sense")).first();
    var parent_wed_id = $sense.attr("id");

    return this._sense_refman.idToSubsenseRefman(parent_wed_id);
};

BTWDecorator.prototype._getRefmanForElement = function ($root, $el) {
    var name = util.getOriginalName($el[0]);
    switch(name) {
    case "ptr":
    case "ref":
        // Find the target and return its value

        // Slice to drop the #.
        var target_id = $el.attr(util.encodeAttrName("target")).slice(1);
        var $target = $root.find('[id="' + "BTW-" + target_id + '"]');
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
    var pair = this._mode.nodesAroundEditableContents($element[0]);

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
    "btw:historico-semantical-data": "UNIT 3: HISTORICO-SEMANTICAL DATA"
};

function unitHeadingDecorator($root, $el, gui_updater) {
    $el.children('.head').remove();
    var name = util.getOriginalName($el[0]);
    var head = unit_heading_map[name];
    if (head === undefined)
        throw new Error("found an element with name " + name +
                        ", which is not handled");

    var $head = $('<div class="head _phantom _start_wrapper">' + head +
                  "</div>");
    $head.attr('id', allocateHeadID());

    gui_updater.insertNodeAt($el[0], 0, $head[0]);
}

BTWDecorator.prototype.sectionHeadingDecorator = function ($root, $el,
                                                           gui_updater, head) {
    $el.children('.head').remove();
    if (head === undefined) {
        var name = util.getOriginalName($el[0]);
        for(var s_ix = 0, spec;
            (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix) {
            if ($el.is(spec.selector))
                break;
        }
        if (spec === undefined)
            throw new Error("found an element with name " + name +
                            ", which is not handled");
        var label_f = spec.label_f;
        head = (label_f) ? spec.heading + " " + label_f($el[0]) : spec.heading;
    }

    var $head = $('<div class="head _phantom _start_wrapper">[' + head +
                  "]</div>");
    $head.attr('id', allocateHeadID());

    gui_updater.insertNodeAt($el[0], 0, $head[0]);
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

function setTitle($el, data) {
    var creators = data.creators;
    var first_creator = "***ITEM HAS NO CREATORS***";
    if (creators)
        first_creator = creators.split(",")[0];

    var title = first_creator + ", " + data.title;
    var date = data.date;
    if (date)
        title += ", " + date;

    $el.tooltip({"title": title, container: "body"});
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
            this._gui_updater.insertBefore($el[0], $text[0], null);

            if ($target.length > 0) {
                var target_name = util.getOriginalName($target[0]);

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
        var bibl_prefix = "/bibliography/";
        if (orig_target.lastIndexOf(bibl_prefix, 0) === 0) {
            // Bibliographical reference...
            if (is_ptr)
                throw new Error("internal error: bibliographic "+
                                "reference recorded as ptr");

            target = orig_target;

            // It is okay to skip the tree updater for these operations.
            $el.children("._ref_abbr, ._ref_paren").each(
                function () {
                dec._gui_updater.removeNode(this);
            });

            var start = [
                "<div class='_phantom _decoration_text _ref_paren " +
                    "_open_ref_paren _start_wrapper'>(</div>",
                '<div class="_text _phantom _ref_abbr"></div>'
            ];

            var el = $el[0];
            // Start from the end and insert before the first child.
            for(var start_ix = start.length - 1; start_ix >= 0; --start_ix)
                dec._gui_updater.insertBefore(el, $(start[start_ix])[0],
                                              el.firstChild);
            dec._gui_updater.insertBefore(
                el, $("<div class='_phantom _decoration_text " +
                      "_ref_paren _close_ref_paren _end_wrapper'>)</div>")[0]);


            var ref_abbr = $el.children("._ref_abbr")[0];
            $.ajax({
                url: target,
                headers: {
                    Accept: "application/json"
                }
            }).done(function (data) {
                var text = "";

                if (data.reference_title) {
                    text = data.reference_title;
                    setTitle($el, data.item);
                }
                else {
                    var creators = data.creators;
                    text = "***ITEM HAS NO CREATORS***";
                    if (creators)
                        text = creators.split(",")[0];

                    if (data.date)
                        text += ", " + data.date;
                    setTitle($el, data);
                }


                dec._gui_updater.insertText(ref_abbr, 0, text);
                $el.trigger("wed-refresh");

            }).fail(function () {
                dec._gui_updater.insertText(ref_abbr, 0, "NON-EXISTENT");
                $el.trigger("wed-refresh");
            });
        }
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
        var orig_name = util.getOriginalName($parent[0]);

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
            orig_name === "btw:english-rendition" ||
            orig_name === "btw:explanation") {
            if (orig_name === "btw:explanation")
                data_parent = $(data_parent).parent(
                    util.classFromOriginalName("btw:subsense"))[0];
            $a.on("contextmenu", {node: data_parent},
                  this._navigationContextMenuHandler.bind(this));
            $el.on("wed-context-menu", {node: data_parent},
                   this._navigationContextMenuHandler.bind(this));
            $el.data("wed-custom-context-menu", true);
        }

        getParent(my_depth - 1).append($li);
        prev_at_depth[my_depth] = $li;

    }.bind(this));

    this._editor.$navigation_list.empty();
    this._editor.$navigation_list.append(prev_at_depth[0].children());
};

BTWDecorator.prototype._navigationContextMenuHandler = log.wrap(
    function (wed_ev, ev) {
    // ev is undefined if called from the context menu. In this case,
    // wed_ev contains all that we want.
    if (!ev)
        ev = wed_ev;
    // node is the node in the data tree which corresponds to the
    // navigation item for which a context menu handler was required
    // by the user.
    var node = wed_ev.data.node;
    var orig_name = util.getOriginalName(node);

    // container, offset: location of the node in its parent.
    var container = node.parentNode;
    var offset = _indexOf.call(container.childNodes, node);

    // List of items to put in the contextual menu.
    var tuples = [];

    //
    // Create "insert" transformations for siblings that could be
    // inserted before this node.
    //
    var actions = this._mode.getContextualActions("insert", orig_name,
                                                  container, offset);
    // data to pass to transformations
    var data = {element_name: orig_name,
                move_caret_to: makeDLoc(this._editor.data_root,
                                        container, offset)};
    var act_ix, act;
    for(act_ix = 0, act; (act = actions[act_ix]) !== undefined; ++act_ix)
        tuples.push([act, data, act.getLabelFor(data) +
                     " before this one"]);

    //
    // Create "insert" transformations for siblings that could be
    // inserted after this node.
    //
    actions = this._mode.getContextualActions("insert", orig_name,
                                              container, offset + 1);

    data = {element_name: orig_name, move_caret_to: makeDLoc(
        this._editor.data_root, container, offset + 1)};
    for(act_ix = 0, act; (act = actions[act_ix]) !== undefined; ++act_ix)
        tuples.push([act, data,
                     act.getLabelFor(data) + " after this one"]);

    var $this_li = $(ev.currentTarget).closest("li");
    var $sibling_links = $this_li.parent().find('li[data-wed-for="' +
                                                orig_name + '"]');

    // If the node has siblings we potentially add swap with previous
    // and swap with next.
    if ($sibling_links.length > 1) {
        // However, don't add swap with prev if we are first.
        data = {element_name: orig_name, node: node,
                move_caret_to: makeDLoc(this._editor.data_root,
                                        container, offset)};
        if ($sibling_links.first().findAndSelf(ev.currentTarget).length === 0)
            tuples.push(
                [this._mode.swap_with_prev_tr, data,
                 this._mode.swap_with_prev_tr.getLabelFor(data)]);

        // Don't add swap with next if we are last.
        if ($sibling_links.last().findAndSelf(ev.currentTarget).length === 0)
            tuples.push(
                [this._mode.swap_with_next_tr, data,
                 this._mode.swap_with_next_tr.getLabelFor(data)]);
    }

    // Delete the node
    data = {node: node, element_name: orig_name,
            move_caret_to: makeDLoc(this._editor.data_root, node, 0)};
    this._mode._tr.getTagTransformations(
        "delete-element", orig_name).forEach(function (act) {
            tuples.push([act, data, act.getLabelFor(data)]);
        });

    // Senses get an additional menu item to insert a subsense.
    if (orig_name === "btw:sense" &&
        $(node).children(util.classFromOriginalName("btw:subsense")).length ===
        0) {
        // We want to know where "btw:subsense" is valid.
        var ename = this._mode._resolver.resolveName("btw:subsense");
        var locations = this._editor.validator.possibleWhere(
            node,
            new validate.Event("enterStartTag", ename.ns, ename.name));

        data = {element_name: "btw:subsense",
                move_caret_to: makeDLoc(this._editor.data_root, node,
                                        locations[0])};
        // We purposely don't use getContextualActions.
        this._mode._tr.getTagTransformations(
            "insert", "btw:subsense").forEach(
                function (act) {
                tuples.push([act, data, act.getLabelFor(data)]);
            });
    }

    // Convert the tuples to actual menu items.
    var items = [];
    for(var tix = 0, tup; (tup = tuples[tix]) !== undefined; ++tix) {
        var $a = $("<a tabindex='0' href='#'>" + tup[2] + "</a>");
        $a.mousedown(false);
        $a.click(tup[1], tup[0].bound_handler);
        items.push($("<li></li>").append($a)[0]);
    }

    new context_menu.ContextMenu(this._editor.my_window.document,
                                 ev.clientX, ev.clientY, items);

    return false;
});


exports.BTWDecorator = BTWDecorator;

});
