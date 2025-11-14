import tempfile
import os
from dotenv import load_dotenv
from flask import Flask, request, redirect, send_file
from skimage import io
import base64
import glob
import numpy as np
import random
import unicodedata
import uuid

from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "pc3_dataset"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def normalize_filename(text):
    """Remueve acentos y caracteres especiales del texto"""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

@app.route("/")
def main():
    return(main_html)

@app.route('/upload', methods=['POST'])
def upload():
    try:
        # obtener base64 y limpiar el encabezado
        img_data = request.form.get('myImage').replace("data:image/png;base64,", "")

        poligono = request.form.get('poligono')
        color = request.form.get('color')

        # normalizar nombre (remover acentos)
        poligono_clean = normalize_filename(poligono)
        color_clean = normalize_filename(color)

        # generar nombre único
        file_name = f"{poligono_clean}_{color_clean}_{uuid.uuid4()}.png"

        # convertir base64 → bytes
        file_bytes = base64.b64decode(img_data)

        # subir a Supabase
        res = supabase.storage.from_(BUCKET_NAME).upload(
            file_name,
            file_bytes,
            file_options={"content-type": "image/png"}
        )

        # manejar respuesta de Supabase
        if hasattr(res, 'error') and res.error:
            print("Error al subir a Supabase:", res.error)
        else:
            print("Imagen subida correctamente:", file_name)
            # obtener URL pública
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
            print("URL pública:", public_url)

    except Exception as err:
        print("Error al subir la imagen:")
        print(err)

    return redirect("/", code=302)

@app.route('/prepare', methods=['GET'])
def prepare_dataset():
    images = []
    labels = []
    
    try:
        # listar todos los archivos en el bucket
        files = supabase.storage.from_(BUCKET_NAME).list()
        
        # agrupar archivos por etiqueta (poligono_color)
        files_by_label = {}
        for file in files:
            file_name = file['name']
            # extraer etiqueta: "bandera_roja_uuid.png" → "bandera_roja"
            label = '_'.join(file_name.split('_')[:-1])
            
            if label not in files_by_label:
                files_by_label[label] = []
            files_by_label[label].append(file_name)
        
        # procesar cada etiqueta
        for label, file_names in files_by_label.items():
            label_images = []
            
            for file_name in file_names:
                try:
                    # descargar archivo de Supabase
                    file_data = supabase.storage.from_(BUCKET_NAME).download(file_name)
                    
                    # convertir bytes a imagen
                    from io import BytesIO
                    img = io.imread(BytesIO(file_data))
                    if img.shape[-1]==4:
                        img = img[:, :, :3]
                    label_images.append(img)
                except Exception as e:
                    print(f"Error al descargar {file_name}: {e}")
                    continue
            
            if label_images:
                # apilar imágenes de esta etiqueta
                images_array = np.array(label_images)
                labels_array = np.array([label] * len(label_images))
                
                images.append(images_array)
                labels.append(labels_array)
        
        # combinar todas las imágenes y etiquetas
        if images:
            images = np.vstack(images)
            labels = np.concatenate(labels)
            np.save('X.npy', images)
            np.save('y.npy', labels)
            return f"OK! {len(images)} imágenes procesadas"
        else:
            return "No se encontraron imágenes"
    
    except Exception as err:
        print("Error al preparar dataset:")
        print(err)
        return f"Error: {err}"

@app.route('/X.npy', methods=['GET'])
def download_X():
    return send_file('./X.npy')

@app.route('/y.npy', methods=['GET'])
def download_y():
    return send_file('./y.npy')

if __name__ == "__main__":
    app.run()
