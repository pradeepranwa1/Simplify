"""
Models for request, response and general purpose use
"""
from pydantic import BaseModel, Field, conlist
from typing import List

class Skill(BaseModel):
    name: str
    expertise_level: int = Field(ge=1, le=10, description="Skill expertise level (1-10)")

class Project(BaseModel):
    id: int
    title: str
    skills: List[Skill]

class Candidate(BaseModel):
    id: int
    name: str
    skills: List[Skill]

class ProjectCreateRequest(BaseModel):
    title: str
    skills: List[Skill]


class CandidateCreateRequest(BaseModel):
    name: str
    skills: List[Skill]

class FormTeamRequest(BaseModel):
    project_id: int
    candidate_ids: conlist(int, min_length=1, max_length=100)
    team_size: int = Field(ge=1, le=10)

class FormTeamScore(BaseModel):
    skill: str
    score: float

class FormTeamCandidateResponse(BaseModel):
    candidate_id : int
    name : str
    assigned_skills: List[str]
    special_score: List[FormTeamScore]

class FormTeamResponse(BaseModel):
    team : List[FormTeamCandidateResponse]
    total_expertise : int
    coverage : float

class SkillResponse(BaseModel):
    name: str
    expertise_level: int = Field(ge=1, le=10, description="Skill expertise level (1-10)")
    special_score: float

class CandidateResponse(BaseModel):
    id: int
    name: str
    skills: List[SkillResponse]

class ProjectListResponse(BaseModel):
    size: int
    projects: List[Project]

class CandidateListResponse(BaseModel):
    size: int
    candidates: List[CandidateResponse]

class User(BaseModel):
    username: str
    hashed_password: str

class UserDetials(BaseModel):
    username: str
    #more more variables as required

class Token(BaseModel):
    access_token: str
    token_type: str
