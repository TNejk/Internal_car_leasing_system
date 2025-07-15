import os
from pathlib import Path

def find_reports_directory():
  """Find the reports directory at the volume mount location."""
  reports_path = "/app/reports"

  if os.path.exists(reports_path) and os.path.isdir(reports_path):
    print(f"DEBUG: Found reports directory at: {reports_path}")
    # List contents of reports directory
    try:
      print(f"DEBUG: Contents of reports directory:")
      for item in os.listdir(reports_path):
        item_path = os.path.join(reports_path, item)
        print(f"DEBUG:   {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
    except Exception as e:
      print(f"DEBUG: Error listing reports directory: {e}")
    return reports_path

  print("ERROR: /app/reports directory not found - check Docker volume mount")
  print("HINT: Volume should be: -v /home/systemak/icls/api/reports:/app/reports")
  return None

def get_reports_paths(folder_path):
  """Get list of report file paths relative to the reports directory."""
  try:
    with os.scandir(folder_path) as entries:
      return [entry.path.removeprefix("/app/reports/") for entry in entries if entry.is_file()]
  except OSError:  # Specific exception > bare except!
    return None
