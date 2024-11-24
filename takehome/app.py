"""
Entry point of application and API calls
"""
from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI,  HTTPException, status, Depends
from typing import Optional
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm

from takehome.config import settings
from takehome.repository.database import engine, Base
from takehome.models import Project, Candidate, ProjectCreateRequest, CandidateCreateRequest, FormTeamRequest
from takehome.models import FormTeamResponse, CandidateResponse, SkillResponse, Skill, ProjectListResponse, CandidateListResponse
from takehome.models import Token
from takehome.repository.database_utils import create_project_db, get_project_by_id, delete_project_db, update_project_db
from takehome.repository.database_utils import get_candidate_by_id, delete_candidate_db, update_candidate_db, create_candidate_db
from takehome.repository.database_utils import get_project_list, get_candidate_list
from takehome.utils import form_team_helper, fetch_special_score, fetch_parallel_scores
from takehome.cache import redis_client
from takehome.constants import SPECIAL_SCORE_REDIS_KEY
from takehome.authy import create_access_token, authenticate_user, get_current_user
from takehome.logs import LoggingContext, LOGGER

# ============================ Team Matcher Server ============================

# Note to challengers:
# You may add additional files as needed to complete the challenge.

# Docs:
# - FastAPI: https://fastapi.tiangolo.com/

# You may modify this file as needed.

# =============================================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
templates = Jinja2Templates(directory=Path(BASE_DIR, "templates"))

# Create the database tables
@app.on_event("startup")
def startup_event():
    LOGGER.info("On startup_event")
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    LOGGER.info("Secret Key: %s", settings.AUTH_SECRET_KEY)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/project/", response_model=Project)
def get_project(id: int, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="get_project", project_id=id)
    LOGGER.info(f"Request received", extra=local_logging_context.store)
    
    project_db = get_project_by_id(id)
    if not project_db:
        LOGGER.warn(f"Invalid Request, Project with provided id does not exists", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Project with provided id does not exists",
        )
    
    skill_response = []
    for skill in project_db.skills:
        skill_tmp = Skill(name=skill.name, expertise_level=skill.expertise_level)
        skill_response.append(skill_tmp)

    project_response = Project(id=project_db.id, title=project_db.title, skills=skill_response)
    LOGGER.debug(f"Request successfully completed ", extra=local_logging_context.store)
    return project_response

@app.post("/project/", response_model=Project)
def create_project(project: ProjectCreateRequest, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="create_project")
    LOGGER.debug(f"Request received with input as {project.dict()}", extra=local_logging_context.store)
    new_project = create_project_db(project, local_logging_context)
    return new_project

@app.delete("/project/")
def delete_project(id: int, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="delete_project", project_id=id)
    LOGGER.debug(f"Request received", extra=local_logging_context.store)
    delete_project_db(id)
    LOGGER.debug(f"Request successfully completed", extra=local_logging_context.store)
    return {"message": "success"}

@app.put("/project/", response_model=Project)
def update_project(project: Project, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="update_project", project_id=project.id)
    LOGGER.debug(f"Request received with input as {project.dict()}", extra=local_logging_context.store)
    updated_project = update_project_db(project)
    LOGGER.debug(f"Request successfully completed", extra=local_logging_context.store)
    return updated_project

@app.get("/candidate/", response_model=CandidateResponse)
def get_candidate(id: int, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="get_candidate", candidate_id=id)
    LOGGER.info(f"Request received", extra=local_logging_context.store)
    candidate_db = get_candidate_by_id(id)
    if not candidate_db:
        LOGGER.warn(f"Invalid Request, Candidate with provided id does not exists", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Candidate with provided id does not exists",
        )
    
    payload = {'candidate_id': str(candidate_db.id)}
    payload['skills'] = [{'skill': skill.name, 'score': skill.expertise_level}  for skill in candidate_db.skills]
    special_score = fetch_special_score(payload)

    local_logging_context.upsert(special_score_payload=payload)
    LOGGER.debug(f"Fetching special score", extra=local_logging_context.store)
    local_logging_context.remove_keys(["special_score_payload"])

    skill_response = []
    for skill in candidate_db.skills:
        skill_tmp = SkillResponse(name=skill.name, expertise_level=skill.expertise_level, special_score=special_score[skill.name])
        skill_response.append(skill_tmp)

    candidate_response = CandidateResponse(id=candidate_db.id, name=candidate_db.name, skills=skill_response)
    LOGGER.debug(f"Request successfully completed ", extra=local_logging_context.store)
    return candidate_response

@app.post("/candidate/", response_model=Candidate)
def create_candidate(candidate: CandidateCreateRequest, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="create_candidate")
    LOGGER.debug(f"Request received with input as {candidate.dict()}", extra=local_logging_context.store)
    new_candidate = create_candidate_db(candidate, local_logging_context)
    #deleting cached special scores
    redis_client.delete(SPECIAL_SCORE_REDIS_KEY.format(new_candidate.id))
    return new_candidate

@app.delete("/candidate/")
def delete_candidate(id: int, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="delete_candidate", candidate_id=id)
    LOGGER.debug(f"Request received", extra=local_logging_context.store)
    delete_candidate_db(id)

    #deleting cached special scores
    redis_client.delete(SPECIAL_SCORE_REDIS_KEY.format(id))
    LOGGER.debug(f"Request succesfully completed", extra=local_logging_context.store)
    return {"message": "success"}

@app.put("/candidate/", response_model=Candidate)
def update_candidate(candidate: Candidate, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="update_candidate", candidate_id=candidate.id)
    LOGGER.debug(f"Request received with input as {candidate.dict()}", extra=local_logging_context.store)
    updated_candidate = update_candidate_db(candidate)

    #deleting cached special score
    redis_client.delete(SPECIAL_SCORE_REDIS_KEY.format(candidate.id))
    candidate_response = Candidate(id=updated_candidate.id, name=updated_candidate.name, skills=updated_candidate.skills)
    LOGGER.debug(f"Request succesfully completed", extra=local_logging_context.store)
    return candidate_response

@app.post('/api/form-team', response_model=FormTeamResponse)
def form_team(request_model: FormTeamRequest, user=Depends(get_current_user)):
    local_logging_context: LoggingContext = LoggingContext(source="form_team", request_model = request_model)
    LOGGER.debug(f"Request received", extra=local_logging_context.store)
    project = get_project_by_id(request_model.project_id)
    if not project:
        LOGGER.warn(f"Invalid Request, Project with provided {request_model.project_id} does not exists", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Project with provided id does not exists",
        )
    
    candidates = []
    for candidate_id in request_model.candidate_ids:
        candidate = get_candidate_by_id(candidate_id)
        LOGGER.warn(f"Invalid Request, Candidate with id {candidate_id} does not exists", extra=local_logging_context.store)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Request, Candidate with id {} does not exists".format(candidate_id),
            )
        candidates.append(candidate)

    if request_model.team_size > len(candidates):
        LOGGER.warn(f"Invalid Request, team_size cannot be greater than candidate list", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, team_size cannot be greater than candidate list",
        )
    
    optimal_team = form_team_helper(request_model.team_size, candidates, project, local_logging_context)
    LOGGER.debug(f"Request succesfully completed", extra=local_logging_context.store)
    return optimal_team

@app.get("/projects/", response_model=ProjectListResponse)
def get_projects(page_no: int, size: int, title: Optional[str] = None,
    skill_required: Optional[str] = None,
    sort_by: Optional[str] = "id",
    order: Optional[str] = "asc",
    user=Depends(get_current_user)
    ):
    local_logging_context: LoggingContext = LoggingContext(source="get_projects")
    LOGGER.debug(f"Request received ", extra=local_logging_context.store)
    # Validate pagination parameters
    if page_no < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, page_no must be greater than 0",
        )
    if size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, size must be greater than 0",
        )

    if sort_by not in ["id", "title"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, possible values of sort_by are id, title",
        )
    
    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, possible values of order are asc, desc",
        )

    # Calculate the skip value based on page_no and size
    skip = (page_no - 1) * size

    return get_project_list(skip, size, title, skill_required, sort_by, order)

@app.get("/candidates/", response_model=CandidateListResponse)
def get_candidates(page_no: int, size: int, name: Optional[str] = None,
    skill_required: Optional[str] = None,
    sort_by: Optional[str] = "id",
    order: Optional[str] = "asc",
    user=Depends(get_current_user) 
    ):
    local_logging_context: LoggingContext = LoggingContext(source="get_candidates")
    LOGGER.debug(f"Request received ", extra=local_logging_context.store)

    # Validate pagination parameters
    if page_no < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, page_no must be greater than 0",
        )
    if size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, size must be greater than 0",
        )

    if sort_by not in ["id", "name"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, possible values of sort_by are id, name",
        )
    
    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, possible values of order are asc, desc",
        )

    # Calculate the skip value based on page_no and size
    skip = (page_no - 1) * size

    candidates_db = get_candidate_list(skip, size, name, skill_required, sort_by, order)

    payloads = []
    for candidate in candidates_db:
        payload = {'candidate_id': str(candidate.id)}
        payload['skills'] = [{'skill': skill.name, 'score': skill.expertise_level} for skill in candidate.skills]
        payloads.append(payload)
    
    special_scores = fetch_parallel_scores(payloads)

    candidate_responses = []
    for candidate in candidates_db:
        special_score = special_scores[str(candidate.id)]
        skill_response = []
        for skill in candidate.skills:
            skill_tmp = SkillResponse(name=skill.name, expertise_level=skill.expertise_level, special_score=special_score[skill.name])
            skill_response.append(skill_tmp)
        candidate_tmp = CandidateResponse(id=candidate.id, name=candidate.name, skills=skill_response)
        candidate_responses.append(candidate_tmp)
    
    return CandidateListResponse(size=len(candidate_responses), candidates=candidate_responses)