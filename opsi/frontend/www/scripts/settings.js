function sleep(time) {
  return new Promise(resolve => setTimeout(resolve, time));
}

// spinner, check, cross
function setIcons(icon) {
  $(".status-indicator-icon")
    .css("display", "none")
    .removeClass("status-indicator-greyscale");
  $(".status-indicator-" + icon).css("display", "block");
}
$(document).ready(function() {
  setIcons("check");
  $("#update-button").click(function(event) {
    event.preventDefault();
    var form = $("#update-form")[0];
    var data = new FormData();
    data.append("file", form[0].files[0]);
    $("#update-button").prop("disabled", true);
    setIcons("spinner")
    $.ajax({
      type: "POST",
      enctype: "multipart/form-data",
      url: "/api/upgrade",
      data: data,
      processData: false,
      contentType: false,
      cache: false,
      success: function(data) {
        setIcons("check")
        $("#update-button").prop("disabled", true);
      },
      error: function(e) {
        console.log(e);
        setIcons("cross")
        $("#update-button").prop("disabled", false);
      }
    });
  });
  $("#delete-button").click(function(event) {
    setIcons("spinner")
    event.preventDefault();
    $.ajax({
      type: "POST",
      enctype: "multipart/form-data",
      url: "/api/nodes",
      data: '{"nodes": []}',
      processData: false,
      contentType: false,
      cache: false,
      success: function(data) {
        setIcons("check")
        $("#delete-button").prop("disabled", true);
      },
      error: function(e) {
        console.log(e);
        setIcons("cross")
        $("#delete-button").prop("disabled", false);
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
    var success = function(content) {
      $.post(
        "/api/nodes",
        content,
        function() {
          console.log("successful post request");
        },
        "json"
      );
    };
    fileReader.onload = function(evt) {
      success(evt.target.result);
    };
    fileReader.readAsText(form[0].files[0]);
  });
  $("#export-button").click(function() {
    $("<a />", {
      download: "nodetree.json",
      href:
        "data:application/json," +
        encodeURIComponent(
          JSON.stringify(
            $.ajax({ url: "/api/nodes", async: false })["responseJSON"]
          )
        )
    })
      .appendTo("body")
      .click(function() {
        $(this).remove();
      })[0]
      .click();
  });
  $(document).on("click", ".profile-button", function(event) {
    setIcons("spinner");
    $.ajax({
      type: "POST",
      url: "/api/profile?profile=" + $(this).val(),
      processData: false,
      contentType: false,
      success: function(data) {
        setIcons("check");
        location.reload();
      },
      error: function(e) {
        console.log(e);
        setIcons("cross");
      }
    });
  });
  $(document).on("click", "#network-button", function(event) {
    var form = $("#network-form")[0];
    if (typeof form[2] === undefined) {
      var data = {
        team: parseInt(form[0].valueAsNumber),
        static: form[1].checked,
      };
    } else {
      var data = {
        team: parseInt(form[0].valueAsNumber),
        static: form[1].checked,
        nt_enabled: form[2].checked,
        nt_client: form[3].value === "client"
      };
    }
    setIcons("spinner");
    $.ajax({
      type: "POST",
      url: "/api/network",
      data: JSON.stringify(data),
      contentType: "application/json",
      success: function(data) {
        sleep(5000).then(() => {
          location.reload();
          setIcons("check");
        });
      },
      error: function(e) {
        console.log(e);
        setIcons("cross");
      }
    });
  });
});

