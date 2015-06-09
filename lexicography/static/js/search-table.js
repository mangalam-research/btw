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
            targets: [1, 2, 3],
            orderable: false,
            visible: false
        });
    }
    else {
        columnDefs.push({
            targets: [3],
            render: function (data, type, row_data) {
                var deleted = row_data[3];
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

    function post_publish_unpublish(ev) {
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

    function check_unpublish(ev) {
        var $modal = $(
'<div class="modal" style="position: absolute" tabindex="1">\
  <div class="modal-dialog">\
    <div class="modal-content">\
      <div class="modal-header">\
        <h3>STOP AND READ!</h3>\
      </div>\
      <div class="modal-body">\
        <p>Unpublishing should be done only under very special \
circumstances. There is <strong>no need</strong> to unpubish an old \
version of an article <strong>merely</strong> because you are publishing \
a newer version.</p>\
        <p>Generally, you should unpublish only as a matter of law or \
ethics (for instance, the article used copyrighted material without \
permission).</p>\
        <p>If you have just published a version of an article and want \
to unpublish it right away, this is fine.</p>\
      </div>\
      <div class="modal-footer">\
          <a href="#" class="btn btn-primary" data-dismiss="modal">\
Cancel</a>\
          <a href="#" class="btn btn-default" data-dismiss="modal">\
Yes, I want to unpublish</a>\
      </div>\
    </div>\
  </div>\
</div>');

        document.body.appendChild($modal[0]);

        $modal.on('click', '.btn.btn-primary', function () {
            document.body.removeChild($modal[0]);
            return false;
        });

        var obj = this;
        $modal.on('click', '.btn.btn-default', function () {
            post_publish_unpublish.call(obj, ev);
            document.body.removeChild($modal[0]);
            return false;
        });

        $modal.modal();
        return false;
    }

    var doc = $table[0].ownerDocument;

    var label = doc.createElement("label");
    label.innerHTML = 'Lemmata only: <input type="checkbox" class="form-control input-sm"></input>';
    var lemma_checkbox = label.lastElementChild;

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

        $([lemma_checkbox, publication_selector, search_all])
            .change(function () {
                table.fnDraw();
            });

        var i, btn;
        for (i = 0; (btn = publish_btns[i]); ++i)
            $(btn).click(post_publish_unpublish);
        for (i = 0; (btn = unpublish_btns[i]); ++i)
            $(btn).click(check_unpublish);
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
            data.lemmata_only = params.lemmata_only;
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
            lemma_checkbox.checked = data.lemmata_only;
            publication_selector.value = data.publication_status;
            search_all.checked = data.search_all;
        },
        ajax: {
            url: options.ajax_source_url,
            data: function (params) {
                params.lemmata_only = lemma_checkbox.checked;
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
