// im sorry
function sleep (time) {
  return new Promise((resolve) => setTimeout(resolve, time));
}
$(document).ready(function() {
    $("#update-button").click(function(event) {
        event.preventDefault();
        var form = $("#update-form")[0];
        var data = new FormData();
        data.append("file", form[0].files[0]);
        $("#update-button").prop("disabled", true);
        $.ajax({
            type: "POST",
            enctype: "multipart/form-data",
            url: "/api/upgrade",
            data: data,
            processData: false,
            contentType: false,
            cache: false,
            success: function(data) {
                $("#update-button").prop("disabled", false);
            },
            error: function(e) {
                $("#update-button").prop("disabled", false);
            }
        });
    });

    $("#shutdown").click(function(event) {
        $.post("/api/shutdown");
    });
    $("#restart").click(function(event) {
        $.post("/api/restart");
    });
    $("#shutdown-host").click(function(event) {
        $.post("/api/shutdown-host");
    });
    $("#restart-host").click(function(event) {
        $.post("/api/restart-host");
    });
    $("#import-button").click(function(event) {
        event.preventDefault();
        var form = $("#import-form")[0];
        var fileReader = new FileReader();
        var nodetree;
        var success = function ( content ) {
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
    $(document).on("click", "#network-button", function(event) {
        var form = $("#network-form")[0];
        var data = {
            "team": parseInt(form[0].valueAsNumber),
            "static": form[1].checked,
            "nt_enabled": form[2].checked,
            "nt_client": (form[3].value == "client")
        }
        $.ajax({
            type: "POST",
            url: "/api/network",
            data: JSON.stringify(data),
            contentType: "application/json",
            success: function(data) {
                sleep(1500).then(() => {
                    location.reload();
                });
            },
            error: function(e) {
                console.log("Failed to update network config");
            },
        });
    });
});
