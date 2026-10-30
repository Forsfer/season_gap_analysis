# Analys över hur gapet mellan tv-säsonger har förändrats


# Om TMDB-API:et och inhämtning
Projektet hämtar data från [The Movie Database (TMDB)](https://www.themoviedb.org/) via deras API. För fullständig dokumentation, se [TMDB:s API-dokumentation](https://developer.themoviedb.org/docs).

## Autentisering
Hos TMDB kan man skapa konto och få en API-nyckel som man lägger in i .env som värde i variabeln "api_key"

## Hur man kör hämtningen
Kör från projektets rot, i den här ordningen:
```bash
uv run python src/fetch_ids.py       # hämtar id:n för serierna i urvalet
uv run python src/fetch_details.py   # hämtar detaljer för varje id
```

## Begränsningar i och felhantering av API:et
- **Rate limit:** TMDB anger en övre gräns på ungefär 40 anrop per sekund, som kan ändras. Projektet pausar 0,25 sekunder mellan anropen.
- **Sidindelning:** `discover` returnerar högst 500 sidor (10 000 resultat). Med nuvarande filter ligger urvalet under den gränsen, men `fetch_ids` loggar antalet sidor så att det syns om den nås.
- **Nya försök:** `api_client.py` försöker automatiskt igen upp till 3 gånger vid nätverksfel och statuskoderna 429, 500, 502, 503 och 504, med ökande väntetid. Vid 429 följs `Retry-After` från servern.
- **Övriga fel** (t.ex. 401, 404) försöks inte igen. Anropet loggas som varning och hoppas över, och misslyckade sidor eller serier listas i slutet av körningen.
- Om första sidan i `fetch_ids` misslyckas avbryts körningen.
- Timeout per anrop är 10 sekunder.

## Kända egenheter
- **Säsong 0 är specials** (extramaterial) och ska filtreras bort i analysen.
- **`air_date` kan saknas** för säsonger som är annonserade men inte har sänts.
- **Säsongsnumreringen följer inte alltid sändningsordningen.** Sortera på `air_date` och inte på `season_number` när väntetid räknas ut.
- **`episode_run_time` är tom för ungefär hälften av serierna** och går inte att använda i analysen.
- **`popularity` och `vote_count` ändras över tid.** Använd `fetched_at` för att veta vilken version av datan som används.
- **Sortering på `popularity` är instabil vid sidindelning.** Serier kan byta sida under hämtningen och dyka upp två gånger eller inte alls. Därför sorteras urvalet på `first_air_date`. Kontrollera ändå att `id` är unikt efter hämtningen.
