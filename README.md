<div align="center">
  <h1>kuryana</h1>

  <p>A simple MyDramaList.com scraper api.</p>
  <p>This scrapes on the go so it might be slow.</p>

  <h4>THIS SERVICE IS ONLY CREATED TO SATISFY THE NEED FOR AN API FOR [MYDRAMALIST.COM](https://mydramalist.com). THIS WILL BE STOPPED ONCE AN OFFICIAL API WILL BE RELEASED.</h4>

</div>

## Deployment

### Self Hosted - Docker

```sh
# run
docker compose up -d --build

# take down
docker compose down
```

#### [Dokploy](Dokploy)

[dokploy.docker-compose.yml](./dokploy.docker-compose.yml)

```
docker compose -f ./dokploy.docker-compose.yml up -d
```

### [Vercel](https://github.com/tbdsux/kuryana/tree/deploy/vercel)

Make sure to set `deploy/vercel` as the branch.

> [!NOTE]
> Deployed vercel project will still continue to live.

## API Use

- Search for dramas

```sh
GET /search/q/{yourquery}
```

- Get DRAMA Info

```sh
GET /id/{mydramalist-slug}
```

- Get DRAMA Cast

```sh
GET /id/{mydramalist-slug}/cast
```

- Get DRAMA Episodes

```sh
GET /id/{mydramalist-slug}/episodes
```

- Get DRAMA Reviews

```sh
GET /id/{mydramalist-slug}/reviews
```

- Get Person(People) Info

```sh
GET /people/{people-id}
```

- Get seasonal drama

```sh
GET /seasonal/{year}/{quarter}
```

- Get Lists

```sh
GET /list/{id}
```

- Get User Dramalist

```sh
GET /dramalist/{user_id}
```

### API Endpoints to use

- Primary (Self-Hosted)

  ```
  https://kuryana.tbdh.app
  ```

  - Swagger [`https://kuryana.tbdh.app/docs`](https://kuryana.tbdh.app/docs)

- Vercel deployment (`deploy/vercel` branch)

  ```
  https://kuryana.vercel.app
  ```

  - Swagger [`https://kuryana.vercel.app/docs`](https://kuryana.vercel.app/docs)

  > Has quirks like requests failing for first time then succeeding.
  >
  > Please start to transition on using the primary deployed endpoint for your projects, thank you.

### Error Messages

```js
// mainly on all endpoints except `search`
// sample: /list/unknown-random-id
{
  "code": 400,
  "error": true,
  "description": {
    "title": "This list is private.",
    "info": "You can see this page because the URL you are accessing cannot be found."
  }
}
```

```js
// could also be this (only on `/search`) endpoint
{
  "error": true,
  "code": 404,
  "description": "404 Not Found"
}
```

### API Wrappers

A JS/TS and Python api wrappers are currently available. [Learn More...](https://gitea.com/tbdsux/kuryana-api-wrappers)

#### JS/TS

```ts
import { Kuryana } from "@tbdhdev/kuryana-ts";

async function main() {
  const kuryana = new Kuryana();
  // const kuryana = new Kuryana("https://custom-endpoint.net");

  const res = await kuryana.search("goblin");

  if (!res.success) {
    console.error("Search failed:", res.error);
    return;
  }

  // log results
  for (const item of res.result.results.dramas) {
    console.log("Drama:", item.title);
    console.log("Year:", item.year);
    console.log("-----\n");
  }
}

main();
```

#### Python

```python
from kuryana import Kuryana

client = Kuryana()


if __name__ == "__main__":
    response = client.get()
    print(response.message)

    assert "MDL Scraper API" in response.message

    print("\n\n")

    search = client.search("goblin")
    for drama in search.results.dramas:
        print(f"{drama.title} - {drama.year}")

```

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

## Others

> [!NOTE]
> All Requests and SCRAPED Datas are not cached by the API Endpoints.

#### &copy; tbdsux
