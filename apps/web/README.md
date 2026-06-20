# Web client (Next.js)

Dashboard for the multi-modal claim-review agent. Calls the deployable FastAPI endpoint
(`code/api`) via the shared `ClaimReviewClient`.

```bash
npm install                      # from repo root (workspaces)
cp apps/web/.env.local.example apps/web/.env.local   # set NEXT_PUBLIC_API_URL
npm run web                      # http://localhost:3000
```

Deploy: Vercel (Next.js native). Set `NEXT_PUBLIC_API_URL` to the deployed API URL.

> Status: scaffold — UI components built in the front-end step.
