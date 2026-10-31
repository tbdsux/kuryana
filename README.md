<div align="center">
  <h1>Kuryana</h1>

  <p><strong>An unofficial JSON API for <a href="https://mydramalist.com">MyDramaList</a>.</strong></p>
  <p>Search Asian dramas, movies and people, and get details, cast, episodes, reviews and user lists as clean, typed JSON.</p>

  <p>
    <a href="#api-use">API</a> ·
    <a href="docs/v2.md">v2 docs</a> ·
    <a href="#deployment">Deploy</a> ·
    <a href="https://kuryana.tbdh.app/docs">Swagger</a>
  </p>

</div>

> [!NOTE]
> Pages are scraped live on every request and nothing is cached, so responses can take a moment.
> Kuryana exists only because MyDramaList has no public API, and it will be retired once an official one is released.

## Deployment

### Self Hosted - Docker

```sh
# run
docker compose up -d --build

# take down
docker compose down
```

#### VPS with nginx

To serve it on your own domain over HTTPS, put nginx in front of the app. A sample config is in [docs/nginx.conf](docs/nginx.conf). It redirects HTTP to HTTPS and proxies requests to the app.

1. Copy it to `/etc/nginx/sites-available/kuryana` and symlink it into `sites-enabled`.
2. Replace `your-domain.com` in both `server_name` lines with your domain and point `ssl_certificate` / `ssl_certificate_key` at your certificate files.
3. Set `proxy_pass` to wherever the app listens: `http://127.0.0.1:8035` with the `docker-compose.yml` above (it publishes port `8035`), or `http://127.0.0.1:8000` when running `fastapi run` directly.
4. Check the config and reload nginx:

```sh
sudo nginx -t && sudo systemctl reload nginx
```

#### [Dokploy](Dokploy)

[dokploy.docker-compose.yml](./dokploy.docker-compose.yml)

```
docker compose -f ./dokploy.docker-compose.yml up -d
```

### Vercel

Import the repository in [Vercel](https://vercel.com/new) and deploy the `main` branch. No extra branch or configuration is needed.

## API Use

Scrapes MyDramaList on request and returns clean, typed JSON.

| Endpoint | Description |
| --- | --- |
| `GET /v2/search?q={query}&page=1` | Search dramas and people |
| `GET /v2/dramas/{slug}` | Drama info |
| `GET /v2/dramas/{slug}/cast` | Full cast and crew, grouped by role |
| `GET /v2/dramas/{slug}/episodes` | Episodes |
| `GET /v2/dramas/{slug}/reviews?page=1` | Reviews |
| `GET /v2/people/{slug}` | Person info and works |
| `GET /v2/lists/{id}?page=1` | A user list |
| `GET /v2/users/{username}/dramalist` | A user's drama list |

`page` is optional and defaults to `1`.

### Response format

Every successful response looks like this. `data` holds only the scraped info.

```js
// GET /v2/people/4444-kim-jong-min
{
  "success": true,
  "data": {
    "name": "Kim Jong Min",
    "nationality": "South Korean",
    "age": 47,
    // ...
  },
  "link": "https://mydramalist.com/people/4444-kim-jong-min",
  "scraped_at": "2026-10-31T08:00:00Z"
}
```

Errors set the real HTTP status (`404`, `422`, `502`, ...) and return:

```js
{
  "success": false,
  "data": null,
  "message": "The requested page was not found. You can see this page because the URL you are accessing cannot be found."
}
```

See [docs/v2.md](docs/v2.md) for what changed from v1.

> [!NOTE]
> The original v1 endpoints are still available and work as before. See [docs/v1.md](docs/v1.md).

### API Endpoints to use

- Primary (Self-Hosted)

  ```
  https://kuryana.tbdh.app
  ```

  - Swagger [`https://kuryana.tbdh.app/docs`](https://kuryana.tbdh.app/docs)

- Vercel deployment

  ```
  https://kuryana.vercel.app
  ```

  - Swagger [`https://kuryana.vercel.app/docs`](https://kuryana.vercel.app/docs)

  > Has quirks like requests failing for first time then succeeding.
  >
  > Please start to transition on using the primary deployed endpoint for your projects, thank you.

## Development

- Minimum Python Version : `3.12`,

- Make sure `uv` is installed in your machine, [more details](https://docs.astral.sh/uv/getting-started/installation/)

- Sync project dependencies

  ```sh
  uv sync
  ```

### Dev Server

Start development server.

```sh
uv run fastapi dev
```

[FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/)

### Project Structure

See [docs/structure.md](docs/structure.md) for the code layout, how a v2 request flows through the app, and how to add a new endpoint.

#### &copy; tbdsux
