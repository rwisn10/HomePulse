# HomePulse

Monitoring serwerów Linux w 2 minuty. Bez Prometheusa i Grafany.
Dashboard w przeglądarce, agent instalowany jedną komendą.

Pokazuje: CPU, RAM, load, temperatury, dyski, sieć, top procesy, status online/offline i historię.

## Szybki start

**1. Serwer (dashboard na porcie 9090):**
```bash
pip install -r requirements.txt
uvicorn server.main:app --host 0.0.0.0 --port 9090
```
albo Docker:
```bash
docker build -t homepulse .
docker run -d -p 9090:9090 -v homepulse-data:/data --name homepulse homepulse
```
Otwórz `http://IP-SERWERA:9090`.

**2. Agent na każdym monitorowanym Linuksie:**
```bash
curl -sSL http://IP-SERWERA:9090/install.sh | sudo bash
```

## Zabezpieczenie tokenem (opcjonalnie)
```bash
HOMEPULSE_TOKEN=mojtajnytoken uvicorn server.main:app --host 0.0.0.0 --port 9090
curl -sSL "http://IP-SERWERA:9090/install.sh?token=mojtajnytoken" | sudo bash
```

## Zmienne środowiskowe agenta
`HOMEPULSE_SERVER`, `HOMEPULSE_TOKEN`, `HOMEPULSE_NAME`, `HOMEPULSE_INTERVAL` (domyślnie 5 s).

## Licencja
MIT
