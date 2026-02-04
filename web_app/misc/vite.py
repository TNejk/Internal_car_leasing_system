import json

def get_vite_asset_path(assets):
  result = []
  for asset in assets:
    pair = {}
    path = 'src/' + asset + '.js'
    with open("static/dist/.vite/manifest.json") as f:
      manifest = json.load(f)

    pair['script'] = '/static/dist/' + manifest.get(path)['file']
    if 'css' in manifest.get(path).keys():
      pair['style'] = '/static/dist/' + manifest.get(path)['css'][0]

    result.append(pair)

  return result

