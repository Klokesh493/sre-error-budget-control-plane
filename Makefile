PYTHON ?= python3

.PHONY: verify
verify:
	$(PYTHON) -B -m unittest discover -s tests -v

PROMTOOL ?= promtool

.PHONY: verify-rules
verify-rules:
	$(PROMTOOL) check rules deploy/prometheus/rules.yml
	$(PROMTOOL) test rules deploy/prometheus/rules.test.yml
