//get the minimap as a png
//https://stackoverflow.com/questions/38316402/how-to-save-a-canvas-as-png-in-selenium
var minimap = document.getElementById("minimap");
var data = minimap.toDataURL().substring(21);
return data
