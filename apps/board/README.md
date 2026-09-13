# Speccify Web-Board

One small service that shows the progress of any number of Speccify projects
in the browser and lets a team move stations and tick tasks — straight into
each repository's spec register (branch `specs`, Spec 028). Spec 032.

```bash
uv run speccify-board --config apps/board/board.example.yaml --data /tmp/board-data
# or, from the repository root:
docker build -f apps/board/Dockerfile -t speccify-board .
docker run --rm -p 8790:8790 -v $PWD/apps/board/board.example.yaml:/config/board.yaml:ro speccify-board
```

Open <http://localhost:8790/>. `GET /r/<name>/` shows one repository,
`GET /api/board.json` the data, `POST /api/refresh` refreshes now,
`GET /healthz` reports every repository's state. Set `BOARD_PASSWORD` for
HTTP Basic auth (user name is ignored). `/mcp` is an MCP server (Streamable
HTTP) guarded by `BOARD_MCP_TOKEN` — install it in itsdcloud as an MCP
integration (Spec 033).

Details and the configuration format: `docs/web-board.md`.
