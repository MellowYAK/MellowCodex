"""Validated development inputs; authorization is supplied by the human session."""
from pydantic import BaseModel, ConfigDict, Field

class FileChange(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str=Field(min_length=1,max_length=700)
    base_hash:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')
    content:str=Field(max_length=1_000_000)

class PatchProposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    candidate_id:str=Field(pattern='^[a-f0-9]{32}$')
    expected_revision:int=Field(ge=0)
    changes:list[FileChange]=Field(min_length=1,max_length=50)

class WorkPacket(BaseModel):
    model_config=ConfigDict(extra='forbid')
    project_id:str=Field(pattern='^[a-f0-9]{32}$')
    human_request_original:str=Field(min_length=1,max_length=30000)
    constraints:list[str]=Field(default_factory=list,max_length=80)
    acceptance:list[str]=Field(min_length=1,max_length=80)
    revision:int=Field(default=0,ge=0)
    activation_requested:bool=False
