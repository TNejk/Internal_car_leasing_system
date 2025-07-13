from pydantic import BaseModel, Field
from typing import Annotated

class ReportList(BaseModel):
  reports: Annotated[list[str], Field(examples=["['/app/reports/2025-01-21 ICLS_report.xlsx']"],
                                      description="A list containing relative paths to the report directory. ")]
