define(['jquery', './displayers', 'jquery.cookie', 'datatables.bootstrap'],
       function ($, displayers) {

var Displayers = displayers.Displayers;
var Displayer = displayers.Displayer;

// This number should be bumped whenever we must flush the old saved
// state but do not have any other means to do so.
var _LOCAL_VERSION=1;

/**
 * Manages a semantic field search table. This means:
 *
 * - Create the DataTables object which will link the HTML table to
 *   the Django backend. Customize the table to display the right
 *   information and send the right parameters to the Django backend.
 *
 * - Display semantic field details when a user clicks on a semantic
 *   field shown by the table.
 *
 * - Manage each semantic field display. Using {@link
 *   module:semantic-field-search~Displayers Displayers} and {@link
 *   module:semanatic-field-search~Displayer Displayer}
 */
return function ($table, display_div, options) {
    var doc = display_div.ownerDocument;
    var displayers = new Displayers(display_div);

    var template = '\
 <i class="fa fa-question-circle text-info"></i> <label>in \
<select class="form-control input-sm" name="aspect">\
<option value="sf">semantic field names</option>\
<option value="lexemes">lexemes</option>\
</select></label>\
 <i class="fa fa-question-circle text-info"></i> <label>among \
<select class="form-control input-sm" name="scope">\
<option value="all">all fields</option>\
<option value="hte">HTE fields</option>\
<option value="btw">custom BTW fields</option>\
</select></label>\
 <i class="fa fa-question-circle text-info"></i>\
';

    var search_aspect = null;
    var search_scope = null;

    function makeHelpPopover(el, _class) {
        $(el).popover({
            placement: "auto",
            content: doc.querySelector(
                ".semantic-field-search-help ." + _class),
            html: "true"
        });
    }

    function drawCallback() {
        if (!search_aspect || !search_aspect.parentNode) {
            var filter =
                    doc.getElementById("semantic-field-table_wrapper")
                    .getElementsByClassName("dataTables_filter")[0];
            var input = filter.getElementsByTagName("input")[0];
            input.parentNode.insertAdjacentHTML("afterend", template);
            search_aspect = filter.querySelector("select[name='aspect']");
            search_scope = filter.querySelector("select[name='scope']");

            var help_els = filter
                    .getElementsByClassName('fa-question-circle');
            makeHelpPopover(help_els[0], "search-help");
            makeHelpPopover(help_els[1], "aspect-help");
            makeHelpPopover(help_els[2], "scope-help");

            GUIFromState();
            $([search_aspect, search_scope]).change(function () {
                StateFromGUI();
                table.api().draw();
            });
        }

    }

    var token = _LOCAL_VERSION;

    // We maintain a state-of-the-GUI due to the way DataTables
    // operates. It is possible for the first ajax query to happen
    // before the GUI has been loaded. Therefore the ajax request
    // cannot be modeled directly after what the GUI state ought to
    // be because the GUI does not exist yet.
    var state;

    function resetState() {
        state = {
            aspect: "sf",
            scope: "all"
        };
    }

    resetState();

    function GUIFromState() {
        var aspect = state.aspect;
        if (search_aspect && aspect) {
            search_aspect.value = aspect;
        }

        var scope = state.scope;
        if (search_scope && scope) {
            search_scope.value = scope;
        }
    }

    function StateFromGUI() {
        if (search_aspect) {
            state.aspect = search_aspect.value;
        }

        if (search_scope) {
            state.scope = search_scope.value;
        }
    }

    $.fn.dataTable.ext.errMode = 'none';

    $table.on("error.dt", function () {
        resetState();
        StateFromGUI();
        $(this).DataTable().state.clear();
    });

    var table = $table.dataTable({
        dom: "<'row'<'col-sm-2'l><'col-sm-10'f>>" +
	    "<'row'<'col-sm-12'tr>>" +
	    "<'row'<'col-sm-5'i><'col-sm-7'p>>",
        processing: true,
        serverSide: true,
        autoWidth: false,
        stateSave: true,
        order: [[1, 'asc']],
        stateSaveParams: function (settings, data) {
            data.btw_token = token;
            data.aspect = state.aspect;
            data.scope = state.scope;
        },
        stateLoadParams: function (settings, data) {
            if (data.btw_token !== token) {
                // The token changed, clear the state.
                resetState();
                this.api().state.clear();
                return false;
            }
            return undefined;
        },
        stateLoaded: function (settings, data) {
            var aspect = data.aspect;
            if (aspect && !/^[a-z]+$/.test(aspect))
                data.aspect = undefined; // Corrupt data, reset.

            var scope = data.scope;
            if (scope && !/^[a-z]+$/.test(scope))
                data.scope = undefined; // Corrupt data, reset.

            state = data;
            GUIFromState();
        },
        ajax: {
            url: options.ajax_source_url,
            data: function (params) {
                params.aspect = state.aspect;
                params.scope = state.scope;
            }
        },
        columnDefs: [{
            targets: [0],
            orderable: false,
            visible: false
        }, {
            targets: [1],
            createdCell: function (cell, data, row_data, row_ix, cell_ix) {
                $(cell.getElementsByClassName("sf-link")).click(function (ev) {
                    displayers.open(ev.target.href);
                    return false;
                });

            }
        }],
        drawCallback: drawCallback
    });

    $table.data("search-table", table);
    return {
        table: table,
        displayers: displayers
    };
};

});
