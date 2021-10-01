const thumbsCont = document.getElementById("thumbs-main");
const nrOfImages = 15; //nr of half of the images in thumbs container -1

function loadItem(catalog, idx) {
    let main = document.getElementById("main");
    let item = catalog[idx];
    if (item.type == "img") {
        let img = document.createElement("img");
        img.classList.add("main-image");
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
        vid.classList.add("main-image");
        vid.classList.add("rotate0");
        main.replaceChild(vid, main.childNodes[0]);
    }

    document.getElementById("prev").onclick = function () {
        loadItem(catalog, calculateIndex(idx, -1, catalog.length));
        return false;
    };

    document.getElementById("next").onclick = function () {
        loadItem(catalog, calculateIndex(idx, 1, catalog.length));
    };

    document.onkeydown = function(event) {
        const keyDown = event.key;
        switch (keyDown) {
            case "ArrowLeft":
                loadItem(catalog, calculateIndex(idx, -1, catalog.length));
                break;
            case 'ArrowRight':
                loadItem(catalog, calculateIndex(idx, 1, catalog.length));
                break;
        }
    };

    loadThumbnails(catalog, idx);
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

function loadThumbnails(catalog, idx) {
    if (thumbsCont == null) {
        return false;
    }
    //remove previous images from thumbs container
    while (thumbsCont.lastChild) {
        thumbsCont.removeChild(thumbsCont.lastChild);
    }

    let catalogLength = catalog.length;
    let firsIdx = calculateIndex(idx, - nrOfImages, catalogLength);
    let lastIdx = calculateIndex(idx, nrOfImages, catalogLength);

    for (i = - nrOfImages; i <= nrOfImages; i++) {
        if (i == 0) {
            addMediaToThumbs(catalog, idx, i, true);
        } else {
            addMediaToThumbs(catalog, idx, i);
        }
    }

    document.getElementById("thumbs-prev").onclick = function () {
        thumbsCont.removeChild(thumbsCont.lastChild);
        lastIdx = calculateIndex(lastIdx, -1, catalogLength);
        firsIdx = calculateIndex(firsIdx, +1, catalogLength);
        let imgContainer = createImageContainer(false);
        thumbsCont.insertBefore(imgContainer, thumbsCont.firstChild);
        loadMdiaItem(imgContainer, catalog, firsIdx);
    };

    document.getElementById("thumbs-next").onclick = function () {
        thumbsCont.removeChild(thumbsCont.firstChild);
        lastIdx = calculateIndex(lastIdx, +1, catalogLength);
        firsIdx = calculateIndex(firsIdx, -1, catalogLength);
        addMediaToThumbs(catalog, lastIdx, 0, false);
    };

    thumbsCont.style.width = calculateWidthForContainer(nrOfImages, 100) + "px";
    thumbsCont.style.marginLeft = calculateMarginLeft(nrOfImages, 100) + "px";
}

function calculateIndex(originalIndex, step, dataLength) {
    result = (originalIndex + step + dataLength) % dataLength;
    if (result < 0) { //in case if there are less images then nrOfImages
        result += dataLength;
    } 
    return result;
}

function addMediaToThumbs(catalog, idx, step, selected) {
    let imgContainer = createImageContainer(selected)
    thumbsCont.appendChild(imgContainer);

    let cIdx = calculateIndex(idx, step, catalog.length);
    loadMdiaItem(imgContainer, catalog, cIdx);
}

function createImageContainer(selected) {
    let imgCont = document.createElement('div');
    imgCont.classList.add('thumbs-div');
    if (selected) {
        imgCont.classList.add('selected');
    }
    return imgCont;
}

function loadMdiaItem(parentContainer, catalog, index) {
    let cItem = catalog[index];
    let cImg = document.createElement("img");
    if (cItem.hasOwnProperty("thumbnail")) {
/*        fetch(cItem.thumbnail)
        .then(res => {
            if (res.ok) {
                cImg.src = cItem.thumbnail;
            } else {
                cImg.src = "noThumbnail.jpg";
            }
        }).catch(err => cImg.src = "noThumbnail.jpg");*/
        cImg.src = cItem.thumbnail;
        //if the image can not be loaded
        cImg.addEventListener("error", function(event) {
            event.target.src = "noThumbnail.jpg";
            event.onerror = null;
        });
    } else {
        cImg.src = "noThumbnail.jpg";
    }
    cImg.onclick = function () {
        loadItem(catalog, index);
    }
    
    parentContainer.appendChild(cImg);
}

function calculateWidthForContainer(nrOfImages, imageWidth) {
    return (2 * nrOfImages + 1) * imageWidth;
}

function calculateMarginLeft(nrOfImages, imageWidth) {
    let cWidth = calculateWidthForContainer(nrOfImages, imageWidth);
    let visibleWidth = document.getElementById("thumbs").offsetWidth;
    //console.log(visibleWidth);
    let marginLeftValue = Math.round(- (cWidth - visibleWidth + 3 * imageWidth) / 2);
    //console.log(marginLeftValue);
    return marginLeftValue;
}


init();