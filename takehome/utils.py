from typing import List
from itertools import combinations
from fastapi import HTTPException, status
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

from takehome.repository.database_models import CandidateDB, ProjectDB
from takehome.models import FormTeamCandidateResponse, FormTeamResponse, FormTeamScore
from takehome.config import settings
from takehome.cache import redis_client
from takehome.constants import SPECIAL_SCORE_REDIS_KEY
from takehome.logs import LoggingContext, LOGGER

def calculate_team_coverage(team: List[CandidateDB], required_skills: dict):
    skills_covered = {}
    total_expertise = 0

    skill_match = {candidate.id: [] for candidate in team}

    for candidate in team:
        candidate_skills = {skill['name']: skill['expertise_level'] for skill in candidate.skills}
        for skill in candidate_skills.keys():
            expertise = candidate_skills[skill]
            if skill in required_skills.keys() and expertise >= required_skills[skill]:
                if skill not in skills_covered or expertise > skills_covered[skill]:
                    skills_covered[skill] = expertise
                    skill_match[candidate.id].append(skill)
    
    total_expertise = sum(skills_covered.values())
    coverage = len(skills_covered.keys()) / len(required_skills.keys())
    return coverage, total_expertise, skill_match 

def form_team_helper(team_size: int, candidates: List[CandidateDB], project: ProjectDB, local_logging_context: LoggingContext) -> FormTeamResponse:

    best_team = None
    best_coverage = 0
    best_expertise = 0
    best_skill_match = {}

    required_skills = { skill['name']: skill['expertise_level']  for skill in project.skills}

    for team in combinations(candidates, team_size):
        coverage, expertise, skill_match = calculate_team_coverage(team, required_skills)

        if (coverage > best_coverage) or (coverage == best_coverage and expertise > best_expertise):
            best_team = team
            best_coverage = coverage
            best_expertise = expertise
            best_skill_match = skill_match
    
    if not best_team:
        LOGGER.warn("Could not form the best team", extra=local_logging_context.store)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not form the best team",
        )
    
    candidate_response = []
    special_score_payload = []
    for candidate in best_team:
        assigned_skills = best_skill_match.get(candidate.id, [])
        tmp_response = FormTeamCandidateResponse(candidate_id=candidate.id, name=candidate.name,
                            assigned_skills=assigned_skills, special_score=[])
        candidate_response.append(tmp_response)

        cur_special_score = {'candidate_id': str(candidate.id)}
        cur_special_score['skills']=[]
        for skill in candidate.skills:
            if skill['name'] in assigned_skills:
                cur_special_score['skills'].append({'skill': skill['name'], 'score': skill['expertise_level']})
        special_score_payload.append(cur_special_score)
    LOGGER.info("Created a optimal team", extra=local_logging_context.store)
    
    LOGGER.info(f"Fetching special scores for payload {special_score_payload}", extra=local_logging_context.store)
    special_scores = fetch_parallel_scores(special_score_payload)
    for candidate in candidate_response:
        special_score = special_scores[str(candidate.candidate_id)]
        for skill in special_score.keys():
            candidate.special_score.append(FormTeamScore(skill=skill, score=special_score[skill]))

    response = FormTeamResponse(team=candidate_response, coverage=best_coverage, total_expertise=best_expertise)
    return response

def fetch_parallel_scores(payloads: List[dict]) -> List[dict]:
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_special_score, payloads))
    
    candidate_ids = [payload['candidate_id'] for payload in payloads]
    return dict(zip(candidate_ids, results))

def fetch_special_score( payload: dict) -> float:
    LOGGER.debug(f"fetching special score for payload {payload}")
    
    candidate_id = int(payload['candidate_id'])
    cached_output = redis_client.get(SPECIAL_SCORE_REDIS_KEY.format(candidate_id))
    if cached_output:
        return json.loads(cached_output)
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(url=settings.MOCK_FLAKY_ENDPOINT, data=json.dumps(payload)).json()
            success_flag = response.get("success", False)

            if not success_flag:
                raise Exception

            special_scores = response.get("special_scores", [])
            if len(special_scores) != len(payload.get("skills", [])):
                raise Exception

            skills_score_map = {}
            for index, skill in enumerate(payload.get("skills", [])):
                skills_score_map[skill['skill']] = special_scores[index]
            
            redis_client.set(SPECIAL_SCORE_REDIS_KEY.format(candidate_id), json.dumps(skills_score_map), ex=86400)   # ex=86400 -> 1 day expiry
            return skills_score_map

        except Exception as e:
            LOGGER.warn(f"Attempt {attempt + 1}: Failed as {e} to fetch score for candidate {candidate_id}. Retrying...")
            time.sleep(retry_delay)

    LOGGER.error(f"Failed to fetch score for candidate {candidate_id} after {max_retries} retries.")
    raise Exception(f"Failed to fetch score for candidate {candidate_id} after {max_retries} retries.")