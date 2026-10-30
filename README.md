# Property Finder AI

Streamlit real-estate search app with deterministic filters and an optional Groq AI summary.

## Required Streamlit Secrets

In Streamlit Cloud → Settings → Secrets:

```toml
GROQ_API_KEY = "your_new_rotated_groq_key"
GROQ_MODEL = "llama-3.1-8b-instant"
```

The app works without the key: location, BHK, budget, and text filtering remain available. The Groq call is made only after matching properties are found.

## Security

The old repository version contained a hard-coded Groq key. It has been removed from `app.py`. That old key must be revoked/rotated in the Groq console because removing it from the latest commit does not make the old value safe.

## Property data

The current `properties.txt` labelled format is supported. Pipe-separated rows are also supported:

```text
title | location | bhk | price_lakhs | details
```
