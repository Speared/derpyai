var minimap = document.getElementById("minimap_overlay");
var minimap_context = minimap.getContext("2d");
for (var x = 0; x < minimap.width; x++){
		for(var y = 0; y < minimap.height; y++){
				data_element = document.createElement("div");
				data_element.className = `minimap_data`
				data_element.id = `x:${x} y:${y}`
				var p = minimap_context.getImageData(x, y, 1, 1).data; 
				console.log(p)
				data_element.innerHTML = [ p[0], p[1], p[2] ]
				minimap.appendChild(data_element)
		}
}