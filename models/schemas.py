from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime

class IssueStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"

class IssueBase(BaseModel):
    title: str = Field(..., max_length=200)
    body: Optional[str] = None
    status: IssueStatus = IssueStatus.OPEN
    labels: List[str] = []

class IssueCreate(IssueBase):
    pass

class IssueUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    body: Optional[str] = None
    status: Optional[IssueStatus] = None
    labels: Optional[List[str]] = None

class Issue(IssueBase):
    id: int
    number: int
    repo_full_name: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class NewIssue(BaseModel):
    title: str
    body: str

class IssueSummary(BaseModel):
    repo_full_name: str
    number: int
    title: str
    body: str

class Command(BaseModel):
    issue: IssueSummary
    command: str