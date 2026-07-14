# Cognee memory installed

Run:

```bash
hermes memory setup cognee
```

Your Cognee service must be reachable and run with `CACHING=true`. If authentication is enabled, provide a Cognee API key during setup; Hermes stores it in the active profile's `.env` as `COGNEE_API_KEY`.

Then verify:

```bash
hermes memory status
curl -fsS http://localhost:8000/health
```
