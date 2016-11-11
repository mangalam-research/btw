define(function factory(require) {
  "use strict";

  var $ = require("jquery");
  var Displayers = require("./displayers").Displayers;
  require("jquery.cookie");
  require("datatables.bootstrap");

  // This number should be bumped whenever we must flush the old saved
  // state but do not have any other means to do so.
  var _LOCAL_VERSION = 1;

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
  return function semanticFieldSearch($table, displayDiv, options) {
    var doc = displayDiv.ownerDocument;
    var displayers = new Displayers(displayDiv);

    var template = "\
 <i class='fa fa-question-circle text-info'></i> <label>in \
<select class='form-control input-sm' name='aspect'>\
<option value='sf'>semantic field names</option>\
<option value='lexemes'>lexemes</option>\
</select></label>\
 <i class='fa fa-question-circle text-info'></i> <label>among \
<select class='form-control input-sm' name='scope'>\
<option value='all'>all fields</option>\
<option value='hte'>HTE fields</option>\
<option value='btw'>custom BTW fields</option>\
</select></label>\
 <i class='fa fa-question-circle text-info'></i>\
";

    var searchAspect = null;
    var searchScope = null;

    function makeHelpPopover(el, _class) {
      $(el).popover({
        placement: "auto",
        content: doc.querySelector(
          ".semantic-field-search-help ." + _class),
        html: "true",
      });
    }

    // We maintain a state-of-the-GUI due to the way DataTables
    // operates. It is possible for the first ajax query to happen
    // before the GUI has been loaded. Therefore the ajax request
    // cannot be modeled directly after what the GUI state ought to
    // be because the GUI does not exist yet.
    var state;

    function resetState() {
      state = {
        aspect: "sf",
        scope: "all",
      };
    }

    function guiFromState() {
      var aspect = state.aspect;
      if (searchAspect && aspect) {
        searchAspect.value = aspect;
      }

      var scope = state.scope;
      if (searchScope && scope) {
        searchScope.value = scope;
      }
    }

    function stateFromGUI() {
      if (searchAspect) {
        state.aspect = searchAspect.value;
      }

      if (searchScope) {
        state.scope = searchScope.value;
      }
    }

    function drawCallback() {
      if (!searchAspect || !searchAspect.parentNode) {
        var filter =
              doc.getElementById("semantic-field-table_wrapper")
              .getElementsByClassName("dataTables_filter")[0];
        var input = filter.getElementsByTagName("input")[0];
        input.parentNode.insertAdjacentHTML("afterend", template);
        searchAspect = filter.querySelector("select[name='aspect']");
        searchScope = filter.querySelector("select[name='scope']");

        var helpEls = filter
              .getElementsByClassName("fa-question-circle");
        makeHelpPopover(helpEls[0], "search-help");
        makeHelpPopover(helpEls[1], "aspect-help");
        makeHelpPopover(helpEls[2], "scope-help");

        guiFromState();
        $([searchAspect, searchScope]).change(function onChange() {
          stateFromGUI();
          table.api().draw(); // eslint-disable-line no-use-before-define
        });
      }
    }

    var token = _LOCAL_VERSION;

    resetState();

    $.fn.dataTable.ext.errMode = "none";

    $table.on("error.dt", function onError() {
      resetState();
      stateFromGUI();
      $(this).DataTable().state.clear(); // eslint-disable-line new-cap
    });

    var table = $table.dataTable({
      dom: "<'row'<'col-sm-2'l><'col-sm-10'f>>" +
        "<'row'<'col-sm-12'tr>>" +
        "<'row'<'col-sm-5'i><'col-sm-7'p>>",
      processing: true,
      serverSide: true,
      autoWidth: false,
      stateSave: true,
      order: [[1, "asc"]],
      stateSaveParams: function stateSaveParams(settings, data) {
        data.btw_token = token;
        data.aspect = state.aspect;
        data.scope = state.scope;
      },
      stateLoadParams: function stateLoadParams(settings, data) {
        if (data.btw_token !== token) {
          // The token changed, clear the state.
          resetState();
          this.api().state.clear();
          return false;
        }
        return undefined;
      },
      stateLoaded: function stateLoaded(settings, data) {
        var aspect = data.aspect;
        if (aspect && !/^[a-z]+$/.test(aspect)) {
          data.aspect = undefined; // Corrupt data, reset.
        }

        var scope = data.scope;
        if (scope && !/^[a-z]+$/.test(scope)) {
          data.scope = undefined; // Corrupt data, reset.
        }

        state = data;
        guiFromState();
      },
      ajax: {
        url: options.ajax_source_url,
        data: function data(params) {
          params.aspect = state.aspect;
          params.scope = state.scope;
        },
      },
      columnDefs: [{
        targets: [0],
        orderable: false,
        visible: false,
      }, {
        targets: [1],
        createdCell: function createdCell(cell) {
          $(cell.getElementsByClassName("sf-link")).click(function onClick(ev) {
            displayers.open(ev.target.href);
            return false;
          });
        },
      }],
      drawCallback: drawCallback,
    });

    $table.data("search-table", table);
    return {
      table: table,
      displayers: displayers,
    };
  };
});
