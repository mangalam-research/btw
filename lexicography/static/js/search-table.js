define(['jquery', 'jquery.cookie', 'datatables.bootstrap'], function ($) {

var csrftoken = $.cookie('csrftoken');

return function ($table, options) {
    var can_author = options.can_author;
    var aoColumnDefs = [];
    if (!can_author) {
        aoColumnDefs.push({
            aTargets: [1],
            bSortable: false,
            bVisible: false
        });
        aoColumnDefs.push({
            aTargets: [2],
            bSortable: false,
            bVisible: false
        });
    }
    else {
        aoColumnDefs.push({
            aTargets: [2],
            mRender: function (data, type, row_data) {
                var deleted = row_data[2];
                return deleted === "Yes" ?
                    '<span style="color: red">Yes</span>' : deleted;
            }
        });
    }
    var record_name = options.can_author ? "change records" : "articles";
    var table = $table.dataTable({
        iDisplayLength: options.rows || undefined,
        bLengthChange: (options.rows === undefined),
        bProcessing: true,
        bServerSide: true,
        bAutoWidth: false,
        sAjaxSource: options.ajax_source_url,
        fnServerParams: function (aoData) {
            aoData.push({"name": "bHeadwordsOnly",
                         "value": headword_checkbox &&
                         headword_checkbox.checked} );
            aoData.push({"name": "sPublicationStatus",
                         // If the selector does not exist, then the user
                         // can only search published articles.
                         "value": publication_selector ?
                         publication_selector.value :
                         (can_author ? "both": "published")});
            aoData.push({"name": "bSearchAll",
                         "value": search_all && search_all.checked});
        },
        aoColumnDefs: aoColumnDefs,
        oLanguage: {
            sInfo: "Showing _START_ to _END_ of _TOTAL_ " + record_name,
            sInfoEmpty: "No " + record_name + " to show",
            sInfoFiltered: "(filtered from _MAX_ total " + record_name + ")",
            sLengthMenu: "Show _MENU_ " + record_name
        }
    });

    $table.data("search-table", table);

    var doc = $table[0].ownerDocument;
    var filter =
            doc.getElementById("search-table_wrapper")
            .getElementsByClassName("dataTables_filter")[0];
    var filter_row = filter.parentNode.parentNode;
    var label = filter.ownerDocument.createElement("label");
    label.innerHTML = 'Headwords only: <input type="checkbox" class="form-control input-sm"></input>';
    var headword_checkbox = label.lastElementChild;
    filter.appendChild(doc.createTextNode(" "));
    filter.appendChild(label);

    var publication_selector, search_all;
    if (can_author) {
        var advanced = filter.ownerDocument.createElement("div");
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

        publication_selector =
            advanced.getElementsByClassName("btw-publication-status")[0];

        filter_row.parentNode.insertBefore(advanced,
                                           filter_row.nextElementSibling);

        search_all =
            advanced.getElementsByClassName("btw-search-all-history")[0];
    }

    $([headword_checkbox, publication_selector, search_all]).change(function () {
        table.fnDraw();
    });

    return table;
};

});
