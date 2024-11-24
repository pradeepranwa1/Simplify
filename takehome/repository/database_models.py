"""
Database tables
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from takehome.repository.database import Base

class ProjectDB(Base):
    """
    Represents a project in the database.

    Attributes:
        id (int): The unique identifier for the project.
        title (str): The title of the project.
        skills (list): A list of skills associated with the project,
                        represented by `ProjectSkillDB`.
    """
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    skills = relationship("ProjectSkillDB", back_populates="project")

class CandidateDB(Base):
    """
    Represents a candidate in the database.

    Attributes:
        id (int): The unique identifier for the candidate.
        name (str): The name of the candidate.
        skills (list): A list of skills possessed by the candidate,
                        represented by `CandidateSkillDB`.
    """
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    skills = relationship("CandidateSkillDB", back_populates="candidate")

class CandidateSkillDB(Base):
    """
    Represents a skill possessed by a candidate.

    Attributes:
        id (int): The unique identifier for the candidate's skill.
        name (str): The name of the skill (e.g., Python, Java).
        expertise_level (int): The level of expertise for the skill (1-10).
        candidate_id (int): The foreign key reference to the associated candidate.
        candidate (CandidateDB): The CandidateDB orm instance to which the skill belongs,
                                    this is not a database column.
    """
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    expertise_level = Column(Integer)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    candidate = relationship("CandidateDB", back_populates="skills")

class ProjectSkillDB(Base):
    """
    Represents a skill required for a project.

    Attributes:
        id (int): The unique identifier for the project's skill.
        name (str): The name of the skill.
        expertise_level (int): The level of expertise required for the skill (1-10).
        project_id (int): The foreign key reference to the associated project.
        project (ProjectDB): The ProjectDB instance orm to which the skill belongs,
                                this is not a database column.
    """
    __tablename__ = "project_skills"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    expertise_level = Column(Integer)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("ProjectDB", back_populates="skills")
