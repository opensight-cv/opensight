// im sorry
$(document).ready(function() {
    $("#upload-button").click(function(event) {
        event.preventDefault();
        var form = $("#upload-form")[0];
        var data = new FormData();
        data.append("file", form[0].files[0]);
        $("#upload-button").prop("disabled", true);
        $.ajax({
            type: "POST",
            enctype: "multipart/form-data",
            url: "/api/upgrade",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            success: function(data) {
                $("#upload-button").prop("disabled", false);
            },
            error: function(e) {
                $("#upload-button").prop("disabled", false);
            }
        });
    });

    $("#shutdown").click(function(event) {
        $.post("/api/shutdown");
    });
    $("#restart").click(function(event) {
        $.post("/api/restart");
    });
    $("#import-button").click(function(event) {
        event.preventDefault();
        var form = $("#import-form")[0];
        var fileReader = new FileReader();
        var nodetree;
        var success = function ( content ) {
            console.log(content);
            $.post(
                "/api/nodes",
                content,
                function() {
                    console.log("successful post request");
                },
                "json"
            );
        }
        fileReader.onload = function ( evt ) { success( evt.target.result ) };
        fileReader.readAsText(form[0].files[0]);
    });
    $("#export-button").click(function() {
        $("<a />", {
            "download": "nodetree.json",
            "href" : "data:application/json," + encodeURIComponent(JSON.stringify(
                $.ajax({url:"/api/nodes", async: false})['responseJSON']
            ))
        }).appendTo("body")
            .click(function() {
                $(this).remove()
            })[0].click()
    })
    $(document).on("click", "#profile-button", function(event) {
        $.ajax({
            type: "POST",
            url: "/api/profile?profile=" + $(this).val(),
            processData: false,
            contentType: false,
            success: function(data) {
                location.reload();
            },
            error: function(e) {
                location.reload();
            }
        });
    });
});
