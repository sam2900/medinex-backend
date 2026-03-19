from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, Field


class PageText(BaseModel):
    page_num: int
    text: str


class TextChunk(BaseModel):
    chunk_id: str
    pdf_name: str
    page_num: int
    text: str


class RetrievedChunk(BaseModel):
    chunk_id: str
    page_num: int
    text: str
    score: Optional[float] = None


class RetrievalMatch(BaseModel):
    chunk_id: str
    page_num: int
    text: str
    score: Optional[float] = None


class ExtractedField(BaseModel):
    value: Optional[str] = None
    method: Optional[str] = None
    confidence: Optional[float] = None
    source_chunk_id: Optional[str] = None
    source_page_num: Optional[int] = None
    raw_evidence: Optional[str] = None
    warning: Optional[str] = None


class FieldEvidence(BaseModel):
    field_name: str
    query: str
    matches: List[RetrievedChunk] = Field(default_factory=list)


class Table2StudyDetails(BaseModel):
    pdf_name: str
    protocol_title: ExtractedField
    protocol_number: ExtractedField
    phase: ExtractedField
    document_date: ExtractedField
    
class Table3VisitRow(BaseModel):
    visit_title: str
    visit_id: str


class Table3VisitDetails(BaseModel):
    pdf_name: str
    visits: List[Table3VisitRow] = Field(default_factory=list)
    

class Table4ProcedureRow(BaseModel):
    procedure: str
    code: str = ""
    unit_basis: str = ""
    budget: str = ""
    visit_values: dict[str, str] = Field(default_factory=dict)


class Table4ProcedureDetails(BaseModel):
    pdf_name: str
    visit_columns: List[str] = Field(default_factory=list)
    procedures: List[Table4ProcedureRow] = Field(default_factory=list)
    

class Table5NonProcedureRow(BaseModel):
    non_procedure_item: str
    code: str = ""
    unit_basis: str = ""
    budget: str = ""
    visit_values: dict[str, str] = Field(default_factory=dict)


class Table5NonProcedureDetails(BaseModel):
    pdf_name: str
    visit_columns: List[str] = Field(default_factory=list)
    items: List[Table5NonProcedureRow] = Field(default_factory=list)
    

class Table6SiteFeeRow(BaseModel):
    site_fee_description: str
    code: str = ""
    unit_basis: str = ""
    unit_cost: str = ""


class Table6SiteFeeDetails(BaseModel):
    pdf_name: str
    items: List[Table6SiteFeeRow] = Field(default_factory=list)
    

class Table7ConditionalProcedureRow(BaseModel):
    conditional_procedure: str
    code: str = ""
    unit_basis: str = ""
    unit_cost: str = ""
    overhead: str = ""
    unit_cost_incl_overhead: str = ""


class Table7ConditionalProcedureDetails(BaseModel):
    pdf_name: str
    items: List[Table7ConditionalProcedureRow] = Field(default_factory=list)
    

class SourceTableChoice(BaseModel):
    label: str
    page_hint: Optional[int] = None
    reason: str = ""


class ProtocolSourceSelection(BaseModel):
    pdf_name: str
    source_type: str = ""
    confidence: str = ""
    primary_tables: List[SourceTableChoice] = Field(default_factory=list)
    secondary_tables: List[SourceTableChoice] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    
class Table8PatientCostRow(BaseModel):
    patient_cost_item: str
    code: str = ""
    unit_basis: str = ""
    unit_cost: str = ""


class Table8PatientCostDetails(BaseModel):
    pdf_name: str
    items: List[Table8PatientCostRow] = Field(default_factory=list)
    
class Table1BudgetRow(BaseModel):
    category: str
    details: str = ""


class Table1BudgetEstimationDetails(BaseModel):
    pdf_name: str
    items: List[Table1BudgetRow] = Field(default_factory=list)