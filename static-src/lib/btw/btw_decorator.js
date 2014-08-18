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
var updater_domlistener = require("wed/updater_domlistener");
var btw_util = require("./btw_util");
var id_manager = require("./id_manager");
var context_menu = require("wed/gui/context_menu");
var tooltip = require("wed/gui/tooltip").tooltip;
var validate = require("salve/validate");
var makeDLoc = require("wed/dloc").makeDLoc;
require("wed/jquery.findandself");
var closestByClass = domutil.closestByClass;
var closest = domutil.closest;

var _indexOf = Array.prototype.indexOf;

function BTWDecorator(mode, meta) {
    Decorator.apply(this, Array.prototype.slice.call(arguments, 2));

    this._gui_root = this._editor.gui_root;
    this._gui_domlistener =
        new updater_domlistener.Listener(this._gui_root, this._gui_updater);
    this._mode = mode;
    this._meta = meta;
    this._sense_refman = new refmans.SenseReferenceManager();
    this._example_refman = new refmans.ExampleReferenceManager();
    this._sense_subsense_id_manager = new id_manager.IDManager("S.");
    this._example_id_manager = new id_manager.IDManager("E.");

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
        heading: "cognates"
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
        "btw:term",
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
     * @property {Array.<String>} children An array
     * indicating the children for which to create visible absences.
     */

    // The following array is going to be transformed into the data
    // structure just described above.
    this._visible_absence_specs = [
        {
            parent: jqutil.toDataSelector("btw:sense"),
            children: ["btw:subsense", "btw:explanation",
                       "btw:semantic-fields", "btw:citations",
                       "btw:other-citations", "btw:contrastive-section"]
        },
        {
            parent: jqutil.toDataSelector("btw:citations"),
            children: ["btw:example"]
        },
        {
            parent: jqutil.toDataSelector(
                "btw:subsense, btw:antonym, btw:cognate, "+
                    "btw:conceptual-proximate"),
            children: ["btw:other-citations"]
        }
    ];

}

oop.inherit(BTWDecorator, Decorator);

BTWDecorator.prototype.addHandlers = function () {
    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:sense"),
        function (root, tree, parent, prev, next, el) {
        this.includedSenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:sense"),
        function (root, tree, parent, prev, next, el) {
        this.excludedSenseHandler(el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:subsense"),
        function (root, tree, parent, prev, next, el) {
        this.includedSubsenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:subsense"),
        function (root, tree, parent, prev, next, el) {
        this.excludedSubsenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:example, btw:example-explained"),
        function (root, tree, parent, prev, next, el) {
        this.excludedExampleHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "children-changed",
        jqutil.toDataSelector("ref, ref *"),
        function (root, added, removed, prev, next, el) {
        this._refChangedInGUI(root, closestByClass(el, "ref", root));
    }.bind(this));

    this._gui_domlistener.addHandler(
        "text-changed",
        jqutil.toDataSelector("ref, ref *"),
        function (root, el) {
        this._refChangedInGUI(root, closestByClass(el, "ref", root));
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("*"),
        function (root, tree, parent, prev, next, el) {
        this.refreshElement(root, el);
    }.bind(this));

    // This is needed to handle cases when an btw:cit acquires or
    // loses Pāli text.
    this._domlistener.addHandler(
        "excluded-element",
        jqutil.toDataSelector("btw:cit foreign"),
        function (root, tree, parent, prev, next, el) {
        var cit = closestByClass(el, "btw:cit", root);
        // Refresh after the element is removed.
        var dec = this;
        setTimeout(function () {
            dec.refreshElement(root, cit);
            dec.refreshElement(root, domutil.siblingByClass(
                cit, "btw:explanation"));
        }, 0);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        jqutil.toDataSelector("btw:cit foreign"),
        function (root, tree, parent, prev, next, el) {
        var cit = closestByClass(el, "btw:cit", root);
        this.refreshElement(root, cit);
        this.refreshElement(root, domutil.siblingByClass(
            cit, "btw:explanation"));
    }.bind(this));


    this._domlistener.addHandler(
        "children-changed",
        util.classFromOriginalName("*"),
        function (root, added, removed, prev, next, el) {
        var removed_flag = false;
        var i, r;
        for(i = 0; !removed_flag && (r = removed[i]) !== undefined; ++i)
            removed_flag = r.nodeType === Node.TEXT_NODE ||
                r.classList.contains("_real") ||
                r.classList.contains("_phantom_wrap");

        if (!removed_flag) {
            var added_flag = false;
            for(i = 0; !added_flag && (r = added[i]) !== undefined; ++i)
                added_flag = r.nodeType === Node.TEXT_NODE ||
                r.classList.contains("_real") ||
                r.classList.contains("_phantom_wrap");

            if (added_flag)
                this.refreshElement(root, el);
        }
        else
            // Refresh the element **after** the data is removed.
            setTimeout(function () {
                this.refreshElement(root, el);
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
    var i, limit, id;

    var data_el = $root.data("wed_mirror_node");
    var senses_subsenses = data_el.querySelectorAll(jqutil.toDataSelector(
        "btw:sense, btw:subsense"));
    for(i = 0, limit = senses_subsenses.length; i < limit; ++i) {
        var s = senses_subsenses[i];
        id = s.getAttribute(util.encodeAttrName("xml:id"));
        if (id)
            this._sense_subsense_id_manager.seen(id, true);
    }

    var examples = data_el.querySelectorAll(jqutil.toDataSelector(
        "btw:example, btw:example-explained"));
    for(i = 0, limit = examples.length; i < limit; ++i) {
        var ex = examples[i];
        id = ex.getAttribute(util.encodeAttrName("xml:id"));
        if (id)
            this._example_id_manager.seen(id, true);
    }

    // Call the overriden method
    Decorator.prototype.startListening.apply(this, arguments);
};

BTWDecorator.prototype.refreshElement = function (root, el) {
    // Skip elements which would already have been removed from
    // the tree. Unlikely but...
    if (!root.contains(el))
        return;

    this.refreshVisibleAbsences(root, el);

    var klass = this._meta.getAdditionalClasses(el);
    if (klass.length)
        el.className += " " + klass;

    var name = util.getOriginalName(el);
    var skip_default = false;
    switch(name) {
    case "btw:overview":
    case "btw:sense-discrimination":
    case "btw:historico-semantical-data":
        unitHeadingDecorator(root, el, this._gui_updater);
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
        this.sectionHeadingDecorator(root, el, this._gui_updater);
        break;
    case "btw:semantic-fields":
        this.sectionHeadingDecorator(root, el, this._gui_updater);
        this.listDecorator(el, "; ");
        break;
    case "ptr":
        this.ptrDecorator(root, el);
        break;
    case "foreign":
        languageDecorator(el);
        break;
    case "ref":
        this.refDecorator(root, el);
        break;
    case "btw:example":
        this.idDecorator(root, el);
        break;
    case "btw:cit":
        this.citDecorator(root, el);
        skip_default = true; // citDecorator calls elementDecorator
        break;
    case "btw:explanation":
        this.explanationDecorator(root, el);
        skip_default = true; // explanationDecorator calls elementDecorator
        break;
    case "btw:none":
        this.noneDecorator(root, el);
        // THIS ELEMENT DOES NOT GET THE REGULAR DECORATION.
        skip_default = true;
        break;
    }

    if (!skip_default)
        this.elementDecorator(root, el);

    //
    // This mode makes the validator work while it is decorating the
    // GUI tree. Therefore, the position of errors *can* be erroneous
    // when these errors are generated while the GUI tree is being
    // decorated. So we need to restart the validation to fix the
    // erroneous error markers.
    //
    // We want to do it only if there *are* validation errors in this
    // element.
    //
    var error = false;
    var child = el.firstElementChild;
    while(child) {
        error = child.classList.contains("wed-validation-error");
        if (error)
            break;

        child = child.nextElementSibling;
    }

    if (error)
        this._editor.validator.restartAt($.data(el, "wed-mirror-node"));
};

BTWDecorator.prototype.elementDecorator = function (root, el) {
    var orig_name = util.getOriginalName(el);
    Decorator.prototype.elementDecorator.call(
        this, root, el, this._label_levels[orig_name] || 1,
        log.wrap(this._contextMenuHandler.bind(this, true)),
        log.wrap(this._contextMenuHandler.bind(this, false)));
};

BTWDecorator.prototype.noneDecorator = function (root, el) {
    this._gui_updater.removeNodes(el.childNodes);
    var text = el.ownerDocument.createElement("div");
    text.className = "_text _phantom";
    text.innerHTML = "ø";
    this._gui_updater.insertBefore(el, text, null);
};

BTWDecorator.prototype.refreshVisibleAbsences = function (root, el) {
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("_va_instantiator"))
            this._gui_updater.removeNode(child);
        child = next;
    }

    var found, spec;
    for(var i = 0, limit = this._visible_absence_specs.length; i < limit;
        ++i) {
        spec = this._visible_absence_specs[i];
        if (el.matches(spec.parent)) {
            found = spec;
            break;
        }
    }

    if (found) {
        var node = this._editor.toDataNode(el);
        var orig_errors = this._editor.validator.getErrorsFor(node);

        // Create a hash table that we can use for later tests.
        var orig_strings = Object.create(null);
        for(var oe_ix = 0, oe_limit = orig_errors.length; oe_ix < oe_limit;
            ++oe_ix)
            orig_strings[orig_errors[oe_ix].error.toString()] = true;

        var children = found.children;
        spec_loop:
        for(var spec_ix = 0, spec_limit = children.length;
            spec_ix < spec_limit; ++spec_ix) {
            spec = children[spec_ix];

            // We want to present controls only for children that are
            // absent!
            child = el.firstElementChild;
            while(child) {
                if (child.classList.contains(spec))
                    continue spec_loop;
                child = child.nextElementSibling;
            }

            var ename = this._mode._resolver.resolveName(spec);
            var locations = this._editor.validator.possibleWhere(
                node, new validate.Event("enterStartTag", ename.ns,
                                         ename.name));

            // Narrow it down to locations where adding the element
            // won't cause a subsequent problem.
            var filtered_locations = [];
            location_loop:
            for(var lix = 0, l; (l = locations[lix]) !== undefined; ++lix) {
                var clone = node.cloneNode(true);
                var div = clone.ownerDocument.createElement("div");
                div.appendChild(clone);
                clone.insertBefore(transformation.makeElement(spec),
                                   clone.childNodes[l] || null);

                var errors =
                    this._editor.validator.speculativelyValidateFragment(
                        node.parentNode,
                        _indexOf.call(node.parentNode.childNodes, node), div);

                // What we are doing here is reducing the errors only
                // to those that indicate that the added element would
                // be problematic.
                for(var eix = 0, err; (err = errors[eix]) !== undefined;
                    ++eix) {
                    var err_msg = err.error.toString();
                    if (err.node === clone &&
                        // We want only errors that were not
                        // originally present.
                        !orig_strings[err_msg] &&
                        // And that are about a tag not being allowed.
                        err_msg.lastIndexOf("tag not allowed here: ", 0) ===
                        0)
                        // There's nothing to be done with this location.
                        break location_loop;
                }

                filtered_locations.push(l);
            }
            locations = filtered_locations;

            // No suitable location.
            if (!locations.length)
                continue;

            var data_loc = makeDLoc(this._editor.data_root, node, locations[0]);
            var data = {name: spec, move_caret_to: data_loc};
            var gui_loc = this._gui_updater.fromDataLocation(data_loc);

            var tuples = [];
            this._mode.getContextualActions(
                "insert", spec, node, locations[0]).forEach(
                    function (act) {
                    tuples.push([act, data, act.getLabelFor(data)]);
                });

            var control = el.ownerDocument.createElement("button");
            control.className = "_gui _phantom _va_instantiator btn " +
                "btn-instantiator btn-xs";
            control.setAttribute("href", "#");
            var $control = $(control);
            // Get tooltips from the current mode
            var self = this;
            var options = {
                title: function (name) {
                    if (!self._editor.preferences.get("tooltips"))
                        return undefined;
                    return self._editor.mode.shortDescriptionFor(name);
                }.bind(undefined, spec),
                container: $control,
                delay: { show: 1000 },
                placement: "auto top"
            };
            tooltip($control, options);

            if (tuples.length > 1) {
                control.innerHTML = ' + ' + spec;

                // Convert the tuples to actual menu items.
                var items = [];
                for(var tix = 0, tup; (tup = tuples[tix]) !== undefined; ++tix) {
                    var li = el.ownerDocument.createElement("li");
                    li.innerHTML = "<a tabindex='0' href='#'>" + tup[2] +
                        "</a>";
                    var $a = $(li.firstChild);
                    $a.click(tup[1], tup[0].bound_handler);
                    $a.mousedown(false);
                    items.push(li);
                }

                $control.click(function (ev) {
                    if (this._editor.getGUICaret() === undefined)
                        this._editor.setGUICaret(gui_loc);
                    new context_menu.ContextMenu(
                        this._editor.my_window.document,
                        ev.clientX, ev.clientY,
                        items);
                    return false;
                }.bind(this));
            }
            else if (tuples.length === 1) {
                control.innerHTML = tuples[0][2];
                $control.mousedown(false);
                $control.click(tuples[0][1], function (ev) {
                    if (this._editor.getDataCaret() === undefined)
                        this._editor.setDataCaret(data_loc);
                    tuples[0][0].bound_terminal_handler(ev);
                    this.refreshElement(root, el);
                }.bind(this));
            }
            this._gui_updater.insertNodeAt(gui_loc, control);
        }
    }
};

var WHEEL = "☸";

BTWDecorator.prototype.citDecorator = function (root, el) {
    this.elementDecorator(root, el);

    var ref;
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("_ref_space") ||
            child.classList.contains("_cit_bullet"))
            this._gui_updater.removeNode(child);
        else if (child.classList.contains("ref"))
            ref = child;
        child = next;
    }

    if (ref) {
        var space = el.ownerDocument.createElement("div");
        space.className = "_text _phantom _ref_space";
        space.innerHTML = " ";
        el.insertBefore(space, ref.nextSibling);
    }

    if (el.querySelector("*[" + util.encodeAttrName("xml:lang") +
                 "='pi-Latn']")) {
        var div = el.ownerDocument.createElement("div");
        div.className = "_phantom _text _cit_bullet";
        div.style.position = "absolute";
        div.style.left = "-1em";
        div.textContent = WHEEL;
        this._gui_updater.insertNodeAt(el, 0, div);
        el.style.position = "relative";
    }
};

BTWDecorator.prototype.idDecorator = function (root, el) {
    var name = util.getOriginalName(el);

    var refman = this._getRefmanForElement(root, el);
    if (refman) {
        var wed_id = el.id;
        if (!wed_id) {
            var id = el.getAttribute(util.encodeAttrName("xml:id"));
            var id_man = this._getIDManagerForRefman(refman);
            wed_id = "BTW-" + (id || id_man.generate());
            el.id = wed_id;
        }

        // We have some reference managers that don't derive from
        // ReferenceManager and thus do not have this method.
        if (refman.allocateLabel)
            refman.allocateLabel(wed_id);
    }

    this._domlistener.trigger("refresh-sense-ptrs");
};

BTWDecorator.prototype.refreshSensePtrsHandler = function (root) {
    var ptrs = root.getElementsByClassName("ptr");
    for(var i = 0, ptr; (ptr = ptrs[i]) !== undefined; ++i)
        this.linkingDecorator(root, ptr, true);
};


BTWDecorator.prototype.includedSenseHandler = function (root, el) {
    this.idDecorator(root, el);
    this._domlistener.trigger("included-sense");
};

BTWDecorator.prototype.excludedSenseHandler = function (el) {
    this._deleteLinksPointingTo(el);
    // Yep, we trigger the included-sense trigger.
    this._domlistener.trigger("included-sense");
};



BTWDecorator.prototype.includedSubsenseHandler = function (root, el) {
    this.idDecorator(root, el);
    this.refreshSubsensesForSense(root, el.parentNode);
};


BTWDecorator.prototype.excludedSubsenseHandler = function (root, el) {
    this._deleteLinksPointingTo(el);
    this.refreshSubsensesForSense(root, el.parentNode);
};

BTWDecorator.prototype._deleteLinksPointingTo = function (el) {
    var id = el.getAttribute(util.encodeAttrName("xml:id"));
    var selector = ["*[" + util.encodeAttrName("target") + "='#" + id + "']"];

    var links = this._editor.data_root.querySelectorAll(selector);
    for(var i = 0; i < links.length; ++i)
        this._editor.data_updater.removeNode(links[i]);
};

BTWDecorator.prototype.excludedExampleHandler = function (root, el) {
    this._deleteLinksPointingTo(el);
};

BTWDecorator.prototype.includedSenseTriggerHandler = function (root) {
    this._sense_refman.deallocateAll();
    var senses = root.getElementsByClassName("btw:sense");
    for(var i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        this.idDecorator(root, sense);
        this.sectionHeadingDecorator(root, sense, this._gui_updater);
        // Refresh the headings that use the sense label.
        for (var s_ix = 0, spec;
             (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        {
            if (spec.label_f === this._bound_getSenseLabel) {
                var subheaders = sense.querySelectorAll(spec.selector);
                for(var shix = 0, sh; (sh = subheaders[shix]) !== undefined;
                    ++shix)
                    this.sectionHeadingDecorator(root, sh, this._gui_updater);
            }
        }
        this.refreshSubsensesForSense(root, sense);
    }
};

BTWDecorator.prototype.refreshSubsensesForSense = function (root, sense) {
    // The indexOf search ensures we don't put duplicates in the list.
    if (this._senses_for_refresh_subsenses.indexOf(sense) === -1) {
        this._senses_for_refresh_subsenses.push(sense);
        this._domlistener.trigger("refresh-subsenses");
    }
};

BTWDecorator.prototype.refreshSubsensesTriggerHandler = function (root) {
    // Grab the list before we try to do anything.
    var senses = this._senses_for_refresh_subsenses;
    this._senses_for_refresh_subsenses = [];
    senses.forEach(function (sense) {
        this._refreshSubsensesForSense(root, sense);
    }.bind(this));
};

BTWDecorator.prototype._refreshSubsensesForSense = function (root, sense) {
    var refman = this._getSubsenseRefman(sense);
    refman.deallocateAll();

    // This happens if the sense was removed from the document.
    if (!this._editor.gui_root.contains(sense))
        return;

    var subsenses = sense.getElementsByClassName("btw:subsense");
    for(var i = 0, subsense; (subsense = subsenses[i]) !== undefined; ++i) {
        var explanation;
        var child = subsenses.firstElementChild;
        while(child) {
            if (child.classList.contains("btw:explanation")) {
                explanation = child;
                break;
            }
            child = child.nextElementSibling;
        }

        this.idDecorator(root, subsense);
        if (explanation)
            this.explanationDecorator(root, explanation);

        // Refresh the headings that use the subsense label.
        for (var s_ix = 0, spec;
             (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix)
        {
            if (spec.label_f === this._bound_getSubsenseLabel) {
                var subheaders = subsense.querySelectorAll(spec.selector);
                for(var shix = 0, sh; (sh = subheaders[shix]) !== undefined;
                    ++shix)
                    this.sectionHeadingDecorator(root, sh, this._gui_updater);
            }
        }
    }
};

BTWDecorator.prototype.explanationDecorator = function (root, el) {
    var child, next, div; // Damn hoisting...
    // Handle explanations that are in btw:example-explained.
    if (el.parentNode.classList.contains("btw:example-explained")) {
        child = el.firstElementChild;
        while(child) {
            next = child.nextElementSibling;
            if (child.classList.contains("_explanation_bullet")) {
                this._gui_updater.removeNode(child);
                break; // There's only one.
            }
            child = next;
        }

        var cit = el.nextElementSibling;
        // If the next btw:cit element contains Pāli text.
        if (cit.classList.contains("btw:cit") &&
            cit.querySelector("*[" + util.encodeAttrName("xml:lang") +
                              "='pi-Latn']")) {
            div = el.ownerDocument.createElement("div");
            div.className = "_phantom _decoration_text _explanation_bullet";
            div.style.position = "absolute";
            div.style.left = "-1em";
            div.textContent = WHEEL;
            this._gui_updater.insertNodeAt(el, 0, div);
            el.style.position = "relative";
        }
        this.elementDecorator(root, el);
        return;
    }

    this.elementDecorator(root, el);
    var label;
    var parent = el.parentNode;
    // Is it in a subsense?
    if (parent.classList.contains("btw:subsense")) {
        var refman = this._getSubsenseRefman(el);
        label = refman.idToSublabel(parent.id);
        child = el.firstElementChild;
        var start;
        while(child) {
            next = child.nextElementSibling;
            if (child.classList.contains("_explanation_number"))
                this._gui_updater.removeNode(child);
            else if (child.classList.contains("__start_label"))
                start = child;
            child = next;
        }

        // We want to insert it after the start label.
        div = el.ownerDocument.createElement("div");
        div.className = "_phantom _decoration_text _explanation_number " +
            "_start_wrapper'";
        div.textContent = label + ". ";
        this._gui_updater.insertBefore(el, div,
                                       start ? start.nextSibling : null);

    }
    this.sectionHeadingDecorator(root, el, this._gui_updater);
};

BTWDecorator.prototype._getSenseLabelForHead = function (el) {
    var id = el.id;
    if (!id)
        throw new Error("element does not have an id: " + el);
    return this._sense_refman.idToLabelForHead(id);
};

BTWDecorator.prototype._getSenseLabel = function (el) {
    var what = el;
    var sense;
    while(what) {
        if (what.classList.contains("btw:sense")) {
            sense = what;
            break;
        }
        what = what.parentNode;
    }

    var id = sense && sense.id;

    if (!id)
        throw new Error("element does not have sense parent with an id: " + el);
    return this._sense_refman.idToLabel(id);
};

BTWDecorator.prototype._getSubsenseLabel = function (el) {
    var refman = this._getSubsenseRefman(el);

    var what = el;
    var subsense;
    while(what) {
        if (what.classList.contains("btw:subsense")) {
            subsense = what;
            break;
        }
        what = what.parentNode;
    }

    var id = subsense && subsense.id;
    if (!id)
        // This can happen during the decoration of the tree because
        // there is in general no guarantee about the order in which
        // elements are decorated. A second pass will ensure that the
        // label is not undefined.
        return undefined;
    var label = refman.idToLabelForHead(id);
    return label;
};

function closestSense(el) {
    var what = el;
    var sense;
    while(what) {
        if (what.classList.contains("btw:sense")) {
            sense = what;
            break;
        }
        what = what.parentNode;
    }

    return sense;
}

/**
 * @param {Node} el The element for which we want the subsense
 * reference manager. This element must be a child of a btw:sense
 * element or a btw:sense element.
 * @returns {module:btw_refmans~SubsenseReferenceManager} The subsense
 * reference manager.
 */
BTWDecorator.prototype._getSubsenseRefman = function (el) {
    var sense = closestSense(el);
    var id = sense && sense.id;
    return this._sense_refman.idToSubsenseRefman(id);
};

BTWDecorator.prototype._getRefmanForElement = function (root, el) {
    var name = util.getOriginalName(el);
    switch(name) {
    case "ptr":
    case "ref":
        // Find the target and return its value

        var target_attr = el.getAttribute(util.encodeAttrName("target"));
        if (!target_attr)
            return null;

        // Slice to drop the #.
        var target_id = target_attr.slice(1);

        var target = el.ownerDocument.getElementById("BTW-" + target_id);
        return target ? this._getRefmanForElement(root, target) : null;
    case "btw:sense":
        return this._sense_refman;
    case "btw:subsense":
        var sense = closestSense(el);
        return this._sense_refman.idToSubsenseRefman(sense.id);
    case "btw:example":
    case "btw:example-explained":
        return this._example_refman;
    default:
        throw new Error("unexpected element: " + el);
    }
};

BTWDecorator.prototype._getIDManagerForRefman = function (refman) {
    switch(refman.name) {
    case "sense":
    case "subsense":
        return this._sense_subsense_id_manager;
    case "example":
        return this._example_id_manager;
    default:
        throw new Error("unexpected name: " + refman.name);
    }
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

function unitHeadingDecorator(root, el, gui_updater) {
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("head")) {
            gui_updater.removeNode(child);
            break; // There's only one.
        }
        child = next;
    }

    var name = util.getOriginalName(el);
    var head_str = unit_heading_map[name];
    if (head_str === undefined)
        throw new Error("found an element with name " + name +
                        ", which is not handled");

    var head = el.ownerDocument.createElement("div");
    head.className = "head _phantom _start_wrapper";
    head.innerHTML = head_str;
    head.id = allocateHeadID();
    gui_updater.insertNodeAt(el, 0, head);
}

BTWDecorator.prototype.sectionHeadingDecorator = function (root, el,
                                                           gui_updater,
                                                           head_str) {
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("head")) {
            gui_updater.removeNode(child);
            break; // There's only one.
        }
        child = next;
    }

    if (head_str === undefined) {
        var name = util.getOriginalName(el);
        for(var s_ix = 0, spec;
            (spec = this._section_heading_specs[s_ix]) !== undefined; ++s_ix) {
            if (el.matches(spec.selector))
                break;
        }
        if (spec === undefined)
            throw new Error("found an element with name " + name +
                            ", which is not handled");
        var label_f = spec.label_f;
        head_str = (label_f) ? spec.heading + " " + label_f(el) : spec.heading;
    }

    var head = el.ownerDocument.createElement("div");
    head.className = "head _phantom _start_wrapper";
    head.textContent = "[" + head_str + "]";
    head.id = allocateHeadID();
    gui_updater.insertNodeAt(el, 0, head);
};

function setTitle($el, data) {
    var creators = data.creators;
    var first_creator = "***ITEM HAS NO CREATORS***";
    if (creators)
        first_creator = creators.split(",")[0];

    var title = first_creator + ", " + data.title;
    var date = data.date;
    if (date)
        title += ", " + date;

    tooltip($el, {"title": title, container: "body"});
}

BTWDecorator.prototype.linkingDecorator = function (root, el, is_ptr) {
    var orig_target = el.getAttribute(util.encodeAttrName("target"));
    // XXX This should become an error one day. The only reason we
    // need this now is that some of the early test files had <ref>
    // elements without targets.
    if (!orig_target)
        orig_target = "";

    orig_target = orig_target.trim();

    var doc = root.ownerDocument;
    var target_id, child, next; // Damn hoisting.
    if (orig_target.lastIndexOf("#", 0) === 0) {
        // Internal target
        // Add BTW in front because we want the target used by wed.
        target_id = orig_target.replace(/#(.*)$/,'#BTW-$1');

        var text = doc.createElement("div");
        text.className = "_text _phantom _linking_deco";
        var a = doc.createElement("a");
        a.className = "_phantom";
        a.setAttribute("href", target_id);
        text.appendChild(a);
        if (is_ptr) {
            // _linking_deco is used locally to make this function idempotent

            child = el.firstElementChild;
            while(child) {
                next = child.nextElementSibling;
                if (child.classList.contains("_linking_deco")) {
                    this._gui_updater.removeNode(child);
                    break; // There is only one.
                }
                child = next;
            }

            var refman = this._getRefmanForElement(root, el);

            // Find the referred element. Slice to drop the #.
            var target = doc.getElementById(target_id.slice(1));

            // An undefined or null refman can happen when first
            // decorating the document.
            var label;
            if (refman) {
                if (refman.name === "sense" || refman.name === "subsense") {
                    label = refman.idToLabel(target_id.slice(1));
                    label = label && "[" + label + "]";
                }
                else {
                    // An empty target can happen when first
                    // decorating the document.
                    if (target) {
                        var data_el = this._editor.toDataNode(el);
                        var data_target = this._editor.toDataNode(target);
                        label = refman.getPositionalLabel(data_el,
                                                          data_target,
                                                          target_id.slice(1));
                    }
                }
            }

            if (label === undefined)
                label = target_id;

            a.textContent = label;

            // A ptr contains only attributes, no text, so we can just append.
            var pair = this._mode.nodesAroundEditableContents(el);
            this._gui_updater.insertBefore(el, text, pair[1]);

            if (target) {
                var target_name = util.getOriginalName(target);

                // Reduce the target to something sensible for tooltip text.
                if (target_name === "btw:sense")
                    target = target.querySelector(jqutil.toDataSelector(
                        "btw:english-rendition>btw:english-term"));
                else if (target_name === "btw:subsense") {
                    child = target.firstElementChild;
                    while(child) {
                        if (child.classList.contains("btw:explanation")) {
                            target = child;
                            break;
                        }
                        child = child.nextElementSibling;
                    }
                }
                else if (target_name === "btw:example")
                    target = undefined;

                if (target) {
                    target = target.cloneNode(true);
                    var nodes = target.querySelectorAll(
                        ".head, ._gui, ._explanation_number");
                    for (var node_ix = 0, node;
                         (node = nodes[node_ix]) !== undefined; ++node_ix)
                        node.parentNode.removeChild(node);
                    tooltip($(text), {"title":
                                      "<div>" + target.innerHTML + "</div>",
                                      "html": true, "container": "body"});
                }
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

            target_id = orig_target;

            // It is okay to skip the tree updater for these operations.
            child = el.firstElementChild;
            while(child) {
                next = child.nextElementSibling;
                if (child.classList.contains("_ref_abbr") ||
                    child.classList.contains("_ref_paren"))
                    this._gui_updater.removeNode(child);
                child = next;
            }

            var abbr = doc.createElement("div");
            abbr.className = "_text _phantom _ref_abbr";
            this._gui_updater.insertBefore(el, abbr, el.firstChild);
            var open = doc.createElement("div");
            open.className = "_phantom _decoration_text _ref_paren " +
                "_open_ref_paren _start_wrapper";
            open.innerHTML = "(";
            this._gui_updater.insertBefore(el, open, abbr);

            var close = doc.createElement("div");
            close.className = "_phantom _decoration_text " +
                      "_ref_paren _close_ref_paren _end_wrapper";
            close.innerHTML = ")";
            this._gui_updater.insertBefore(el, close);

            var dec = this;
            var $el = $(el);
            $.ajax({
                url: target_id,
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


                dec._gui_updater.insertText(abbr, 0, text);
                $el.trigger("wed-refresh");

            }).fail(function () {
                dec._gui_updater.insertText(abbr, 0, "NON-EXISTENT");
                $el.trigger("wed-refresh");
            });
        }
    }
};

BTWDecorator.prototype._refChangedInGUI = function (root, el) {
    var example = closest(el, jqutil.toDataSelector(
        "btw:example, btw:example-explained"));

    if (!example)
        return;

    var id = example.getAttribute(util.encodeAttrName("xml:id"));
    if (!id)
        return;

    // Find the referred element.
    var ptrs = root.querySelectorAll(
        util.classFromOriginalName("ptr") + "[" +
            util.encodeAttrName("target") + "='#" + id + "']");

    for (var i = 0, limit = ptrs.length; i < limit; ++i)
        this.refreshElement(root, ptrs[i]);
};


BTWDecorator.prototype.ptrDecorator = function (root, el) {
    this.linkingDecorator(root, el, true);
};

BTWDecorator.prototype.refDecorator = function (root, el) {
    this.linkingDecorator(root, el, false);
};

function languageDecorator(el) {
    var lang = el.getAttribute(util.encodeAttrName("xml:lang"));
    var prefix = lang.slice(0, 2);
    if (prefix !== "en") {
        el.classList.add("_btw_foreign");
        // $el.css("background-color", "#DFCFAF");
        // // Chinese is not commonly italicized.
        if (prefix !== "zh")
            //$el.css("font-style", "italic");
            el.classList.add("_btw_foreign_italics");

        var label = btw_util.languageCodeToLabel(lang);
        if (label === undefined)
            throw new Error("unknown language: " + lang);
        label = label.split("; ")[0];
        tooltip($(el), {"title": label, "container": "body"});
    }
}


BTWDecorator.prototype._refreshNavigationHandler = function () {
    var doc = this._gui_root.ownerDocument;
    var prev_at_depth = [doc.createElement("li")];

    function getParent(depth) {
        var parent = prev_at_depth[depth];
        if (!parent) {
            parent = doc.createElement("li");
            prev_at_depth[depth] = parent;
            var grandparent = getParent(depth - 1);
            grandparent.appendChild(parent);
        }
        return parent;
    }

    var heads = this._gui_root.getElementsByClassName("head");
    for(var i = 0, el; (el = heads[i]) !== undefined; ++i) {
        // This is the list of DOM parents that do have a head
        // child, i.e. which participate in navigation.
        var parents = [];
        var parent = el.parentNode;
        while (parent) {
            if (domutil.childByClass(parent, "head"))
                parents.push(parent);

            if (parent === this._gui_root)
                break; // Don't go beyond this point.

            parent = parent.parentNode;
        }

        // This will never be less than 1 because the current
        // element's parent satisfies the selectors above.
        var my_depth = parents.length;

        parent = el.parentNode;
        var orig_name = util.getOriginalName(parent);

        var li = doc.createElement("li");
        li.className = 'btw-navbar-item';
        li.innerHTML = "<a class='navbar-link' href='#" + el.id +
                    "'>" + el.textContent + "</a>";

        // getContextualActions needs to operate on the data tree.
        var data_parent = $.data(parent, "wed_mirror_node");

        // btw:explanation is the element that gets the heading that
        // marks the start of a sense. So we need to adjust.
        if (orig_name === "btw:explanation") {
            var parent_subsense = data_parent.parentNode;
            if (parent_subsense.classList.contains("btw:subsense")) {
                orig_name = "btw:subsense";
                data_parent = parent_subsense;
            }
        }

        // Add contextmenu handlers depending on the type of parent
        // we are dealing with.
        var a = li.firstChild;
        li.setAttribute('data-wed-for', orig_name);

        var $el = $(el);
        if (orig_name === "btw:sense" ||
            orig_name === "btw:english-rendition" ||
            orig_name === "btw:subsense") {
            $(a).on("contextmenu", {node: data_parent},
                  this._navigationContextMenuHandler.bind(this));
            a.innerHTML += ' <i class="fa fa-cog"></i>';
            var old_icon = domutil.childByClass(el, 'fa');
            if (old_icon)
                old_icon.parentNode.removeChild(old_icon);
            el.innerHTML += ' <i class="fa fa-cog"></i>';
            // We must remove all previous handlers.
            $el.off("wed-context-menu");
            $el.on("wed-context-menu", {node: data_parent},
                   this._navigationContextMenuHandler.bind(this));
        }
        else {
            // We turn off context menus on the link and on the header.
            $(a).on("contextmenu", false);
            $el.on("wed-context-menu", false);
        }
        el.setAttribute("data-wed-custom-context-menu", true);

        getParent(my_depth - 1).appendChild(li);
        prev_at_depth[my_depth] = li;
    }

    this._editor.setNavigationList(
        Array.prototype.slice.call(prev_at_depth[0].children));
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
    var data = {name: orig_name,
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

    data = {name: orig_name, move_caret_to: makeDLoc(
        this._editor.data_root, container, offset + 1)};
    for(act_ix = 0, act; (act = actions[act_ix]) !== undefined; ++act_ix)
        tuples.push([act, data,
                     act.getLabelFor(data) + " after this one"]);

    var target = ev.target;
    var doc = ev.target.ownerDocument;
    var nav_list = closestByClass(target, "nav-list", document.body);
    if (nav_list) {
        // This context menu was invoked in the navigation list.

        var this_li = closest(target, "li", nav_list);
        var sibling_links = [];
        var parent = this_li.parentNode;
        var child = parent.firstElementChild;
        while(child) {
            if (child.getAttribute('data-wed-for') === orig_name)
                sibling_links.push(child);
            child = child.nextElementSibling;
        }

        // If the node has siblings we potentially add swap with previous
        // and swap with next.
        if (sibling_links.length > 1) {
            data = {name: orig_name, node: node,
                    move_caret_to: makeDLoc(this._editor.data_root,
                                            container, offset)};
            // However, don't add swap with prev if we are first.
            if (!sibling_links[0].contains(ev.currentTarget))
                tuples.push(
                    [this._mode.swap_with_prev_tr, data,
                     this._mode.swap_with_prev_tr.getLabelFor(data)]);

            // Don't add swap with next if we are last.
            if (!sibling_links[sibling_links.length - 1].contains(ev.currentTarget))
                tuples.push(
                    [this._mode.swap_with_next_tr, data,
                     this._mode.swap_with_next_tr.getLabelFor(data)]);
        }
    }
    else {
        // Set the caret to be inside the head
        this._editor.setGUICaret(target, 0);
    }

    // Delete the node
    data = {node: node, name: orig_name,
            move_caret_to: makeDLoc(this._editor.data_root, node, 0)};
    this._mode.getContextualActions(
        "delete-element", orig_name, node, 0).forEach(function (act) {
            tuples.push([act, data, act.getLabelFor(data)]);
        });

    var li;

    // Convert the tuples to actual menu items.
    var items = [];

    // Put the documentation link first.
    var doc_url = this._mode.documentationLinkFor(orig_name);
    if (doc_url) {
        li = doc.createElement("li");
        var a = this._editor.makeDocumentationLink(doc_url);
        li.appendChild(a);
        items.push(li);
    }

    for(var tix = 0, tup; (tup = tuples[tix]) !== undefined; ++tix) {
        li = doc.createElement("li");
        li.innerHTML = "<a tabindex='0' href='#'>" + tup[2] + "</a>";
        var $a = $(li.firstChild);
        $a.mousedown(false);
        $a.click(tup[1], tup[0].bound_handler);
        items.push(li);
    }

    new context_menu.ContextMenu(this._editor.my_window.document,
                                 ev.clientX, ev.clientY, items);

    return false;
});


exports.BTWDecorator = BTWDecorator;

});
