# Operator runbook

## Reproduce

```sh
make verify
python3 budget.py examples/healthy.json
python3 budget.py examples/incident.json
make verify-rules  # requires promtool
```

## Triage and recovery

For a page, compare short and long burn rates, then check whether traffic is concentrated in one route, region, or deploy version. For insufficient data, verify the request counter and the scrape target before interpreting burn. Keep the release on hold until the latest evidence returns healthy.

## Evidence boundaries

Replay uses ordered historical snapshots and does not page responders. Zero traffic and missing scrapes need separate availability alerts in a live Prometheus installation. The Prometheus rules were evaluated with promtool fixtures.
