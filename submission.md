# Backend Candidate Team Challenge

## Submission Overview

1. Database Models
   - Candidate
   - Project
   - CandidateSkills
   - ProjectSkills

2. Endpoints
   - CRUD operations for projects and candidates
   - Basic input validation and error handling with Pydantic
   - Unit tests for API endpoints
   - Get List objects with pagincation, sorting and filtering
   - Proper Error Handling
   - Custom Logger with Logger class passed to uvicorn
   - Ruff implementation for linting
   - Added auth for users
   - Added GitHub CI actions to automate testing/linting of code
   - Optimal Team Algorithm Endpoint
   - Implemention of flaky url in Fastapi application for special score
   - Used redis for caching of special scores
   - Used splite as Database
   - Usage of Pydantic for data validation and serialization


## Project Setup
1. `poetry install`: Install dependecies
2. `poetry run dev`: Run Main server
3. `poetry run mock`: Run Mock server
4. `poetry run pytest`: Run the tests.
5. Temp creds are username- preadeep, password - tmp@123


## Improvements Required
- Instead of reading ssm from env file read from ssm parameters.
- Skills of Projects and Candidate can be stored in single table with many-many relationship
- User tables, user crud operation


## Mistkae in Form Team Challenge
- Exmaple1- SQL should be assigned to candidate 3 and not 2
- Example2-  Answer should be candidate (3,4) and not (1,2)