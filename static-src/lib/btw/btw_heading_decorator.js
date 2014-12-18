/**
 * @module wed/modes/btw/btw_heading_decorator
 * @desc Module for decorating headings
 * @author Louis-Dominique Dubeau
 */
define(function (require, exports, module) {
'use strict';

var util = require("wed/util");
var domutil = require("wed/domutil");
var IDManager = require("./id_manager").IDManager;
var btw_util = require("./btw_util");

function HeadingDecorator(refmans, gui_updater, implied_brackets) {
    this._refmans = refmans;
    this._gui_updater = gui_updater;
    if (implied_brackets === undefined)
        implied_brackets = true;
    this._implied_brackets = implied_brackets;

    this._collapse_heading_id_manager =
        new IDManager("collapse-heading-");
    this._collapse_id_manager =
        new IDManager("collapse-");

    // We bind them here so that we have a unique function to use.
    this._bound_getSenseLabel =
        this._refmans.getSenseLabel.bind(this._refmans);
    this._bound_getSubsenseLabel =
        this._refmans.getSubsenseLabel.bind(this._refmans);

    this._specs = [ {
        selector: "btw:definition",
        heading: "definition"
    }, {
        selector: "btw:sense",
        heading: "SENSE",
        label_f: this._refmans.getSenseLabelForHead.bind(this._refmans)
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
        selector: "btw:antonym>btw:citations",
        heading: "citations"
    }, {
        selector: "btw:cognate>btw:citations",
        heading: "citations"
    }, {
        selector: "btw:conceptual-proximate>btw:citations",
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
        heading: "other citations for sense",
        label_f: this._bound_getSenseLabel
    }, {
        selector: "btw:other-citations",
        heading: "other citations"
    }];

    // Convert the selectors to actual selectors.
    for (var s_ix = 0, spec; (spec = this._specs[s_ix]) !== undefined; ++s_ix)
        spec.data_selector = domutil.toGUISelector(spec.selector);
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

HeadingDecorator.prototype.addSpec = function(spec) {
    this._specs = this._specs.filter(function (x) {
        return x.selector !== spec.selector;
    });
    spec.data_selector = domutil.toGUISelector(spec.selector);
    this._specs.push(spec);
};

HeadingDecorator.prototype.unitHeadingDecorator = function (el) {
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("head")) {
            this._gui_updater.removeNode(child);
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
    this._gui_updater.insertNodeAt(el, 0, head);
};

HeadingDecorator.prototype.sectionHeadingDecorator = function (
    el, specs, head_str) {
    var child = el.firstElementChild;
    var next;
    while(child) {
        next = child.nextElementSibling;
        if (child.classList.contains("head")) {
            this._gui_updater.removeNode(child);
            break; // There's only one.
        }
        child = next;
    }

    var collapse = false;
    if (head_str === undefined) {
        var name = util.getOriginalName(el);
        for(var s_ix = 0, spec; (spec = this._specs[s_ix]) !== undefined;
            ++s_ix) {
            if (el.matches(spec.data_selector))
                break;
        }
        if (spec === undefined)
            throw new Error("found an element with name " + name +
                            ", which is not handled");
        if (spec.heading !== null) {
            var label_f = spec.label_f;
            head_str = (label_f) ? spec.heading + " " + label_f(el) : spec.heading;
        }

        collapse = spec.collapse;
    }

    if (head_str !== undefined) {
        if (!collapse) {
            var head = el.ownerDocument.createElement("div");
            head.className = "head _phantom _start_wrapper";
            head.textContent = this._implied_brackets ?
                ("[" + head_str + "]") : head_str;
            head.id = allocateHeadID();
            this._gui_updater.insertNodeAt(el, 0, head);
        }
        else {
            // If collapse is a string, it is shorthand for a collapse
            // object with the field `kind` set to the value of the
            // string.
            if (typeof collapse === "string") {
                collapse = {
                    kind: collapse
                };
            }
            var collapsible = btw_util.makeCollapsible(
                el.ownerDocument,
                collapse.kind,
                this._collapse_heading_id_manager.generate(),
                this._collapse_id_manager.generate(),
                collapse.additional_heading_classes);
            var group = collapsible.group;
            var panel_body = collapsible.content;
            collapsible.heading.textContent = head_str;

            next = el.nextSibling;
            var parent = el.parentNode;
            this._gui_updater.removeNode(el);
            panel_body.appendChild(el);
            this._gui_updater.insertBefore(parent,
                                           group, next);
        }
    }
};

HeadingDecorator.prototype._updateHeadingsFor = function(el, func) {
    // Refresh the headings that use the sense label.
    for (var s_ix = 0, spec; (spec = this._specs[s_ix]) !== undefined; ++s_ix) {
        if (spec.label_f === func) {
            var subheaders = el.querySelectorAll(spec.data_selector);
            for(var shix = 0, sh; (sh = subheaders[shix]) !== undefined;
                ++shix)
                    this.sectionHeadingDecorator(sh);
        }
    }
};

HeadingDecorator.prototype.updateHeadingsForSubsense = function(subsense) {
    // Refresh the headings that use the subsense label.
    this._updateHeadingsFor(subsense, this._bound_getSubsenseLabel);
};

HeadingDecorator.prototype.updateHeadingsForSense = function(sense) {
    // Refresh the headings that use the sense label.
    this._updateHeadingsFor(sense, this._bound_getSenseLabel);
};

exports.HeadingDecorator = HeadingDecorator;

});
