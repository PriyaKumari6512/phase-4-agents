# spec-kit skills

`speckit-specify`, `speckit-plan`, `speckit-tasks` and `speckit-analyze` are copied unchanged from
[github/spec-kit](https://github.com/github/spec-kit) 1.3.0 (`specify init --integration claude`), under its MIT
license (`LICENSE-spec-kit`). To upgrade, copy the new `SKILL.md` files over these and the core templates over
`src/agent_engine/phase4/speckit_assets/templates/`.

The skills call `.specify/scripts/bash/*.sh`. This engine has no shell, so the agent calls the `speckit_script`
tool instead, which returns the same JSON (`src/agent_engine/phase4/speckit.py`).
