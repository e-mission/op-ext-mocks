from __future__ import annotations

from copy import deepcopy
import html
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title='Bikeep Mock API')
TRANSITION_DELAY_SECS = 0.25


class CommandBody(BaseModel):
    command: str


class CommandOutcomeBody(BaseModel):
    device_id: str
    command: str
    outcome: str


_DEFAULT_LOCATIONS: List[Dict[str, Any]] = [
    {
        'id': 'test-station-1',
        'name': 'Mock Station 1',
        'latitude': 37.7749,
        'longitude': -122.4194,
        'devices': {'total': 2},
    },
    {
        'id': 'test-station-2',
        'name': 'Mock Station 2',
        'latitude': 37.7900,
        'longitude': -122.4100,
        'devices': {'total': 1},
    },
]

_DEFAULT_DEVICES: Dict[str, List[Dict[str, Any]]] = {
    'test-station-1': [
        {
            'id': 'mock-dock-1',
            'type': 'BIKE_DOCK',
            'alias': '1',
            'code': 'mock-code-1',
            'location': {'id': 'test-station-1'},
            'state': {'value': 'LOCKED', 'changed_at': '2026-10-12T00:00:00Z'},
        },
        {
            'id': 'mock-dock-2',
            'type': 'BIKE_DOCK',
            'alias': '2',
            'code': 'mock-code-2',
            'location': {'id': 'test-station-1'},
            'state': {'value': 'UNLOCKED', 'changed_at': '2026-10-12T00:00:00Z'},
        },
    ],
    'test-station-2': [
        {
            'id': 'mock-locker-1',
            'type': 'LOCKER',
            'alias': '1',
            'code': 'mock-code-3',
            'location': {'id': 'test-station-2'},
            'state': {'value': 'LOCKED', 'changed_at': '2026-10-12T00:00:00Z'},
        },
    ],
}

_locations_by_id = {location['id']: deepcopy(location) for location in _DEFAULT_LOCATIONS}
_devices_by_location_id = {location_id: deepcopy(devices) for location_id, devices in _DEFAULT_DEVICES.items()}
_command_outcomes: Dict[str, Dict[str, str]] = {}


def _now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _settle_device_state(device: Dict[str, Any]) -> None:
    transition = device.get('_pending_transition')
    if transition is None:
        return

    if time.time() < transition['ready_at']:
        return

    device['state'] = {
        'value': transition['target_state'],
        'changed_at': _now_iso(),
    }
    device.pop('_pending_transition', None)


def _device_view(device: Dict[str, Any]) -> Dict[str, Any]:
    _settle_device_state(device)
    device_doc = deepcopy(device)
    device_doc.pop('_pending_transition', None)
    return device_doc


def _all_devices() -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    for location_devices in _devices_by_location_id.values():
        devices.extend(location_devices)
    return devices


def _find_device(device_id: str) -> Optional[Dict[str, Any]]:
    for device in _all_devices():
        if device.get('id') == device_id:
            return device
    return None


def _find_location_for_device(device_id: str) -> Optional[Dict[str, Any]]:
    device = _find_device(device_id)
    if device is None:
        return None
    location_id = (device.get('location') or {}).get('id')
    if location_id is None:
        return None
    return _locations_by_id.get(location_id)


def _get_command_outcome(device_id: str, command: str) -> str:
        return _command_outcomes.get(device_id, {}).get(command, 'success')


def _set_command_outcome(device_id: str, command: str, outcome: str) -> None:
        if outcome not in {'success', 'failure'}:
                raise ValueError(f'Unsupported outcome {outcome}')
        _command_outcomes.setdefault(device_id, {})[command] = outcome


def _clear_command_outcomes() -> None:
        _command_outcomes.clear()


def _mock_error_response(device_id: str, command: str) -> JSONResponse:
        return JSONResponse(
                status_code=409,
                content={
                        'error_code': f'MOCK_{command.upper()}_FAILED',
                        'error_message': f'Mock {command} failure for device {device_id}',
                        'mock': True,
                },
        )


def _render_mock_ui() -> str:
        rows = []
        for device in _all_devices():
                device_view = _device_view(device)
                device_id = html.escape(str(device_view.get('id')))
                location_id = html.escape(str((device_view.get('location') or {}).get('id')))
                state_value = html.escape(str((device_view.get('state') or {}).get('value')))
                lock_outcome = _get_command_outcome(device_view['id'], 'lock')
                unlock_outcome = _get_command_outcome(device_view['id'], 'unlock')
                rows.append(
                        f"""
                        <tr>
                            <td>{device_id}</td>
                            <td>{location_id}</td>
                            <td>{state_value}</td>
                            <td>
                                <select data-device-id=\"{device_id}\" data-command=\"lock\">
                                    <option value=\"success\" {'selected' if lock_outcome == 'success' else ''}>success</option>
                                    <option value=\"failure\" {'selected' if lock_outcome == 'failure' else ''}>failure</option>
                                </select>
                            </td>
                            <td>
                                <select data-device-id=\"{device_id}\" data-command=\"unlock\">
                                    <option value=\"success\" {'selected' if unlock_outcome == 'success' else ''}>success</option>
                                    <option value=\"failure\" {'selected' if unlock_outcome == 'failure' else ''}>failure</option>
                                </select>
                            </td>
                        </tr>
                        """
                )

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset=\"utf-8\" />
                <title>Bikeep Mock Controls</title>
                <style>
                    body {{ font-family: sans-serif; margin: 24px; }}
                    table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
                    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
                    th {{ background: #f5f5f5; }}
                    .actions {{ margin: 16px 0; display: flex; gap: 12px; }}
                    .status {{ margin-top: 12px; color: #333; }}
                </style>
            </head>
            <body>
                <h1>Bikeep Mock Controls</h1>
                <p>Configure whether lock and unlock commands succeed or fail for each mock device.</p>
                <div class=\"actions\">
                    <button id=\"save-all\" type=\"button\">Save all</button>
                    <button id=\"reset-all\" type=\"button\">Reset outcomes</button>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Device</th>
                            <th>Location</th>
                            <th>Current state</th>
                            <th>Lock outcome</th>
                            <th>Unlock outcome</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
                <div class=\"status\" id=\"status\"></div>
                <script>
                    async function setOutcome(deviceId, command, outcome) {{
                        const response = await fetch('/mock/command-outcome', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ device_id: deviceId, command, outcome }})
                        }});
                        if (!response.ok) {{
                            const errorBody = await response.text();
                            throw new Error(errorBody || 'Failed to update outcome');
                        }}
                    }}

                    document.getElementById('save-all').addEventListener('click', async () => {{
                        const status = document.getElementById('status');
                        const selects = Array.from(document.querySelectorAll('select'));
                        try {{
                            for (const select of selects) {{
                                await setOutcome(select.dataset.deviceId, select.dataset.command, select.value);
                            }}
                            status.textContent = 'Saved';
                        }} catch (err) {{
                            status.textContent = `Save failed: ${{err.message}}`;
                        }}
                    }});

                    document.getElementById('reset-all').addEventListener('click', async () => {{
                        const status = document.getElementById('status');
                        const response = await fetch('/mock/command-outcome/reset', {{ method: 'POST' }});
                        if (!response.ok) {{
                            status.textContent = 'Reset failed';
                            return;
                        }}
                        for (const select of document.querySelectorAll('select')) {{
                            select.value = 'success';
                        }}
                        status.textContent = 'Reset';
                    }});
                </script>
            </body>
        </html>
        """


def reset_mock_state() -> None:
    """Restore the default mock station and device state."""
    _locations_by_id.clear()
    _locations_by_id.update({location['id']: deepcopy(location) for location in _DEFAULT_LOCATIONS})

    _devices_by_location_id.clear()
    _devices_by_location_id.update({location_id: deepcopy(devices) for location_id, devices in _DEFAULT_DEVICES.items()})
    _clear_command_outcomes()


def set_mock_locations(locations: List[Dict[str, Any]]) -> None:
    """Replace the mock locations with custom test data."""
    _locations_by_id.clear()
    for location in locations:
        if 'id' not in location:
            raise ValueError('Each location must include an id')
        _locations_by_id[location['id']] = deepcopy(location)


def set_mock_devices(location_id: str, devices: List[Dict[str, Any]]) -> None:
    """Replace the mock devices for a specific location."""
    _devices_by_location_id[location_id] = deepcopy(devices)


@app.post('/oauth2/token')
def oauth_token() -> Dict[str, Any]:
    return {
        'access_token': 'mock-access-token',
        'expires_in': 3600,
        'token_type': 'Bearer',
    }


@app.get('/location/v1/locations')
def list_locations() -> Dict[str, Any]:
    locations = []
    for location in _locations_by_id.values():
        location_doc = deepcopy(location)
        location_devices = _devices_by_location_id.get(location_doc['id'], [])
        location_doc.setdefault('devices', {})
        location_doc['devices']['total'] = len(location_devices)
        location_doc['devices']['available'] = sum(
            1 for device in location_devices if (device.get('state') or {}).get('value') == 'UNLOCKED'
        )
        locations.append(location_doc)
    return {'data': locations}


@app.get('/location/v1/locations/{location_id}')
def get_location(location_id: str) -> Dict[str, Any]:
    location = _locations_by_id.get(location_id)
    if location is None:
        raise HTTPException(status_code=404, detail={'error_code': 'LOCATION_NOT_FOUND', 'error_message': location_id})
    return deepcopy(location)


@app.get('/device/v1/locations/{location_id}/devices')
def list_devices(location_id: str) -> Dict[str, Any]:
    if location_id not in _locations_by_id:
        raise HTTPException(status_code=404, detail={'error_code': 'LOCATION_NOT_FOUND', 'error_message': location_id})
    return {'data': [_device_view(device) for device in _devices_by_location_id.get(location_id, [])]}


@app.get('/device/v1/devices/{device_id}')
def get_device(device_id: str) -> Dict[str, Any]:
    device = _find_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail={'error_code': 'DEVICE_NOT_FOUND', 'error_message': device_id})

    location = _find_location_for_device(device_id)
    location_uri = None if location is None else f"/location/v1/locations/{location['id']}"
    response = _device_view(device)
    response['location'] = {'uri': location_uri} if location_uri else {}
    return response


@app.post('/device/v1/devices/{device_id}/commands')
def device_command(device_id: str, body: CommandBody) -> Dict[str, Any]:
    device = _find_device(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail={'error_code': 'DEVICE_NOT_FOUND', 'error_message': device_id})

    command = body.command
    if command == 'lock':
        if _get_command_outcome(device_id, command) == 'failure':
            return _mock_error_response(device_id, command)
        _settle_device_state(device)
        current_state = (device.get('state') or {}).get('value')
        if current_state == 'LOCKED':
            return {'status': 'locked', 'dock_id': device_id, 'mock': True}

        device['state'] = {'value': 'LOCKING', 'changed_at': _now_iso()}
        device['_pending_transition'] = {
            'target_state': 'LOCKED',
            'ready_at': time.time() + TRANSITION_DELAY_SECS,
        }
        return {'status': 'locking', 'dock_id': device_id, 'mock': True}
    if command == 'unlock':
        if _get_command_outcome(device_id, command) == 'failure':
            return _mock_error_response(device_id, command)
        device['state'] = {'value': 'UNLOCKED', 'changed_at': _now_iso()}
        device.pop('_pending_transition', None)
        return {'status': 'unlocked', 'dock_id': device_id, 'mock': True}
    if command == 'take-photo':
        return {'status': 'photo_taken', 'device_id': device_id, 'mock': True}

    raise HTTPException(
        status_code=400,
        detail={'error_code': 'UNSUPPORTED_COMMAND', 'error_message': command},
    )


@app.get('/mock/state')
def get_mock_state() -> Dict[str, Any]:
    """Return the current mock state for debugging or tests."""
    return {
        'locations': deepcopy(list(_locations_by_id.values())),
        'devices': deepcopy(_devices_by_location_id),
        'command_outcomes': deepcopy(_command_outcomes),
    }


@app.get('/mock/ui', response_class=HTMLResponse)
def mock_ui() -> str:
    return _render_mock_ui()


@app.post('/mock/command-outcome')
def set_command_outcome(body: CommandOutcomeBody) -> Dict[str, Any]:
    device = _find_device(body.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail={'error_code': 'DEVICE_NOT_FOUND', 'error_message': body.device_id})
    if body.command not in {'lock', 'unlock'}:
        raise HTTPException(status_code=400, detail={'error_code': 'UNSUPPORTED_COMMAND', 'error_message': body.command})
    if body.outcome not in {'success', 'failure'}:
        raise HTTPException(status_code=400, detail={'error_code': 'UNSUPPORTED_OUTCOME', 'error_message': body.outcome})

    _set_command_outcome(body.device_id, body.command, body.outcome)
    return {
        'status': 'ok',
        'device_id': body.device_id,
        'command': body.command,
        'outcome': body.outcome,
    }


@app.post('/mock/command-outcome/reset')
def reset_command_outcomes() -> Dict[str, Any]:
    _clear_command_outcomes()
    return {'status': 'reset'}


@app.post('/mock/reset')
def reset_state() -> Dict[str, Any]:
    reset_mock_state()
    return {'status': 'reset'}
