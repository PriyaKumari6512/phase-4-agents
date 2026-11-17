"""Direct typed-record adapter. Divergent/custom Markdown uses the legacy importer."""
import re
from agent_engine.phase4 import files
from agent_engine.phase4.feature_documents import FeatureDocument, render
from agent_engine.phase4.speckit_parse import RawSpec, RawStory, RawTask, PATH_RE


def read_feature(project, directory):
    canonical = f"{directory}/feature.json"
    if not files.exists(project, canonical):
        return None
    document = FeatureDocument.model_validate_json(files.read_text(project, canonical))
    rendered = render(document)
    # Accepted external edits always take precedence over a stale canonical record.
    if any(not files.exists(project, f"{directory}/{name}") or
           files.read_text(project, f"{directory}/{name}") != text for name, text in rendered.items()):
        return None
    stories = [RawStory(s.number, s.title, s.priority,
                       f"As a {s.as_a}, I want {s.i_want}, so that {s.so_that} (source: {', '.join(s.source_ids)})",
                       [(a.given.strip(" ,"), a.when.strip(" ,"), a.then.strip(" .")) for a in s.acceptance], s.source_ids)
               for s in document.stories]
    spec = RawSpec(document.title, stories,
                   [(f"FR-{r.number:03d}", r.text, r.source_ids) for r in document.requirements],
                   list(dict.fromkeys(r for s in document.stories for r in s.source_ids)))
    for story in stories:
        block = rendered['spec.md'].split(f"### User Story {story.num} - ", 1)[1].split('\n', 1)[1]
        story.body = re.split(r'(?m)^#{2,3} ', block, maxsplit=1)[0].strip()
    tasks = []
    for number, phase in enumerate(document.phases, 1):
        for task in phase.tasks:
            paths = " " + " ".join(f"`{p}`" for p in task.file_paths) if task.file_paths else ""
            deps = f" (depends on {', '.join(task.depends_on)})" if task.depends_on else ""
            text = task.description + paths + deps
            tasks.append(RawTask(task.task_id, task.parallel, phase.story_number, text,
                                 number, phase.kind, task.depends_on,
                                 list(dict.fromkeys(PATH_RE.findall(text)))))
    return spec, tasks
