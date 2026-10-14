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

## Run In A Dev Container

This repo includes a devcontainer configuration for both GitHub Codespaces and VS Code. When the container starts, it automatically installs the Python dependencies and launches the mock API in the background.

### GitHub Codespaces

> To launch a devcontainer in GitHub Codespaces, open your repository in GitHub, click the green "Code" button, select "Codespaces," then "Create codespace."

After the codespace is created, wait for the container to finish setting up, then open the `Ports` panel and confirm port `24533` is forwarded.

### VS Code

> To launch a devcontainer in VS Code, open the repository folder in VS Code, then use the command palette and run "Dev Containers: Reopen in Container" or "Dev Containers: Rebuild and Reopen in Container."

If the repo was opened before the devcontainer config was added or changed, rebuild the container once so the post-create and post-start hooks run.

Once the container is running:

1. Open the `Ports` panel in VS Code or Codespaces.
2. Confirm port `24533` is forwarded.
3. Visit `/mock/ui` to configure lock/unlock success or failure.

In the Codespaces `Ports` panel, set port `24533`'s **Port protocol** to `HTTP`. The public forwarded URL still uses HTTPS; the proxy terminates that TLS and forwards HTTP to Uvicorn. If the port protocol is set to `HTTPS`, the proxy instead sends TLS to Uvicorn, which would require configuring Uvicorn with a certificate and key.

Example:

```text
http://localhost:24533/mock/ui
```

Or, in GitHub Codespaces:

```text
https://<your-codespace-name>-24533.app.github.dev/mock/ui
```

## Point The Bikeep Client At The Mock

This repo matches the server-side change in e-mission/e-mission-server#1112: the Bikeep URLs can be configured via environment variables instead of hardcoded module constants.

The devcontainer starts the mock automatically on container startup, and uvicorn runs with autoreload so file changes restart the server inside the container.

If you are running the mock from the devcontainer, use the forwarded container URL or localhost depending on where the client runs:

```bash
export BIKEEP_API_URL="http://127.0.0.1:24533"
export BIKEEP_AUTH_URL="http://127.0.0.1:24533/oauth2/token"
```

If the caller runs in the same container, `127.0.0.1:24533` is enough.

If the caller runs outside the container, use the forwarded URL shown in the Ports panel. That public URL is HTTPS, and the certificate is handled by Codespaces or the VS Code forwarding layer.

If the server is already running and you change the devcontainer config, rebuild the container once so the startup hook is picked up again.

For example, in a Codespace you might use:

```bash
export BIKEEP_API_URL="https://<your-codespace-name>-24533.app.github.dev"
export BIKEEP_AUTH_URL="https://<your-codespace-name>-24533.app.github.dev/oauth2/token"
```

This keeps the client configuration aligned with the server PR that allows the Bikeep endpoints to be passed in externally.

## Useful Endpoints

Inspect current mock state:

```bash
curl http://127.0.0.1:24533/mock/state
```

Reset devices and configured outcomes:

```bash
curl -X POST http://127.0.0.1:24533/mock/reset
```

Force a lock failure for one device:

```bash
curl -X POST http://127.0.0.1:24533/mock/command-outcome \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"mock-dock-1","command":"lock","outcome":"failure"}'
```

Clear all forced outcomes:

```bash
curl -X POST http://127.0.0.1:24533/mock/command-outcome/reset
```

## Notes

- The mock models a transient `UNLOCKED -> LOCKING -> LOCKED` transition for lock commands.
- `unlock` immediately sets the device state back to `UNLOCKED`.
- Command failures return JSON error payloads so the existing Bikeep client logging path can exercise failure handling.
