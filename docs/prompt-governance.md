# Prompt Governance

## Rules
- every prompt must be versioned
- prompts must live in files
- prompts must be seeded into the database later
- prompts must link to a schema
- active prompts must be immutable
- no inline prompt strings inside service code

## Prompt roles
- signal_engine
- catalyst_classifier
- trade_reviewer

## Each prompt version must include
- name
- role
- version
- system_prompt
- user_template
- schema_json
- notes
