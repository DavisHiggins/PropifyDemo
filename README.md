# Propify Demo

Propify Demo is the public-facing preview of Propify, a private NBA player prop analytics platform.

## What this demo is for

This build is designed to show the real Propify product structure without exposing proprietary analytics.

It mirrors the private application's:
- home screen
- header and navigation hierarchy
- Analyze / Parlays / Tracking / Learn / Account layout
- single-prop workflow
- parlay workflow structure
- dashboard and knowledge-base sections

## What is interactive

The public demo intentionally allows only one live workflow:

- **Analyze** — users can enter a player, stat, line, and opponent to generate a deterministic demo analysis preview

Everything else is visible as a product preview, but locked:

- Parlays
- Tracking
- Account features
- private metric explanations
- saved picks, grading, and account-linked data

## Why the results are blurred

The real Propify platform includes proprietary modeling, probability logic, tracking, and internal product features.

To keep the public demo professional while protecting private work, most analytical values are intentionally blurred. The public demo focuses on:
- UI
- information architecture
- product flow
- visual polish

## Release framing

This demo communicates that the full Propify platform is planned for broader public release sometime in **2026**, while keeping the exact release window private.

## Tech stack

- Python
- Streamlit
- NumPy
- Pandas

## Notes

This repository is a **public demo only**.

It does **not** include:
- the private production model
- private data pipelines
- authentication logic
- per-user tracking backend
- protected model weights
- internal release-only features
