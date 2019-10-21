//get request, change functions.json url to wherever yours is
$.get("/api/funcs", function(data) {
    funct = new functions(data);
    funct.ui();
})
$.get("/api/nodes", function(data) {
    nodeTreeImport = new importNodeTree(data, funct);
    nodeTreeImport.go();
})
