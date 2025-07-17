from typing import Optional, Union, Tuple
import requests
from flask import session

def api_call(
    method: str,
    postfix: str,
    payload: Optional[dict] = None,
    additional_headers: Optional[dict] = None,
    timeout: int = 5
) -> Union[dict, Tuple[dict, int]]:

    url = f'https://icls.sosit-wh.net/v2/{postfix}'
    headers = {
        'Authorization': f'Bearer {session.get("token")}',
        'Content-Type': 'application/json'
    }

    if additional_headers:
        headers.update(additional_headers)

    print(payload)
    print(headers)

    try:
        method = method.upper()
        request_func = {
            'GET': lambda: requests.get(url, params=payload, headers=headers, timeout=timeout),
            'POST': lambda: requests.post(url, json=payload, headers=headers, timeout=timeout),
            'PUT': lambda: requests.put(url, json=payload, headers=headers, timeout=timeout),
            'PATCH': lambda: requests.patch(url, json=payload, headers=headers, timeout=timeout),
            'DELETE': lambda: requests.delete(url, json=payload, headers=headers, timeout=timeout),
        }.get(method)

        if not request_func:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response = request_func()

        try:
            return response.json()
        except ValueError:
            return {'error': 'Invalid JSON response', 'status_code': response.status_code, 'raw': response.text}, 500

    except requests.RequestException as e:
        return {'error': 'Failed to reach server', 'msg': str(e)}, 500
