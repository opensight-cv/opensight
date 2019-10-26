$(function () {
    function onError() {
        setIcons("cross");
    }

    function onSuccess() {
        setIcons("check");
    }

    // If any of these .then()s fail, there will be no checkmark 

    $.get("../dev/funcs.json") // Download functions
    .then(function (data) { // Load functions
        try {
            funct = new functions(data);
            funct.ui();
        } catch (err) {
            onError("Error importing functions: " + err.message);
            throw err;
        }
    })
    .then(function() { // Download nodes
        return $.get("/api/nodes");
    })
    .then(function (data) { // Import nodes
        try {
            nodeTreeImport = new importNodeTree(data, funct);
            nodeTreeImport.go();
        } catch (err) {
            onError("Error importing nodetree: " + err.message);
            throw err;
        }
    })
    .then(function() { // Ask server if nodetree valid
        return postGo();
    })
    .then(onSuccess);
});
