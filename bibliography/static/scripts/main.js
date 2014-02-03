require(["jquery", "bootstrap", "modules/bibSearch"], function ($, _bootstrap,
                                                                BS) {
    // instantiate the bibliography search class
    var bibSearch = new BS();

    $(document).ready(function () {
        $(".bibsearch-form").submit(function (ev) {
            ev.preventDefault();
            return false;
        });

        // when the list selection changes fire ajax search event
        $("#id_library").change(function () {
            var keywordField = $("#id_keyword").val();
            if (keywordField.length > 0) {
                // fire the ajax submit
                bibSearch.ajaxSearch();
            }
        });

        var keytimer = null;
        var timerdelay = 300; //adjust speed in ms var
        var keywordHistory = "";

        // when the search keyword changes fire ajax search event
        $("#id_keyword").bind('keyup change input propertychange',
        function (evnt) {

            var code = evnt.which;
            if (code == 13) {
                evnt.preventDefault();
            }

            if (keytimer) {
                //if new key comes before timeout clear it
                window.clearTimeout(keytimer);
            }

            keytimer = window.setTimeout(function () {
                var keydata = $("#id_keyword").val()

                if ((keydata.length > 0) && (keywordHistory != keydata))
                // as timerdelay is reached timeout occurs, now
                // fire ajax.
                {
                    bibSearch.ajaxSearch();
                    keywordHistory = keydata;
                }
            }, timerdelay);

        });

    });

});
