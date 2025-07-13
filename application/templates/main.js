function navFunction() {
        var x = document.getElementById("birdNav");
        if (x.className === "topnav") {
            x.className += " responsive";
        } else {
            x.className = "navbar";
        }
    }

    function takePicture() {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onreadystatechange = function () {
            if (xmlhttp.readyState === 4 && xmlhttp.status === 200) {
                var response = xmlhttp.responseText; // hier kannst du etwas mit der Rückgabe machen
            }
        };
        xmlhttp.open("GET", "http://127.0.0.1/cam", true);
        xmlhttp.send();
    }

    function toggleFullScreen(element) {
      // Falls kein Fullscreen aktiv ist, aktiviere ihn
      if (!document.fullscreenElement) {
        element.requestFullscreen().catch(err => {
          console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
        });
      } else {
        // Ansonsten verlasse den Fullscreen-Modus
        document.exitFullscreen();
      }
    }

    window.addEventListener("beforeunload", function () {
        navigator.sendBeacon('/stop_stream');
    })
