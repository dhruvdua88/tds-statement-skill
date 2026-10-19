.PHONY: help fixtures test golden demo clean install check readme-count ui

help:
	@echo "make fixtures   regenerate the test fixtures (fixtures/means synthetic data)"
	@echo "make test       run the test suite"
	@echo "make golden     regenerate the golden files (look at the diff first)"
	@echo "make demo       run the whole pipeline over the messy fixture into /tmp/tdsdemo"
	@echo "make install    symlink this folder into ~/.claude/skills"
	@echo "make check      environment check for the official utility"
	@echo "make ui         open the guided page in the browser (local only)"
	@echo "make readme-count  rewrite the test count in README.md from the real suite"

fixtures:
	python3 tests/make_fixtures.py

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

golden:
	python3 tests/update_golden.py

ui:
	python3 scripts/tds.py ui

readme-count:
	python3 tests/readme_count.py

check:
	python3 scripts/tds.py check-env

install:
	ln -sfn "$(CURDIR)" "$(HOME)/.claude/skills/tds-statement"
	@echo "linked $(CURDIR) -> ~/.claude/skills/tds-statement"

demo:
	rm -rf /tmp/tdsdemo && mkdir -p /tmp/tdsdemo
	python3 scripts/tds.py intake tests/fixtures/messy_source.xlsx -o /tmp/tdsdemo/statement.json \
	        --form 140 --fy 2026-27 --quarter Q2 --report /tmp/tdsdemo/mapping.xlsx
	python3 scripts/tds.py lint /tmp/tdsdemo/statement.json || true
	python3 scripts/tds.py build /tmp/tdsdemo/statement.json -o /tmp/tdsdemo/build
	python3 scripts/tds.py excel /tmp/tdsdemo/statement.json -o /tmp/tdsdemo/working.xlsx
	python3 scripts/tds.py package /tmp/tdsdemo/statement.json -o /tmp/tdsdemo/deliverables \
	        --txt-dir /tmp/tdsdemo/build --working-paper /tmp/tdsdemo/working.xlsx
	@echo "outputs in /tmp/tdsdemo"

clean:
	rm -rf /tmp/tdsdemo
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
