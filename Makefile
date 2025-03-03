#!/usr/bin/make

.DEFAULT_GOAL := help
.PHONY: clean help deptry outdated run-gen-python lint style-check style-fix package-check build publish publish-test export-requirements version-tag

# include .env

# Dependencies
### Detect and show dependencies
deptry:
	@poetry run deptry .

### Show outdated dependencies
outdated:
	@poetry show --top-level --outdated --only main

### Export requirements.txt and requirements-dev.txt
export-requirements:
	@poetry export -f requirements.txt --output requirements.txt --without-hashes --without-urls --only main
	@poetry export -f requirements.txt --output requirements-dev.txt --without-hashes --without-urls --only dev

run-gen-python:
	@poetry run datamodel-codegen --class-name Transform --input .yaml_templates/transform_template.yml --output charmina/transform.py --input-file-type yaml
	@poetry run datamodel-codegen --class-name Metadata --input .yaml_templates/metadata_template.yml --output charmina/metadata.py --input-file-type yaml

# Linting and code formatting
### Lint check
lint:
	@poetry run pylint ./charmina

### Check code style
style-check:
	@poetry run autoflake --remove-unused-variables --remove-all-unused-imports --recursive --verbose ./charmina
	@poetry run black --check ./charmina

### Fix code style
style-fix:
	@poetry run autoflake --in-place --remove-unused-variables --remove-all-unused-imports --recursive --verbose ./charmina
	@poetry run black ./charmina

# Build and publish
### Check package
package-check:
	@poetry check --lock

### Build
build:
	rm -rf dist/ build/
	@poetry build

### Publish
publish: style-check package-check build
	@poetry publish

### Publish to test-pypi
publish-test: style-check package-check build
	@poetry publish -r test-pypi

### Create git tag and push
version-tag:
	git tag v$$(poetry version -s)
	git push --tags

# show help: Renders automatically target comments (###). Regular comments (#) ignored
# Based on: https://gist.github.com/prwhite/8168133?permalink_comment_id=2278355#gistcomment-2278355
TARGET_COLOR := $(shell tput -Txterm setaf 6)
BOLD := $(shell tput -Txterm bold)
RESET := $(shell tput -Txterm sgr0)
help:
	@echo ''
	@echo 'Usage:'
	@echo '  make ${TARGET_COLOR}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^### (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 4, RLENGTH); \
      printf "  ${TARGET_COLOR}%-20s${RESET} %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)
