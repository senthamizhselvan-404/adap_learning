"""
Ollama Client — gemma3:4b
==========================
Wraps the Ollama HTTP API for:
  1. Skill extraction from raw curriculum text
  2. Pathway explanation generation
  3. Curriculum gap analysis narrative

All functions degrade gracefully when Ollama is not running.
"""
import json
import logging
import requests
from flask import current_app

logger = logging.getLogger('ealps.ollama')


def _chat(prompt: str, system: str = '', timeout: int = 120) -> str:
    base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    model    = current_app.config.get('OLLAMA_MODEL',    'gemma3:4b')

    payload = {
        'model':   model,
        'stream':  False,
        'messages': [],
    }
    if system:
        payload['messages'].append({'role': 'system', 'content': system})
    payload['messages'].append({'role': 'user', 'content': prompt})

    try:
        resp = requests.post(
            f'{base_url}/api/chat',
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()['message']['content'].strip()
    except requests.exceptions.ConnectionError:
        logger.warning('Ollama not reachable — start with: ollama serve')
        return '[Ollama not running — start with: ollama serve]'
    except requests.exceptions.Timeout:
        logger.warning('Ollama request timed out after %ds', timeout)
        return '[Ollama request timed out]'
    except Exception as e:
        logger.error('Ollama error: %s', e)
        return f'[Ollama error: {str(e)}]'


def extract_skills_from_text(raw_text: str) -> list:
    """
    Extract skills from curriculum text.
    Returns list of dicts: [{skill_name, category, bloom_level, estimated_hours}]
    """
    system = (
        'You are a curriculum analysis AI. Extract technical and professional skills '
        'from educational content. Respond ONLY with a valid JSON array, no markdown, '
        'no explanation.'
    )
    prompt = (
        'Extract all skills from the following curriculum text.\n'
        'For each skill return a JSON object with keys:\n'
        '  skill_name (string), category (string), bloom_level (int 1-6), '
        'estimated_hours (float)\n\n'
        'Respond with ONLY a JSON array like: '
        '[{"skill_name":"Python","category":"Programming","bloom_level":3,"estimated_hours":40}]\n\n'
        f'Curriculum text:\n{raw_text[:4000]}'
    )

    raw = _chat(prompt, system=system, timeout=90)

    try:
        clean = raw.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean)
        if isinstance(result, list):
            return result
        return []
    except Exception:
        return []


def generate_pathway_explanation(target_role: str, skills: list) -> str:
    """Generate a human-readable explanation for a learning pathway."""
    skill_list = ', '.join([s.get('skill_name', '') for s in skills[:10] if s.get('skill_name')])
    if not skill_list:
        return ''
    prompt = (
        f'You are a career advisor. A learner wants to become a {target_role}. '
        f'Their personalised learning pathway starts with: {skill_list}. '
        'Write 2-3 sentences explaining why this sequence makes sense and what outcomes to expect.'
    )
    return _chat(prompt, timeout=60)


def analyse_curriculum_gaps(decayed_skills: list, emerging_skills: list) -> str:
    """Generate an admin-facing curriculum gap analysis narrative."""
    decayed  = ', '.join(decayed_skills[:5])  if decayed_skills  else 'none'
    emerging = ', '.join(emerging_skills[:5]) if emerging_skills else 'none'
    prompt = (
        'You are an academic curriculum advisor. '
        f'Declining skills detected in curriculum: {decayed}. '
        f'Emerging market skills not yet in curriculum: {emerging}. '
        'Write 3 actionable recommendations for the curriculum committee in plain English.'
    )
    return _chat(prompt, timeout=60)


def check_ollama_health() -> bool:
    """Ping Ollama to confirm it is running."""
    try:
        base_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        r = requests.get(f'{base_url}/api/tags', timeout=5)
        return r.status_code == 200
    except Exception:
        return False
