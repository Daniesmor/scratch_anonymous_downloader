import os
import json
import requests

# Ruta al archivo JSON del proyecto
json_file_path = 'project.json'

# Crear directorios para almacenar los recursos
images_dir = 'images'
sounds_dir = 'sounds'
os.makedirs(images_dir, exist_ok=True)
os.makedirs(sounds_dir, exist_ok=True)

# Cargar el archivo JSON
with open(json_file_path, 'r') as json_file:
    project_data = json.load(json_file)

# Función para descargar archivos
def download_file(url, path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, 'wb') as file:
            file.write(response.content)
        print(f'Descargado: {path}')
    else:
        print(f'Error al descargar {path}')

# Descargar disfraces (costumes)
for target in project_data['targets']:
    for costume in target.get('costumes', []):
        asset_id = costume['assetId']
        extension = costume['dataFormat']
        url = f'https://assets.scratch.mit.edu/{asset_id}.{extension}'
        download_file(url, os.path.join(images_dir, f'{asset_id}.{extension}'))

# Descargar sonidos
for target in project_data['targets']:
    for sound in target.get('sounds', []):
        asset_id = sound['assetId']
        extension = sound['dataFormat']
        url = f'https://assets.scratch.mit.edu/{asset_id}.{extension}'
        download_file(url, os.path.join(sounds_dir, f'{asset_id}.{extension}'))

print('Descarga de recursos completa.')
