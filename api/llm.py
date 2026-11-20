"""Bounded JSON completion with an owner-configured gateway fallback."""
import os
import re
import httpx


def complete_json(messages, *, key=None, max_tokens=4000, fallback=True):
    providers = []
    primary = key or os.environ.get('STUDIO_OPENROUTER_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
    if primary:
        providers.append(('https://openrouter.ai/api/v1', primary, os.environ.get('DEMO_MODEL', 'inclusionai/ling-3.2-flash:free')))
    if fallback and os.environ.get('VELONA_API_KEY'):
        providers.insert(0, (os.environ.get('VELONA_BASE_URL', 'https://velona.in/gateway/v1'), os.environ['VELONA_API_KEY'], os.environ.get('VELONA_MODEL', 'openai/gpt-4.1-mini')))
    for base, credential, model in providers:
        try:
            native = base.endswith('/gateway/v1')
            body = {'model': model, 'turns': messages, 'config': {'max_tokens': max_tokens}, 'output': {'format': 'json'}} if native else {
                'model': model, 'messages': messages, 'max_tokens': max_tokens, 'reasoning': {'enabled': False}, 'response_format': {'type': 'json_object'}}
            response = httpx.post(base + ('/inference/run' if native else '/chat/completions'), headers={'Authorization': 'Bearer ' + credential}, json=body, timeout=65)
            response.raise_for_status()
            data = response.json()
            if 'choices' not in data and isinstance(data.get('data'), dict):
                data = data['data']
            content = data.get('output') if native else data['choices'][0]['message']['content']
            if not isinstance(content, str) or not content.strip():
                continue
            content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip())
            return content, data.get('usage', {}), model
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            continue
    raise RuntimeError('The model providers are unavailable. Please retry shortly.')
