import tempfile
import os
from flask import Flask, request, redirect, send_file
from skimage import io
import base64
import glob
import numpy as np
import random

app = Flask(__name__)

main_html = """
<html>
<head>
  <style>
    .color-btn {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: 2px solid black;
      margin: 5px;
      cursor: pointer;
    }
    #color-palette {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
    }
  </style>
</head>

<script>
  var mousePressed = false;
  var lastX, lastY;
  var ctx;
  var currentColor = 'black';
  var color_random;
  var poligono_random;

  function InitThis() {
      ctx = document.getElementById('myCanvas').getContext("2d");

      ctx.fillStyle = "white";
      ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

      var poligonos = ["bandera"];
      var colores = ["roja", "verde", "azul", "amarilla", "naranja"];

      poligono_random = poligonos[Math.floor(Math.random() * poligonos.length)];
      color_random = colores[Math.floor(Math.random() * colores.length)];

      var mensaje = poligono_random + " " + color_random;
      document.getElementById('mensaje').innerHTML = 'Dibuja una ' + mensaje;

      document.getElementById('poligono').value = poligono_random;
      document.getElementById('color').value = color_random;

      $('#myCanvas').mousedown(function (e) {
          mousePressed = true;
          Draw(e.pageX - $(this).offset().left, e.pageY - $(this).offset().top, false);
      });

      $('#myCanvas').mousemove(function (e) {
          if (mousePressed) {
              Draw(e.pageX - $(this).offset().left, e.pageY - $(this).offset().top, true);
          }
      });

      $('#myCanvas').mouseup(function (e) {
          mousePressed = false;
      });
      $('#myCanvas').mouseleave(function (e) {
          mousePressed = false;
      });
  }

  function setColor(color) {
      currentColor = color;
      document.getElementById("current-color").style.backgroundColor = color;
  }

  function Draw(x, y, isDown) {
      if (isDown) {
          ctx.beginPath();
          ctx.strokeStyle = currentColor;
          ctx.lineWidth = 11;
          ctx.lineJoin = "round";
          ctx.moveTo(lastX, lastY);
          ctx.lineTo(x, y);
          ctx.closePath();
          ctx.stroke();
      }
      lastX = x; lastY = y;
  }

  function clearArea() {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  }

  function prepareImg() {
      var canvas = document.getElementById('myCanvas');
      document.getElementById('myImage').value = canvas.toDataURL();
  }
</script>

<body onload="InitThis();">
  <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js" type="text/javascript"></script>

  <div align="center">
      <h1 id="mensaje">Dibujando...</h1>

      <canvas id="myCanvas" width="200" height="200" style="border:2px solid black"></canvas>
      <br/><br/>

      <div id="color-palette">
          <div class="color-btn" style="background-color:#FF0000" onclick="setColor('#FF0000')"></div>
          <div class="color-btn" style="background-color:#00AA00" onclick="setColor('#00AA00')"></div>
          <div class="color-btn" style="background-color:#0000FF" onclick="setColor('#0000FF')"></div>
          <div class="color-btn" style="background-color:#FFD700" onclick="setColor('#FFD700')"></div>
          <div class="color-btn" style="background-color:#FF8000" onclick="setColor('#FF8000')"></div>
          <div class="color-btn" style="background-color:black" onclick="setColor('black')"></div>
      </div>

      <p>Color actual:</p>
      <div id="current-color" style="width:40px; height:40px; border:2px solid black; background-color:black; margin:auto;"></div>
      <br/>

      <button onclick="javascript:clearArea();return false;">Borrar</button>
      <br/><br/>

      <form method="post" action="upload" onsubmit="javascript:prepareImg();" enctype="multipart/form-data">
        <input id="poligono" name="poligono" type="hidden" value="">
        <input id="color" name="color" type="hidden" value="">
        <input id="myImage" name="myImage" type="hidden" value="">
        <input id="bt_upload" type="submit" value="Enviar">
      </form>
  </div>
</body>
</html>
"""

@app.route("/")
def main():
    return(main_html)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        img_data = request.form.get('myImage').replace("data:image/png;base64,","")
        poligono = request.form.get('poligono')
        color = request.form.get('color')

        folder_name = f"{poligono}_{color}"
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        with tempfile.NamedTemporaryFile(delete=False, mode="w+b", suffix='.png', dir=folder_name) as fh:
            fh.write(base64.b64decode(img_data))

        print(f"Imagen guardada en: {folder_name}")
    except Exception as err:
        print("Error al guardar la imagen:")
        print(err)

    return redirect("/", code=302)

@app.route('/prepare', methods=['GET'])
def prepare_dataset():
    images = []
    labels = []
    folders = glob.glob('*_*')

    for folder in folders:
        filelist = glob.glob(f'{folder}/*.png')
        if not filelist:
            continue
        images_read = io.concatenate_images(io.imread_collection(filelist))
        images_read = images_read[:, :, :, :3]
        labels_read = np.array([folder] * images_read.shape[0])
        images.append(images_read)
        labels.append(labels_read)

    images = np.vstack(images)
    labels = np.concatenate(labels)
    np.save('X.npy', images)
    np.save('y.npy', labels)
    return "OK!"

@app.route('/X.npy', methods=['GET'])
def download_X():
    return send_file('./X.npy')

@app.route('/y.npy', methods=['GET'])
def download_y():
    return send_file('./y.npy')

if __name__ == "__main__":
    app.run()
