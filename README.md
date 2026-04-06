# Agents

- This repo is inspired by OpenWebUI.
- You can follow the documentation for setting up the development environment. See at [OpenWebUI documentation](https://docs.openwebui.com/getting-started/quick-start/)

# Change port

Following are the default ports for the backend and frontend components, along with instructions on how to change them if needed:

| Component | Default port | Custom port |
|-----------|-------------|-------------|
| Backend   | 8080        | `sh backend/dev.sh --port <port>` |
| Frontend  | 5173        | `vite dev --port <port>` |

**Important:** When changing the backend port, always set `VITE_BACKEND_PORT` to the same value so the frontend can connect.
For example:

```bash
sh backend/dev.sh --port 8082
VITE_BACKEND_PORT=8082 bun dev
```

# Mandatory: create data directory

```bash
cd backend
mkdir data
```

# Dummy gmail account for testing

```bash
BACKEND_PORT=8082
python3 scripts/signup_dummy_accounts.py \
  --base-url "http://localhost:${BACKEND_PORT}" \
  --admin-email your-admin@example.com \
  --admin-password 'your-admin-password' \
  --permission-profile manager
```

```bash
BACKEND_PORT=8082
python3 scripts/signup_dummy_accounts.py \
  --base-url "http://localhost:${BACKEND_PORT}" \
  --admin-email your-admin@example.com \
  --admin-password 'your-admin-password' \
  --permission-profile employee
```

```bash
BACKEND_PORT=8082
python3 scripts/signup_dummy_accounts.py \
  --base-url "http://localhost:${BACKEND_PORT}" \
  --admin-email your-admin@example.com \
  --admin-password 'your-admin-password' \
  --permission-profile auto
```
