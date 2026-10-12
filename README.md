# Bikeep Mock

This standalone directory contains a small FastAPI app that mocks the Bikeep endpoints used by the main emission app.

## What It Provides

The mock serves these endpoint groups:

- `POST /oauth2/token`
- `GET /location/v1/locations`
- `GET /location/v1/locations/{location_id}`
- `GET /device/v1/locations/{location_id}/devices`
- `GET /device/v1/devices/{device_id}`
- `POST /device/v1/devices/{device_id}/commands`
- `GET /mock/ui`
- `GET /mock/state`
- `POST /mock/reset`
- `POST /mock/command-outcome`
- `POST /mock/command-outcome/reset`

The mock UI at `GET /mock/ui` lets you force `lock` and `unlock` to succeed or fail per device.

## Run In GitHub Codespaces

From this mock repo root, install the minimal dependencies if they are not already available:

```bash
pip install fastapi uvicorn
```

Start the mock server:

```bash
PYTHONPATH=. uvicorn bikeep_mock:app --host 0.0.0.0 --port 8000
```

In GitHub Codespaces:

1. Open the `Ports` panel.
2. Confirm port `8000` is forwarded.
3. Open the forwarded URL in the browser.
4. Visit `/mock/ui` to configure lock/unlock success or failure.

Example:

```text
https://<your-codespace-name>-8000.app.github.dev/mock/ui
```

## Point The Bikeep Client At The Mock

`bikeep_service.py` currently uses module constants for the Bikeep base URLs. For a quick local test in Codespaces, set them before calling the service from Python:

```python
import emission.net.ext_service.bikeep.bikeep_service as bikeep

bikeep.BIKEEP_API_URL = "http://127.0.0.1:8000"
bikeep.BIKEEP_AUTH_URL = "http://127.0.0.1:8000/oauth2/token"
```

If the caller runs in the same Codespaces container, `127.0.0.1:8000` is enough. If you need to hit the mock from outside the container, use the forwarded Codespaces URL instead.

## Useful Endpoints

Inspect current mock state:

```bash
curl http://127.0.0.1:8000/mock/state
```

Reset devices and configured outcomes:

```bash
curl -X POST http://127.0.0.1:8000/mock/reset
```

Force a lock failure for one device:

```bash
curl -X POST http://127.0.0.1:8000/mock/command-outcome \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mock-dock-1","command":"lock","outcome":"failure"}'
```

Clear all forced outcomes:

```bash
curl -X POST http://127.0.0.1:8000/mock/command-outcome/reset
```

## Notes

- The mock models a transient `UNLOCKED -> LOCKING -> LOCKED` transition for lock commands.
- `unlock` immediately sets the device state back to `UNLOCKED`.
- Command failures return JSON error payloads so the existing Bikeep client logging path can exercise failure handling.
