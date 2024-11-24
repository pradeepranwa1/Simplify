"""
Used for any interactions with database, READ/WRITE/UPDATE/DELETE
"""
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload

from takehome.repository.database_models import CandidateDB, ProjectDB, CandidateSkillDB, ProjectSkillDB
from takehome.repository.database import get_db
from takehome.models import Project, Candidate, ProjectCreateRequest, CandidateCreateRequest, Skill
from takehome.models import ProjectListResponse
from takehome.logs import LoggingContext, LOGGER

def get_project_by_title(title: str) -> ProjectDB:
    """
    Fetch a project from the database by its title.
    Args:
        title (str): The title of the project to search for.
    Returns:
        ProjectDB: The project instance corresponding to the title, or None if not found.
    """
    with get_db() as db:
        project = db.query(ProjectDB).filter(ProjectDB.title == title).first()
        return project

def get_project_by_id(id: int) -> ProjectDB:
    """
    Fetch a project from the database by its ID, including its skills using joinedload.
    Args:
        id (int): The unique identifier of the project.
    Returns:
        ProjectDB: The project instance corresponding to the ID, or None if not found.
    """
    with get_db() as db:
        project = db.query(ProjectDB).options(joinedload(ProjectDB.skills)).filter(
                        ProjectDB.id == id).first()
        return project

def create_project_db(project: ProjectCreateRequest, local_logging_context: LoggingContext) -> Project:
    """
    Create a new project in the database with the provided data.
    Args:
        project (ProjectCreateRequest): The project details, and associated skills.
    Returns:
        Project: The formated project response object with its skills.
    Raises:
        HTTPException: If a project with the same title already exists.
    """
    #check if project with same title exist
    _check_project = get_project_by_title(project.title)
    if _check_project:
        LOGGER.warn(f"Invalid Request, Project already exists with id as {_check_project.id}", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Project already exists",
        )

    with get_db() as db:
        new_project = ProjectDB(title=project.title)
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        for skill in project.skills:
            new_skill = ProjectSkillDB(
                name=skill.name,
                expertise_level=skill.expertise_level,
                project_id=new_project.id,
            )
            db.add(new_skill)

        db.commit()
        db.refresh(new_project)

        local_logging_context.upsert(project_id=new_project.id)
        LOGGER.debug("Created New project", extra=local_logging_context.store)
        return Project(
            id=new_project.id,
            title=new_project.title,
            skills=[
                Skill(name=skill.name, expertise_level=skill.expertise_level)
                for skill in new_project.skills
            ],
        )

def delete_project_db(project_id: int) -> None:
    """
    Delete a project from the database by its ID, including its associated skills.
    Args:
        project_id (int): The ID of the project to be deleted.
    Raises:
        HTTPException: If the project with the provided ID does not exist.
    """
    _project = get_project_by_id(project_id)
    if not _project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Project with provided id does not exists",
        )
    
    with get_db() as db:
        db.query(ProjectSkillDB).filter(
            ProjectSkillDB.project_id == _project.id).delete()
        db.delete(_project)
        db.commit()

def update_project_db(project: Project) -> Project:
    """
    Update the details of an existing project, including its skills.
    Args:
        project (Project): The project data to update, including title and skills.
    Returns:
        Project: The formated project response with skills.
    Raises:
        HTTPException: If the project does not exist or is missing an ID.
    """
    if not project.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, project id is compulsory",
        )
    
    with get_db() as db:
        _project = db.query(ProjectDB).filter(ProjectDB.id == project.id).first()
        if not _project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Request, candidate with provided id does not exists",
            )
        
        # Update basic candidate details
        _project.title = _project.title
        
        existing_skills = {skill.name for skill in _project.skills}
        input_skills = {skill.name for skill in project.skills}

        # Remove skills not in the input
        for skill in _project.skills:
            if skill.name not in input_skills:
                db.delete(skill)

        # Add or update skills
        for skill in project.skills:
            if skill.name in existing_skills:
                # Update existing skill
                existing_skill = next((s for s in _project.skills if s.name == skill.name), None)
                if existing_skill:
                    existing_skill.name = skill.name
                    existing_skill.expertise_level = skill.expertise_level
            else:
                # Add new skill
                new_skill = ProjectSkillDB(
                    name=skill.name,
                    expertise_level=skill.expertise_level,
                    project_id=_project.id,
                )
                db.add(new_skill)

        #update command
        db.commit()
        db.refresh(_project)
        return Project(
            id=_project.id,
            title=_project.title,
            skills=[
                Skill(name=skill.name, expertise_level=skill.expertise_level)
                for skill in _project.skills
            ],
        )

def get_candidate_by_name(name: str) -> CandidateDB:
    """
    Fetch a candidate from the database by their name.
    Args:
        name (str): The name of the candidate to search for.
    Returns:
        CandidateDB: The candidate instance corresponding to the name, or None if not found.
    """
    with get_db() as db:
        candidate = db.query(CandidateDB).filter(CandidateDB.name == name).first()
        return candidate

def get_candidate_by_id(id: int) -> CandidateDB:
    """
    Fetch a candidate from the database by their ID, including their skills.
    Args:
        id (int): The unique identifier of the candidate.
    Returns:
        CandidateDB: The candidate instance corresponding to the ID, or None if not found.
    """
    with get_db() as db:
        candidate = db.query(CandidateDB).options(joinedload(CandidateDB.skills)).filter(
                        CandidateDB.id == id).first()
        return candidate

def create_candidate_db(candidate: CandidateCreateRequest, local_logging_context: LoggingContext) -> Candidate:
    """
    Create a new candidate in the database with the associated skills.
    Args:
        candidate (CandidateCreateRequest): The candidate details, including name and skills.
    Returns:
        Candidate: The formated candidate response object with their skills.
    Raises:
        HTTPException: If a candidate with the same name already exists.
    """
    #check if candidate with same name exist
    _check_candidate = get_candidate_by_name(candidate.name)
    if _check_candidate:
        LOGGER.warn(f"Invalid Request, candidate already exists with id as {_check_candidate.id}", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, candidate already exists",
        )

    with get_db() as db:
        new_candidate = CandidateDB(name=candidate.name)
        db.add(new_candidate)
        db.commit()
        db.refresh(new_candidate)
        local_logging_context.upsert(candidate_id=new_candidate.id)
        LOGGER.debug("New Candidate created", extra=local_logging_context.store)

        for skill in candidate.skills:
            new_skill = CandidateSkillDB(
                name=skill.name,
                expertise_level=skill.expertise_level,
                candidate_id=new_candidate.id,
            )
            db.add(new_skill)

        db.commit()
        db.refresh(new_candidate)

        return Candidate(
            id=new_candidate.id,
            name=new_candidate.name,
            skills=[
                Skill(name=skill.name, expertise_level=skill.expertise_level)
                for skill in new_candidate.skills
            ],
        )

def delete_candidate_db(candidate_id: int) -> None:
    """
    Delete a candidate from the database by their ID, including their associated skills.
    Args:
        candidate_id (int): The ID of the candidate to be deleted.
    Raises:
        HTTPException: If the candidate with the provided ID does not exist.
    """
    _candidate = get_candidate_by_id(candidate_id)
    if not _candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, Candidate with provided id does not exists",
        )
    
    with get_db() as db:
        db.query(CandidateSkillDB).filter(
            CandidateSkillDB.candidate_id == _candidate.id).delete()
        db.delete(_candidate)
        db.commit()

def update_candidate_db(candidate: Candidate) -> CandidateDB:
    """
    Update the details of an existing candidate, including their skills.
    Args:
        candidate (Candidate): The candidate data to update, including name and skills.
    Returns:
        Candidate: The updated candidate with their skills.
    Raises:
        HTTPException: If the candidate does not exist or is missing an ID.
    """
    if not candidate.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Request, candidate id is compulsory",
        )
    
    with get_db() as db:
        _candidate = db.query(CandidateDB).filter(CandidateDB.id == candidate.id).first()
        if not _candidate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Request, candidate with provided id does not exists",
            )
        
        # Update basic candidate details
        _candidate.name = candidate.name
        
        existing_skills = {skill.name for skill in _candidate.skills}
        input_skills = {skill.name for skill in candidate.skills}

        # Remove skills not in the input
        for skill in _candidate.skills:
            if skill.name not in input_skills:
                db.delete(skill)

        # Add or update skills
        for skill in candidate.skills:
            if skill.name in existing_skills:
                # Update existing skill
                existing_skill = next((s for s in _candidate.skills if s.name == skill.name), None)
                if existing_skill:
                    existing_skill.name = skill.name
                    existing_skill.expertise_level = skill.expertise_level
            else:
                # Add new skill
                new_skill = CandidateSkillDB(
                    name=skill.name,
                    expertise_level=skill.expertise_level,
                    candidate_id=_candidate.id,
                )
                db.add(new_skill)

        #update command
        db.commit()
        db.refresh(_candidate)
        return Candidate(
            id=_candidate.id,
            name=_candidate.name,
            skills=[
                Skill(name=skill.name, expertise_level=skill.expertise_level)
                for skill in _candidate.skills
            ],
        )

def get_project_list(skip: int, size: int,
                        title: str, skill_required: str,
                        sort_by: str, order: str) -> ProjectListResponse:
    """
    Retrieve a list of projects from the database with optional filters and pagination.
    Args:
        skip (int): The number of records to skip for pagination.
        size (int): The number of records to retrieve per page.
        title (str): The title of the project to filter by (optional).
        skill_name (str): The skill name associated with the project to filter by (optional).
        sort_by (str): The field to sort the results by (e.g., 'id', 'title').
        order (str): The sort order, either 'asc' (ascending) or 'desc' (descending).
    Returns:
        ProjectListResponse: A response containing the list of projects and the total size.
    Raises:
        HTTPException: If any errors occur during the database query.
    """
    with get_db() as db:
        # Build the query for filtering
        query = db.query(ProjectDB).options(joinedload(ProjectDB.skills))

        # Apply title filter if provided
        if title:
            query = query.filter(ProjectDB.title.ilike(f"%{title}%"))

        # Apply skill_name filter if provided
        if skill_required:
            query = query.join(ProjectSkillDB).filter(ProjectSkillDB.name == skill_required)

        if order == "asc":
            query = query.order_by(asc(getattr(ProjectDB, sort_by)))
        else:
            query = query.order_by(desc(getattr(ProjectDB, sort_by)))

        # Apply pagination (skip and limit)
        query = query.offset(skip).limit(size)

        # Execute the query and return the result
        projects = query.all()

        project_responses = []
        for project in projects:
            skill_response = []
            for skill in project.skills:
                skill_tmp = Skill(name=skill.name, expertise_level=skill.expertise_level)
                skill_response.append(skill_tmp)

            tmp_response = Project(id=project.id, title=project.title, skills=skill_response)
            project_responses.append(tmp_response)
        
        return ProjectListResponse(size=len(project_responses), projects=project_responses)

def get_candidate_list(skip: int, size: int,
                        name: str, skill_required: str,
                        sort_by: str, order: str) -> List[CandidateDB]:
    """
    Retrieve a list of candidates from the database with optional filters and pagination.
    Args:
        skip (int): The number of records to skip for pagination.
        size (int): The number of records to retrieve per page.
        name (str): The name of the candidate to filter by (optional).
        skill_name (str): The skill name associated with the candidate to filter by (optional).
        sort_by (str): The field to sort the results by (e.g., 'id', 'name').
        order (str): The sort order, either 'asc' (ascending) or 'desc' (descending).
    Returns:
        List[CandidateDB]: A list of candidates matching the filters and pagination criteria.
    Raises:
        HTTPException: If any errors occur during the database query.
    """
    with get_db() as db:
        # Build the query for filtering
        query = db.query(CandidateDB).options(joinedload(CandidateDB.skills))

        # Apply title filter if provided
        if name:
            query = query.filter(CandidateDB.name.ilike(f"%{name}%"))

        # Apply skill_name filter if provided
        if skill_required:
            query = query.join(CandidateSkillDB).filter(CandidateSkillDB.name == skill_required)

        if order == "asc":
            query = query.order_by(asc(getattr(CandidateDB, sort_by)))
        else:
            query = query.order_by(desc(getattr(CandidateDB, sort_by)))

        # Apply pagination (skip and limit)
        query = query.offset(skip).limit(size)

        # Execute the query and return the result
        candidates = query.all()
        return candidates
