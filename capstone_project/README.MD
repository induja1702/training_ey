# Contract Intelligence Chatbot

## LangSmith observability

This project includes optional LangSmith tracing for request and agent-level observability.

Set the following environment variables before running the app:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY=<your-langsmith-api-key>`
- `LANGSMITH_ENDPOINT=https://api.smith.langchain.com` (or your region endpoint)

The app will automatically trace chat requests, upload requests, intent detection, and RAG pipeline steps when LangSmith is installed and enabled.

Example Docker runtime command with a LangSmith API key:

```bash
docker run -e LANGSMITH_TRACING=true \
  -e LANGSMITH_API_KEY="<your-langsmith-api-key>" \
  -e LANGSMITH_ENDPOINT="https://api.smith.langchain.com" \
  -e LANGSMITH_PROJECT="contract_intelligence" \
  -p 8000:8000 capstone_project
```

If you use a LangSmith workspace in another region, set `LANGSMITH_ENDPOINT` accordingly.
