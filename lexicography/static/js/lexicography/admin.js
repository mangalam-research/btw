require(["jquery", "jquery.cookie"], function ($) {
    $(function () {
        var csrftoken = $.cookie('csrftoken');
        $(".lexicography-revert").click(function () {
            $.ajax({
                type: "POST",
                url: $(this).attr("href"),
                headers: {
                    'X-CSRFToken': csrftoken
                }
            });
            return false;
        });
    });
});
