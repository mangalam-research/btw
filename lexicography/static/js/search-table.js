define(['jquery', 'jquery.cookie', 'datatables.bootstrap',
        'jquery.bootstrap-growl'], function ($) {

// This number should be bumped whenever we must flush the old saved
// state but do not have any other means to do so.
var _LOCAL_VERSION=1;

var csrftoken = $.cookie('csrftoken');

return function ($table, options) {
    var can_author = options.can_author;
    var columnDefs = [];
    if (!can_author) {
        columnDefs.push({
            targets: [1, 2],
            orderable: false,
            visible: false
        });
    }
    else {
        columnDefs.push({
            targets: [2],
            render: function (data, type, row_data) {
                var deleted = row_data[2];
                return deleted === "Yes" ?
                    '<span style="color: red">Yes</span>' : deleted;
            }
        });
    }

    // This is not meant to prevent reverse engineering or be
    // sophisticated in any way. What we want is that if a change in
    // privileges happen, then the saved state should be flushed.
    var token = "" + _LOCAL_VERSION + "," + (can_author ? "1": "0");

    var record_name = can_author ? "change records" : "articles";
    var publish_btns = $table[0].getElementsByClassName("btw-publish-btn");
    var unpublish_btns = $table[0].getElementsByClassName("btw-unpublish-btn");

    function alert(el, data, kind) {
        var rect = el.getBoundingClientRect();
        var alertbox = document.createElement("div");
        alertbox.className = "alert alert-dismissible " + kind;
        alertbox.setAttribute("role", "alert");
        alertbox.innerHTML =
            '<button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>' +
            data + '&nbsp;';
        document.body.appendChild(alertbox);
        alertbox.style.position = "absolute";
        alertbox.style.top = rect.top + 5 + "px";
        alertbox.style.left = rect.left + 5 + "px";
    }

    function handle_publish_unpublish(ev) {
        $.ajax({
            type: "POST",
            url: this.attributes.href.value,
            headers: {
                'X-CSRFToken': csrftoken
            }
        }).done(function (data) {
            alert(ev.target, data, "alert-success");
            table.api().ajax.reload(null, false);
        }).fail(function (jqXHR) {
            alert(ev.target, jqXHR.responseText, "alert-danger");
        });
        return false;
    }
    var doc = $table[0].ownerDocument;

    var label = doc.createElement("label");
    label.innerHTML = 'Headwords only: <input type="checkbox" class="form-control input-sm"></input>';
    var headword_checkbox = label.lastElementChild;

    var advanced = doc.createElement("div");
    advanced.className = "panel-group";
    advanced.style.marginBottom = "0px";
    advanced.id="advanced-search";
    advanced.innerHTML = '\
  <div class="panel panel-default">\
    <div class="panel-heading">\
      <h4 class="panel-title" style="font-size: 12px;">\
        <a data-toggle="collapse" data-parent="#accordion" href="#advanced-search-collapse">\
          <i class="fa fa-plus"></i> Advanced search options\
        </a>\
      </h4>\
    </div>\
    <div id="advanced-search-collapse" class="panel-collapse collapse">\
      <div class="panel-body">\
        <label>Publication status: <select class="btw-publication-status form-control input-sm"><option value="published">Published</option><option value="unpublished">Unpublished</option><option value="both" selected>Both</option></select></label> \
        <label>Search all history: <input type="checkbox" class="btw-search-all-history form-control input-sm"></input></label>\
      </div>\
    </div>\
  </div>';
    var icon = advanced.getElementsByClassName("fa")[0];
    var cl = icon.classList;
    $(advanced).on('show.bs.collapse', function(){
        cl.remove("fa-plus");
        cl.add("fa-minus");
    }).on('hide.bs.collapse', function(){
        cl.remove("fa-minus");
        cl.add("fa-plus");
    });

    var publication_selector =
            advanced.getElementsByClassName("btw-publication-status")[0];

    publication_selector.value = can_author ? "both": "published";

    var search_all =
            advanced.getElementsByClassName("btw-search-all-history")[0];

    function drawCallback() {
        if (!label.parentNode) {
            var filter =
                    doc.getElementById("search-table_wrapper")
                    .getElementsByClassName("dataTables_filter")[0];
            var filter_row = filter.parentNode.parentNode;
            filter.appendChild(doc.createTextNode(" "));
            filter.appendChild(label);

            if (can_author)
                filter_row.parentNode.insertBefore(
                    advanced,
                    filter_row.nextElementSibling);

        }

        $([headword_checkbox, publication_selector, search_all])
            .change(function () {
                table.fnDraw();
            });

        var i, btn;
        for (i = 0; (btn = publish_btns[i]); ++i)
            $(btn).click(handle_publish_unpublish);
        for (i = 0; (btn = unpublish_btns[i]); ++i)
            $(btn).click(handle_publish_unpublish);
    }

    var table = $table.dataTable({
        pageLength: options.rows || undefined,
        lengthChange: (options.rows === undefined),
        processing: true,
        serverSide: true,
        autoWidth: false,
        stateSave: true,
        stateSaveParams: function (settings, data) {
            var params = this.api().ajax.params();
            data.btw_token = token;
            data.headwords_only = params.headwords_only;
            data.publication_status = params.publication_status;
            data.search_all = params.search_all;
        },
        stateLoadParams: function (settings, data) {
            if (data.btw_token !== token) {
                // The token changed, clear the state.
                this.api().state.clear();
                return false;
            }
            return undefined;
        },
        stateLoaded: function (settings, data) {
            headword_checkbox.checked = data.headwords_only;
            publication_selector.value = data.publication_status;
            search_all.checked = data.search_all;
        },
        ajax: {
            url: options.ajax_source_url,
            data: function (params) {
                params.headwords_only = headword_checkbox.checked;
                params.publication_status = publication_selector.value;
                params.search_all = search_all.checked;
            }
        },
        columnDefs: columnDefs,
        language: {
            info: "Showing _START_ to _END_ of _TOTAL_ " + record_name,
            infoEmpty: "No " + record_name + " to show",
            infoFiltered: "(filtered from _MAX_ total " + record_name + ")",
            lengthMenu: "Show _MENU_ " + record_name
        },
        drawCallback: drawCallback
    });

    $table.data("search-table", table);
    return table;
};

});
