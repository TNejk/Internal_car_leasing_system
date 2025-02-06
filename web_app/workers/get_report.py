import requests
import re
from flask import session, send_file


def get_report(email, role, filename):
  filename = filename.replace(' ', '%20')  # URL encode spaces
  print(filename)

  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = f'https://icls.sosit-wh.net/get_report/{filename}?email={email}&role={role}'

  request = requests.get(url=url, headers=headers, stream=True)

  if request.status_code == 200:
    # Get filename from Content-Disposition header
    content_disposition = request.headers.get('Content-Disposition', f'attachment; filename={filename}')
    filename = content_disposition.split('=')[1].strip('"')

    # Sanitize filename (replace problematic characters)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    file_path = f"./{filename}"  # Ensure safe file path

    # Write file in chunks
    with open(file_path, "wb") as f:
      for chunk in request.iter_content(chunk_size=8192):
        f.write(chunk)

    return send_file(file_path, as_attachment=True)

  return "Failed to download file", 500
