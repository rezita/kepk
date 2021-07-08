function loadItem(catalog, idx) {
    let main = document.getElementById("main");
    let item = catalog[idx];
    if (item.type == "img") {
        let img = document.createElement("img");
        img.classList.add("content");
        img.src = item.src;
        let orient = item.orient
        switch (orient) {
            case 6:
                img.classList.add("rotate90");
                break;
            case 3:
                img.classList.add("rotate180");
                break;
            case 8:
                img.classList.add("rotate270");
                break;
            default:
                img.classList.add("rotate0");
        }
        main.replaceChild(img, main.childNodes[0]);
    } else if (item.type == "vid") {
        let vid = document.createElement("video");
        vid.src = item.src;
        vid.controls = true;
        vid.classList.add("content");
        vid.classList.add("rotate0");
        main.replaceChild(vid, main.childNodes[0]);
    }

    document.getElementById("prev").onclick = function () {
        if (idx == 0) {
            loadItem(catalog, catalog.length - 1);
        } else {
            loadItem(catalog, idx - 1);
        }
        return false;
    };

    document.getElementById("next").onclick = function () {
        if (idx == catalog.length - 1) {
            loadItem(catalog, 0);
        } else {
            loadItem(catalog, idx + 1);
        }
    };
}

function init() {
    fetch("photos.json")
        .then(function (catalog) {
            return catalog.json();
        })
        .then(function (jsonCatalog) {
            loadItem(jsonCatalog, 0);
        })
}

init();