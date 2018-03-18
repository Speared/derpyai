//I belive these are the map dimensions
//from enums.js
//exports.gxm = 80;
//exports.gym = 70;
//the map is centered in the x dimension and scaled to fit on the y
//tiles are squares

var minimap = document.getElementById("minimap");
var minimap_context = minimap.getContext("2d");
var maxX = 80
var maxY = 70
var leftbuffer = (minimap.width % maxX) / 2
var tileHeight = minimap.height / maxY
console.log(minimap.width, minimap.height)
console.log(tileHeight)
for (var x = 0; x < maxX; x++){
		for(var y = 0; y < maxY; y++){
				data_element = document.createElement("div");
				data_element.className = `minimap_data`
				data_element.id = [x, y]
				var p = minimap_context.getImageData((x * tileHeight) + leftbuffer, 
														y * tileHeight, 1, 1).data; 
				data_element.innerHTML = [p[0], p[1], p[2]]
				minimap.appendChild(data_element)
		}
}
