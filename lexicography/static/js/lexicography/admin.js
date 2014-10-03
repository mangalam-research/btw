require(["jquery", "jquery.cookie", "jquery.growl"], function ($) {
    $(function () {
        var csrftoken = $.cookie('csrftoken');
        $(".lexicography-revert").click(function () {
            $.ajax({
                type: "POST",
                url: $(this).attr("href"),
                headers: {
                    'X-CSRFToken': csrftoken
                }
            }).done(function () {
                $.growl.notice( {
                    message: "The entry was reverted.",
                    location: "tc"
                });
            }).fail(function () {
                $.growl.error( {
                    message: "Could not revert the entry, " +
                        "probably because it is locked.",
                    location: "tc"
                });
            });
            return false;
        });

        $(".lexicography-delete, .lexicography-undelete").click(function (ev) {
            var delete_ = ev.target.classList.contains("lexicography-delete");
            $.ajax({
                type: "POST",
                url: $(this).attr("href"),
                headers: {
                    'X-CSRFToken': csrftoken
                }
            }).done(function () {
                $.growl.notice( {
                    message: "The entry was " + delete_ ? "deleted" :
                        "undeleted",
                    location: "tc"
                });
            }).fail(function () {
                $.growl.error( {
                    message: "Could not act on the entry, " +
                        "probably because it is locked.",
                    location: "tc"
                });
            });
            return false;
        });
    });
});
