import pytest
from httpx import AsyncClient, ASGITransport

from takehome.repository.database import Base, engine
from takehome.app import app
from tests.test_helper import project_object1, project_object2, candidate_object1, candidate_special_score_object1
from tests.test_helper import candidate_object2, candidate_special_score_object2


# ficture to clear db
#instead of clearing main db we should create a test db and overwrite get_db function
@pytest.fixture(scope="session")
def clear_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(bind=engine)

@pytest.fixture
async def login_token(clear_db):
    payload = {"username": "pradeep", "password": "tmp@123"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/token", data=payload)
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_index():
    """Tests that the index is an HTML response."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"

@pytest.mark.asyncio
async def test_create_project(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json=project_object1, headers=headers)
    assert response.status_code == 200
    assert response.json()['title'] == project_object1['title']
    assert response.json()['skills'] == project_object1['skills']

@pytest.mark.asyncio
async def test_create_project_login_failed():
    headers = {"Authorization": "Bearer something"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json=project_object1, headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_project_duplicate(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json=project_object1, headers=headers)
    assert response.status_code == 400
    assert response.json() == {'detail': 'Invalid Request, Project already exists'}

@pytest.mark.asyncio
async def test_get_project(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/project/", params = params, headers=headers)
    assert response.status_code == 200
    assert response.json()['id'] == 1
    assert response.json()['title'] == project_object1['title']
    assert response.json()['skills'] == project_object1['skills']

@pytest.mark.asyncio
async def test_get_project_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 9999}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/project/", params = params, headers=headers)
    assert response.status_code == 400
    assert response.json() == {'detail': 'Invalid Request, Project with provided id does not exists'}

@pytest.mark.asyncio
async def test_update_project(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/project/", json=project_object2, headers=headers)
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/project/", params = params, headers=headers)
    assert response.status_code == 200
    assert response.json()['title'] == project_object2['title']
    assert response.json()['skills'] == project_object2['skills']

@pytest.mark.asyncio
async def test_update_project_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    project_object2['id']=9999
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/project/", json=project_object2, headers=headers)
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Request, candidate with provided id does not exists"}

@pytest.mark.asyncio
async def test_delete_project(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/project/", params = params, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "success"}

@pytest.mark.asyncio
async def test_delete_project_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/project/", params = params, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Request, Project with provided id does not exists"}

@pytest.mark.asyncio
async def test_create_candidate(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/candidate/", json=candidate_object1, headers=headers)
    assert response.status_code == 200
    assert response.json()['name'] == candidate_object1['name']
    assert response.json()['skills'] == candidate_object1['skills']

@pytest.mark.asyncio
async def test_create_candidate_duplicate(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/candidate/", json=candidate_object1, headers=headers)
    assert response.status_code == 400
    assert response.json() == {'detail': 'Invalid Request, candidate already exists'}

@pytest.mark.asyncio
async def test_get_candidate_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 9999}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/candidate/", params = params, headers=headers)
    assert response.status_code == 400
    assert response.json() == {'detail': 'Invalid Request, Candidate with provided id does not exists'}

@pytest.mark.asyncio
async def test_update_candidate(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/candidate/", json=candidate_object2, headers=headers)
    assert response.status_code == 200
    assert response.json()['name'] == candidate_object2['name']
    assert response.json()['skills'] == candidate_object2['skills']

@pytest.mark.asyncio
async def test_update_candidate_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    candidate_object2['id']=9999
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.put("/candidate/", json=candidate_object2, headers=headers)
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Request, candidate with provided id does not exists"}

@pytest.mark.asyncio
async def test_candidate_project(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/candidate/", params = params, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"message": "success"}

@pytest.mark.asyncio
async def test_delete_candidate_invalid(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    params = {"id": 1}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/candidate/", params = params, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Request, Candidate with provided id does not exists"}

@pytest.mark.asyncio
async def test_get_projects(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json = project_object1, headers=headers)
    
    project_object2['id']=2
    project_object2['title']='New title'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json = project_object2, headers=headers)
    
    params = {
        'page_no': 1,
        'size': 2
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/projects/", params = params, headers=headers)

    assert response.status_code == 200
    assert response.json()['size'] == 2
    assert response.json()['projects'][0]['id'] == 1


@pytest.mark.asyncio
async def test_get_projects_order_desc(login_token):
    headers = {"Authorization": f"Bearer {await login_token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json = project_object1, headers=headers)
    
    project_object2['id']=2
    project_object2['title']='New title'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/project/", json = project_object2, headers=headers)
    
    params = {
        'page_no': 1,
        'size': 2,
        'order': 'desc'
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/projects/", params = params, headers=headers)

    assert response.status_code == 200
    assert response.json()['size'] == 2
    assert response.json()['projects'][0]['id'] == 2


"""


Similarly we can add test case for get_project for other query params and failed cases, 


Plus same set of test cases for get_candidates
for get_candidates we need to mock fetch_special_score function


"""