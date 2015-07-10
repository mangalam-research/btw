define(function (require, exports, module) {
'use strict';

var Decorator = require("wed/decorator").Decorator;
var refmans = require("./btw_refmans");
var oop = require("wed/oop");
var $ = require("jquery");
var util = require("wed/util");
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
var DispatchMixin = require("./btw_dispatch").DispatchMixin;
var HeadingDecorator = require("./btw_heading_decorator").HeadingDecorator;
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
    this._sense_subsense_id_manager = new id_manager.IDManager("S.");
    this._example_id_manager = new id_manager.IDManager("E.");
    this._refmans = new refmans.WholeDocumentManager();
    this._heading_decorator = new HeadingDecorator(
        this._refmans, this._gui_updater);
    this._sense_tooltip_selector = "btw:english-rendition>btw:english-term";

    this._senses_for_refresh_subsenses = [];

    this._label_levels = {};
    [
        "btw:entry",
        "btw:lemma",
        "btw:overview",
        "btw:credits",
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
            parent: domutil.toGUISelector("btw:sense"),
            children: ["btw:subsense", "btw:explanation",
                       "btw:citations", "btw:other-citations",
                       "btw:contrastive-section"]
        },
        {
            parent: domutil.toGUISelector("btw:citations"),
            children: ["btw:example", "btw:example-explained"]
        },
        {
            parent: domutil.toGUISelector(
                "btw:subsense, btw:antonym, btw:cognate, "+
                    "btw:conceptual-proximate"),
            children: ["btw:other-citations"]
        },
        {
            parent: domutil.toGUISelector(
                "btw:example, btw:example-explained"),
            children: ["btw:semantic-fields"]
        },
        {
            parent: domutil.toGUISelector("btw:other-citations"),
            children: ["btw:cit", "btw:semantic-fields"]
        }
    ];

}

oop.inherit(BTWDecorator, Decorator);
oop.implement(BTWDecorator, DispatchMixin);

BTWDecorator.prototype.addHandlers = function () {
    this._domlistener.addHandler(
        "added-element",
        util.classFromOriginalName("btw:entry"),
        function (root, parent, prev, next, el) {
        this.addedEntryHandler(root, el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:sense"),
        function (root, tree, parent, prev, next, el) {
        this.includedSenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluding-element",
        util.classFromOriginalName("btw:sense"),
        function (root, tree, parent, prev, next, el) {
        this.excludingSenseHandler(el);
    }.bind(this));

    this._domlistener.addHandler(
        "included-element",
        util.classFromOriginalName("btw:subsense"),
        function (root, tree, parent, prev, next, el) {
        this.includedSubsenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluding-element",
        util.classFromOriginalName("btw:subsense"),
        function (root, tree, parent, prev, next, el) {
        this.excludingSubsenseHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "excluded-element",
        util.classFromOriginalName("btw:example, btw:example-explained"),
        function (root, tree, parent, prev, next, el) {
        this.excludedExampleHandler(root, el);
    }.bind(this));

    this._gui_domlistener.addHandler(
        "children-changing",
        domutil.toGUISelector("ref, ref *"),
        function (root, added, removed, prev, next, el) {
        this._refChangedInGUI(root, closestByClass(el, "ref", root));
    }.bind(this));

    this._gui_domlistener.addHandler(
        "text-changed",
        domutil.toGUISelector("ref, ref *"),
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
        "excluding-element",
        domutil.toGUISelector("btw:cit foreign"),
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
        domutil.toGUISelector("btw:cit foreign"),
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
        "p",
        key_constants.ENTER,
        key_constants.BACKSPACE,
        key_constants.DELETE);

    input_trigger_factory.makeSplitMergeInputTrigger(
        this._editor,
        "btw:sf",
        key.makeKey(";"),
        key_constants.BACKSPACE,
        key_constants.DELETE);
};

BTWDecorator.prototype.addedEntryHandler = function (root, el) {
    //
    // Perform general checks before we start decorating anything.
    //
    var i, limit, id;

    var data_el = $.data(el, "wed_mirror_node");
    var senses_subsenses = domutil.dataFindAll(data_el,
                                               "btw:sense, btw:subsense");
    for(i = 0, limit = senses_subsenses.length; i < limit; ++i) {
        var s = senses_subsenses[i];
        id = s.getAttribute("xml:id");
        if (id)
            this._sense_subsense_id_manager.seen(id, true);
    }

    var examples = domutil.dataFindAll(data_el,
                                       "btw:example, btw:example-explained");
    for(i = 0, limit = examples.length; i < limit; ++i) {
        var ex = examples[i];
        id = ex.getAttribute("xml:id");
        if (id)
            this._example_id_manager.seen(id, true);
    }
};

BTWDecorator.prototype.refreshElement = function (root, el) {
    // Skip elements which would already have been removed from
    // the tree. Unlikely but...
    if (!root.contains(el))
        return;

    this.refreshVisibleAbsences(root, el);

    this.dispatch(root, el);

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
    var found, spec;
    for(var i = 0, limit = this._visible_absence_specs.length; i < limit;
        ++i) {
        spec = this._visible_absence_specs[i];
        if (el.matches(spec.parent)) {
            found = spec;
            break;
        }
    }

    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("_va_instantiator"))
            this._gui_updater.removeNode(child);
        child = next;
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

            var ename = this._mode._resolver.resolveName(spec);
            var locations = this._editor.validator.possibleWhere(
                node, new validate.Event("enterStartTag", ename.ns,
                                         ename.name));

            // Narrow it down to locations where adding the element
            // won't cause a subsequent problem.
            var filtered_locations = [];
            location_loop:
            for(var lix = 0, l; (l = locations[lix]) !== undefined; ++lix) {
                // We clone only the node itself and its first level
                // children.
                var clone = node.cloneNode(false);
                var div = clone.ownerDocument.createElement("div");
                div.appendChild(clone);

                child = node.firstChild;
                while(child) {
                    clone.appendChild(child.cloneNode(false));
                    child = child.nextSibling;
                }

                clone.insertBefore(
                    transformation.makeElement(clone.ownerDocument,
                                               ename.ns, spec),
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
                        continue location_loop;
                }

                filtered_locations.push(l);
            }
            locations = filtered_locations;

            // No suitable location.
            if (!locations.length)
                continue;

            for (lix = 0; (l = locations[lix]) !== undefined; ++lix) {
                var data_loc = makeDLoc(this._editor.data_root, node, l);
                var data = {name: spec, move_caret_to: data_loc};
                var gui_loc = this._gui_updater.fromDataLocation(data_loc);

                var tuples = [];
                this._mode.getContextualActions(
                    "insert", spec, node, l).forEach(
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

                    $control.click(function (gui_loc, items, ev) {
                        if (this._editor.getGUICaret() === undefined)
                            this._editor.setGUICaret(gui_loc);
                        new context_menu.ContextMenu(
                            this._editor.my_window.document,
                            ev.clientX, ev.clientY,
                            items);
                        return false;
                    }.bind(this, gui_loc, items));
                }
                else if (tuples.length === 1) {
                    control.innerHTML = tuples[0][2];
                    $control.mousedown(false);
                    $control.click(tuples[0][1], function (data_loc, tr, ev) {
                        if (this._editor.getDataCaret() === undefined)
                            this._editor.setDataCaret(data_loc);
                        tr.bound_terminal_handler(ev);
                        this.refreshElement(root, el);
                    }.bind(this, data_loc, tuples[0][0]));
                }
                this._gui_updater.insertNodeAt(gui_loc, control);
            }
        }
    }
};

BTWDecorator.prototype.idDecorator = function (root, el) {
    DispatchMixin.prototype.idDecorator.call(this, root, el);
    this._domlistener.trigger("refresh-sense-ptrs");
};

BTWDecorator.prototype.refreshSensePtrsHandler = function (root) {
    var ptrs = root.getElementsByClassName("ptr");
    for(var i = 0, ptr; (ptr = ptrs[i]) !== undefined; ++i)
        this.linkingDecorator(root, ptr, true);
};

/**
 * This function works exactly like the one in {@link
 * module:btw_dispatch~DispatchMixin DispatchMixin} except that it
 * takes the additional ``final_`` parameter.
 *
 * @param {boolean} final_ Whether there will be any more changes to
 * this ptr or not.
 */
BTWDecorator.prototype.linkingDecorator = function (root, el, is_ptr, final_) {
    DispatchMixin.prototype.linkingDecorator.call(this, root, el, is_ptr);

    // What we are doing here is taking care of updating links to
    // examples when the reference to the bibliographical source they
    // contain is updated. These updates happen asynchronously.
    if (is_ptr && !final_) {
        var doc = el.ownerDocument;
        var orig_target = el.getAttribute(util.encodeAttrName("target"));
        if (!orig_target)
            orig_target = "";

        orig_target = orig_target.trim();

        if (orig_target.lastIndexOf("#", 0) !== 0)
            return;

        // Internal target
        // Add BTW in front because we want the target used by wed.
        var target_id = orig_target.replace(/#(.*)$/,'#BTW-$1');

        // Find the referred element. Slice to drop the #.
        var target = doc.getElementById(target_id.slice(1));

        if (!target)
            return;

        if (!(target.classList.contains("btw:example") ||
              target.classList.contains("btw:example-explained")))
            return;

        // Get the ref element that olds the reference to the
        // bibliographical item, and set an event handler to make sure
        // we update *this* ptr, when the ref changes.
        var ref =
                target.querySelector(domutil.toGUISelector("btw:cit>ref"));

        $(ref).on("wed-refresh", function () {
            this.linkingDecorator(root, el, is_ptr);
        }.bind(this));
    }
};



BTWDecorator.prototype.includedSenseHandler = function (root, el) {
    this.idDecorator(root, el);
    this._domlistener.trigger("included-sense");
};

BTWDecorator.prototype.excludingSenseHandler = function (el) {
    this._deleteLinksPointingTo(el);
    // Yep, we trigger the included-sense trigger.
    this._domlistener.trigger("included-sense");
};



BTWDecorator.prototype.includedSubsenseHandler = function (root, el) {
    this.idDecorator(root, el);
    this.refreshSubsensesForSense(root, el.parentNode);
};


BTWDecorator.prototype.excludingSubsenseHandler = function (root, el) {
    this._deleteLinksPointingTo(el);
    this.refreshSubsensesForSense(root, el.parentNode);
};

BTWDecorator.prototype._deleteLinksPointingTo = function (el) {
    var id = el.getAttribute(util.encodeAttrName("xml:id"));

    // Whereas using querySelectorAll does not **generally** work,
    // using this selector, which selects only on attribute values,
    // works.
    var selector = "*[target='#" + id + "']";

    var links = this._editor.data_root.querySelectorAll(selector);
    for(var i = 0; i < links.length; ++i)
        this._editor.data_updater.removeNode(links[i]);
};

BTWDecorator.prototype.excludedExampleHandler = function (root, el) {
    this._deleteLinksPointingTo(el);
};

BTWDecorator.prototype.includedSenseTriggerHandler = function (root) {
    var senses = root.getElementsByClassName("btw:sense");
    if (senses.length)
        this._refmans.getRefmanForElement(senses[0]).deallocateAll();
    for(var i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        this.idDecorator(root, sense);
        this._heading_decorator.sectionHeadingDecorator(sense);
        this._heading_decorator.updateHeadingsForSense(sense);
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
    var refman = this._refmans.getSubsenseRefman(sense);
    refman.deallocateAll();

    // This happens if the sense was removed from the document.
    if (!this._editor.gui_root.contains(sense))
        return;

    var subsenses = sense.getElementsByClassName("btw:subsense");
    for(var i = 0, subsense; (subsense = subsenses[i]) !== undefined; ++i) {
        this.idDecorator(root, subsense);
        var explanation = domutil.childByClass("btw:explanantion");
        if (explanation)
            this.explanationDecorator(root, explanation);

        this._heading_decorator.updateHeadingsForSubsense(subsense);
    }
};

function jQuery_escapeID(id) {
    return id.replace(/\./g, '\\.');
}

BTWDecorator.prototype._refChangedInGUI = function (root, el) {
    var example = closest(el, domutil.toGUISelector(
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


BTWDecorator.prototype.languageDecorator = function (el) {
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
};


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
            if (parent_subsense.tagName === "btw:subsense") {
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
    var orig_name = node.tagName;

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
