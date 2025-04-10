import requests
import re
from flask import session, send_file, Response

def get_report(filename):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = f'https://icls.sosit-wh.net/get_report/{filename}'
  response = requests.get(url=url, headers=headers, stream=True)

  if response.status_code == 200:
    return Response(
      response.iter_content(chunk_size=8192),
      content_type=response.headers.get('Content-Type', 'application/octet-stream'),
      headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

  return f"Error {response.status_code}: {response.text}", response.status_code