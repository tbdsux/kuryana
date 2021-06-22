# kuryana

A simple MyDramaList.com scraper api.

This scrapes on the go so it might be slow.

#### THIS SERVICE IS ONLY CREATED TO SATISFY THE NEED FOR AN API FOR [MYDRAMALIST.COM](https://mydramalist.com). THIS WILL BE STOPPED ONCE AN OFFICIAL API WILL BE RELEASED.

### Deploy Your Own

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/git/external?repository-url=https%3A%2F%2Fgithub.com%2FTheBoringDude%2Fkuryana)

## API Use

- [Search for dramas](https://kuryana.vercel.app/search/q/)

```
https://kuryana.vercel.app/search/q/{yourquery}
```

- [Get DRAMA Info](https://kuryana.vercel.app/id/)

```
https://kuryana.vercel.app/id/{mydramalist-slug}
```

- [Get DRAMA Cast](https://kuryana.vercel.app/id/{id}/cast)

```
https://kuryana.vercel.app/id/{mydramalist-slug}/cast
```

- [Get Person(People) Info](https://kuryana.vercel.app/people/)

```
https://kuryana.vercel.app/people/{people-id}
```

- [Get seasonal drama](https://kuryana.vercel.app/seasonal/)

```
https://kuryana.vercel.app/seasonal/{year}/{quarter}
```

## Development

- Using the vercel CLI (`localhost:3000`)
  ```
  vercel dev
  ```
- uvicorn (`localhost:8000`)
  ```
  uvicorn api.main --reload
  ```

## NOTE:

All Requests and SCRAPED Datas are not cached by Vercel or the API itself.

#### &copy; TheBoringDude
