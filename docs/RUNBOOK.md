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

## Verify Alertmanager routing

Run `make verify-routing` with Alertmanager on PATH, or supply its binary path with `ALERTMANAGER=/path/to/alertmanager`. The drill starts an isolated loopback webhook and Alertmanager with temporary storage. It submits three fixture alerts to the Alertmanager API and verifies the deliveries and inhibition status.

| Alert | Expected behavior |
| --- | --- |
| Checkout page | Delivered to the page receiver |
| Checkout ticket | Inhibited while the checkout page is active |
| Catalog ticket | Delivered to the ticket receiver |

For a routing failure, check the alert labels, route matchers, and receiver logs. For an inhibition failure, confirm both alerts have the same service label and compare their severity labels. The fixture uses a local receiver.
