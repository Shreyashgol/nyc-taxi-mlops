# 010: Use POST /reload (not restart) for model promotion

Stage: S3 · Date: 2026-11-22 · Author: Shreyash · Drafted by agent: yes

## Choice

When promoting a new champion, the promotion workflow calls `deploy/web.sh reload champion`, which sends `POST /reload` to the running serving-champion container. The old model keeps answering until the new one has loaded, so riders never see a 503.

## Rejected alternative

Restart the serving-champion container after moving the alias. The container's start-up loop (`load_until_available`) would pick up the new version, but during the restart (~10-30 seconds of container boot + model load), Traefik's health check on `/model` would remove the champion from the pool, and all serving traffic would route to the challenger (or 503 if the challenger also has no model). Riders would see either wrong-alias predictions or errors.

## Why

The serving code already supports atomic `/reload`: it holds a lock, loads the new model, warms it up with one prediction, and swaps the reference — the old model answers every request until the swap. Zero downtime for the cost of zero extra complexity (the given `web.sh reload` calls it). Restarting is simpler conceptually but introduces a gap that is avoidable.

## What would show this was wrong

If `/reload` ever leaves the container in a half-loaded state (e.g., memory exhaustion loading two models at once), or if the reload path silently serves stale predictions without updating `lab_model_info`, we would need to revisit in favour of a full restart.
