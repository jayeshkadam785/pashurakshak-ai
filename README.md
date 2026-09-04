# PashuRakshak

Livestock health surveillance and decision-support prototype for **SIH 2026 — PS 26128**
(Government of Maharashtra, Maharashtra State Innovation Society): early detection,
prevention and management of livestock diseases.

## What's in this prototype

- **Farmer view** — home dashboard, symptom reporting form
- **Rule-based triage engine** — flags a report as low/moderate/high risk from
  symptoms, animal count affected, and days since onset (see
  `api/index.py::score_report`)
- **Vet/official dashboard** — village-level risk map (Leaflet), a 14-day
  report trend chart (Chart.js), and a case list
- **Advisories page** — multilingual-ready alert feed (English/Marathi/Hindi
  toggle stubbed in the UI)
- **Animal records** — per-animal vaccination/treatment history table

The triage logic is intentionally simple and explainable, not a trained
model — every rule maps to a named clinical/epidemiological signal, which is
honest to demo and easy to defend to judges. It's built so a real ML/stats
model can replace `score_report()` later without touching the rest of the app.

## Project structure

```
pashurakshak/
├── api/
│   └── index.py         # Flask app: pages + /api/triage + /api/reports
├── templates/            # Jinja2 HTML templates
├── static/
│   ├── style.css
│   └── app.js
├── supabase/
│   └── schema.sql        # table definitions (reports, animals, advisories)
├── vercel.json
└── requirements.txt
```

## Run locally

```bash
pip install -r requirements.txt --break-system-packages
python api/index.py
```

Visit http://localhost:5000

Without any environment variables set, the app runs fully in-memory —
reports submitted via the form are scored by the triage engine but not
persisted between server restarts. This is enough to demo the triage flow
and the dashboard (which falls back to sample data if `/api/reports` is
empty).

## Connect Supabase (optional, for persistence)

1. Create a project at [supabase.com](https://supabase.com)
2. In the SQL editor, run `supabase/schema.sql`
3. Set environment variables (locally in a `.env`/shell, and in Vercel's
   project settings for deployment):

```
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-service-or-anon-key>
```

Once these are set, `/api/reports` reads/writes from the `reports` table
instead of the in-memory list.

## Deploy to Vercel

1. Push this folder to a GitHub repo
2. Import the repo in Vercel
3. Vercel auto-detects `vercel.json` and deploys `api/index.py` as a Python
   serverless function, with `/static` served directly
4. Add `SUPABASE_URL` / `SUPABASE_KEY` under **Project Settings → Environment
   Variables** if you want persistence (skip this to run the demo purely
   off sample/in-memory data)

No separate scraper or scheduled job is needed for this PS — all data comes
from farmer/field-worker reports, so there's nothing that needs to run
outside the request/response cycle.

## Where this differs from NADRES v2

ICAR-NIVEDI's NADRES v2 is a national early-warning system built on
institutional sentinel centres reporting monthly. PashuRakshak is designed
as the missing **last-mile layer**: real-time, farmer-facing symptom
reporting at the village/block level, feeding structured data upward
rather than duplicating national forecasting.

## Roadmap (beyond the 4-day prototype)

- IVR / offline-first reporting for low-connectivity areas
- Photo-based visual triage (camera → AI diagnosis, alongside the
  symptom-checklist flow)
- Real geospatial clustering instead of static demo markers
- Role-based auth (farmer / vet / district official) via Supabase Auth
