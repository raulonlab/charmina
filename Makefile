#!/usr/bin/make

include .env

help:
	@echo "make"
	@echo "    install"
	@echo "        Install all packages of poetry project locally."
	
install:
	poetry install

poetry-show:
	@poetry show --top-level --outdated --only main

run-gen-python:
	poetry run datamodel-codegen --class-name Transform --input .yaml_templates/transform_template.yml --output charmina/transform.py --input-file-type yaml
	poetry run datamodel-codegen --class-name Metadata --input .yaml_templates/metadata_template.yml --output charmina/metadata.py --input-file-type yaml

### lint
poetry-lint:
	@poetry run pylint ./charmina

### autoflake detect (remove unused imports and variables)
poetry-autoflake:
	@poetry run autoflake --remove-unused-variables --remove-all-unused-imports --recursive --verbose ./charmina

### autoflake fix (remove unused imports and variables)
poetry-autoflake-fix:
	@poetry run autoflake --in-place --remove-unused-variables --remove-all-unused-imports --recursive --verbose ./charmina

### black (prettifier)
poetry-black:
	@poetry run black ./charmina

poetry-fix: poetry-autoflake-fix poetry-black

### Detect and show dependencies
poetry-deptry:
	@poetry run deptry .
