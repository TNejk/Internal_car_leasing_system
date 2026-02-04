from pathlib import Path
from pydantic import BaseModel, Field
from typing import Annotated

class ReportGet(BaseModel):
  path: Annotated[Path, Field(description="Path and filename to a locally stored excel report.")]
