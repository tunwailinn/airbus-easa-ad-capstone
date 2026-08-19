.PHONY: demo assistant-api assistant-web assistant-compat assistant-check

demo:
	bash scripts/start_demo.sh

assistant-api:
	.venv/bin/python -m full_corpus_pipeline.assistant_api.app

assistant-web:
	cd apps/web && pnpm dev

assistant-compat:
	.venv/bin/python -m full_corpus_pipeline.assistant_api.validate_warm_compatibility

assistant-check:
	.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -p 'test_assistant_runtime.py'
	cd apps/web && pnpm typecheck && pnpm lint
