# Case study

## Problem

A short spike can page too early, while a small sustained failure rate can quietly exhaust an error budget. Responders need both short and long windows so an alert indicates a continuing problem.

## Implementation

For each window, divide failed requests by total requests and normalize by the allowable error fraction. A page requires at least 14.4× burn in both the 5-minute and 60-minute windows. A ticket requires at least 6× in both 30 minutes and six hours. Replay reports both triggers and prioritizes the page. If a window has zero total requests, its burn is unknown. Missing or nonconsecutive minute buckets fail validation.

## Validation

Six Python tests passed. The healthy fixture returned `healthy`; the incident returned `page`. promtool parsed both rules and checked that checkout triggered both alerts while healthy catalog triggered neither.

## Limits

Replay uses ordered historical snapshots and does not page responders. Zero traffic and missing scrapes need separate availability alerts in a live Prometheus installation. The Prometheus rules were evaluated with promtool fixtures.
