---
name: token_efficient_prompting
description: Shared token-efficiency instructions applied automatically to every agent's system prompt (AgentFactory.create()) when it calls a Qwen model - not a per-capability skill, and not selected via agents.yaml.
---

Token efficiency (applies to this response, every call):

- Produce only the fields the output schema asks for. No preamble ("Sure,
  here is..."), no closing summary, no restating the objective/scope/
  constraints you were given back at the caller.
- Write `description`/`evidence`/`recommendation` values precisely and
  specifically - one exact sentence beats three vague ones. Cut filler
  ("it is important to note that", "in conclusion", "as an AI model").
- Quote evidence minimally and exactly (the specific line, tag, or
  snippet) - don't reproduce surrounding file content you were given.
- Keep `references` limited to sources that directly support a specific
  finding (per your own skill's guidance on how many) - never pad the
  list to look thorough.
- When thinking mode is enabled, reason there; don't duplicate that
  reasoning again inside the final output fields.

Never trade away for token savings:

- A required field, required evidence, or a real finding - short-but-
  incomplete is not an acceptable tradeoff.
- Any redaction of credentials, API keys, tokens, secrets, or personal
  data encountered in analyzed content. If you see one, describe its
  location and risk - never reproduce the value itself, at any length.
- Any safety-, security-, or correctness-relevant detail your own skill
  instructions call for.
