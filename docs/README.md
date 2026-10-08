# Request Tracker handbook

This folder explains **how every piece of the project works and why it is built that way**. The repository is meant to be a blueprint for a real Angular + Django REST Framework + MySQL system, so the docs focus on patterns you can copy, not only on this app's features.

Each topic follows the same shape where it helps:

- **What it does** and **where it lives** (file paths you can open)
- **Why it is built this way** (the decision and its trade-off)
- **Laravel / Vue equivalent**, since that is the background this project assumes
- **Pitfalls** we actually hit

## Reading order

| # | Document | Read it when you want to understand |
|---|---|---|
| 1 | [Architecture](01-architecture.md) | The big picture: folders, conventions, and how one click travels from the browser to MySQL and back |
| 2 | [Backend](02-backend.md) | Every Django/DRF building block used here: settings, models, serializers, viewsets, services, permissions, workflow, uploads, errors, throttling, logging, OpenAPI |
| 3 | [Frontend](03-frontend.md) | Every Angular/PrimeNG building block: bootstrapping, routing, guards, auth and interceptors, services, signals vs RxJS, forms, PrimeNG, shared components, error handling |
| 4 | [Security](04-security.md) | Authentication, authorization (404 vs 403), upload hardening, throttling, and what must change before production |
| 5 | [Testing](05-testing.md) | How the 113 backend tests are organized and the techniques they use; how to check the frontend |
| 6 | [Recipe: add a new module](06-recipe-new-module.md) | Step-by-step checklist to add your own business module (model to Angular page) the same way |
| 7 | [Troubleshooting](07-troubleshooting.md) | Real problems met while building this, with causes and fixes |
| - | [Build notes](notes.md) | What each phase added and which decisions were made, in order |
| - | [openapi.yaml](openapi.yaml) | The generated API contract (regenerate with `manage.py spectacular`) |

If you only have an hour: read **01**, then the "request lifecycle" part of **02**, then **06**.

## Keeping these docs true

- When you change a rule in `services.py`, update the matching section in `02-backend.md`.
- When you add a module, follow `06-recipe-new-module.md` and add a line to `notes.md`.
- Regenerate `openapi.yaml` after API changes:
  `cd backend && python manage.py spectacular --file ../docs/openapi.yaml --validate`
