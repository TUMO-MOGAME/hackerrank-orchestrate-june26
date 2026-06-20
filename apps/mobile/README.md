# Mobile client (Expo / React Native)

Capture claim photos on a phone and get a grounded adjudication from the same agent API
(`code/api`) via the shared `ClaimReviewClient`.

```bash
npm install            # from repo root (workspaces)
npm run mobile         # Expo dev server -> scan QR with Expo Go
```

Set the API URL in `app.json` (`expo.extra.apiUrl`) to the deployed API for device testing.

> Status: scaffold — screens (Capture / Review / Decision) built in the front-end step.
