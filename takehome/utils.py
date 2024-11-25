from typing import List
from itertools import combinations
from fastapi import HTTPException, status
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

from takehome.repository.database_models import CandidateDB, ProjectDB
from takehome.models import FormTeamCandidateResponse, FormTeamResponse, FormTeamScore, CandidateDictSkills
from takehome.config import settings
from takehome.cache import redis_client
from takehome.constants import SPECIAL_SCORE_REDIS_KEY
from takehome.logs import LoggingContext, LOGGER

#calculate coverage, expertise and assigned skills for a given set of candidates with respect to required_skills
def calculate_team_coverage(team: List[CandidateDictSkills], required_skills: dict):
    skills_covered = {}
    total_expertise = 0

    skill_match = {candidate.id: [] for candidate in team}

    for candidate in team:
        candidate_skills = candidate.skills
        for skill_name in candidate_skills.keys():
            expertise = candidate_skills[skill_name]
            if skill_name in required_skills.keys() and expertise >= required_skills[skill_name]:
                if skill_name not in skills_covered or expertise > skills_covered[skill_name]:
                    skills_covered[skill_name] = expertise
                    skill_match[candidate.id].append(skill_name)
    
    total_expertise = sum(skills_covered.values())
    coverage = len(skills_covered.keys()) / len(required_skills.keys())
    return coverage, total_expertise, skill_match 

#remove candidates which contribute zero in project and remove skills which are not required in project
def filter_candidates_and_skills(required_skills, candidates: List[CandidateDB]) -> List[CandidateDictSkills]:

    filtered_candidates = []
    for candidate in candidates:
        is_any_useful_skill = False
        candidate_skills = {skill.name: skill.expertise_level for skill in candidate.skills}
        candidate_skill_keys = list(candidate_skills.keys())
        for skill_name in candidate_skill_keys:
            if skill_name not in required_skills.keys():
                candidate_skills.pop(skill_name)
            elif required_skills[skill_name] > candidate_skills[skill_name]:
                candidate_skills.pop(skill_name)
            else:
                is_any_useful_skill = True
        if is_any_useful_skill:
            tmp_candidate = CandidateDictSkills(id=candidate.id, name=candidate.name, skills=candidate_skills)
            filtered_candidates.append(tmp_candidate)
    return filtered_candidates

#remove candidates for which there exist a candidate who have better expertise for all skills
def filter_better_candidates(candidates: List[CandidateDictSkills]) -> List[CandidateDictSkills]:

    remove_candidates_indexes = []
    for i in range(len(candidates)):
        for j in range(len(candidates)):
            if i==j:
                continue

            is_j_better=True
            i_skills = candidates[i].skills
            j_skills = candidates[j].skills
            for skill_name in i_skills.keys():
                if (skill_name not in j_skills.keys() ) or (j_skills[skill_name] < i_skills[skill_name] ):
                    is_j_better = False 
                
            if is_j_better:
                remove_candidates_indexes.append(i)
    filtered_candidates = []
    for i in range(len(candidates)):
        if i not in remove_candidates_indexes:
            filtered_candidates.append(candidates[i])
    return filtered_candidates


def form_team_helper(team_size: int, candidates: List[CandidateDB], project: ProjectDB, local_logging_context: LoggingContext) -> FormTeamResponse:

    best_team = None  # List[CandidateDictSkills]
    best_coverage = 0
    best_expertise = 0
    best_skill_match = {}

    required_skills = { skill.name: skill.expertise_level  for skill in project.skills}

    #filtering candidates
    filtered_candidates: List[CandidateDictSkills] = filter_candidates_and_skills(required_skills, candidates)
    filtered_candidates: List[CandidateDictSkills] = filter_better_candidates(filtered_candidates)

    for team in combinations(filtered_candidates, team_size):
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
        for skill_name in candidate.skills:
            if skill_name in assigned_skills:
                cur_special_score['skills'].append({'skill': skill_name, 'score': candidate.skills[skill_name]})
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

#using ThreadPoolExecutor to call multiple calls at once
def fetch_parallel_scores(payloads: List[dict]) -> List[dict]:
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_special_score, payloads))
    
    candidate_ids = [payload['candidate_id'] for payload in payloads]
    return dict(zip(candidate_ids, results))

#calls mock server api to fetch special score and store in redis
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