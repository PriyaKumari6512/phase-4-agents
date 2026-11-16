"""Client files for a project: copied into outputs/<project>/inputs/round-N/,
where agents can read them but never change them (guardrails.py).

deepagents' read_file already sends PDFs and images to the model as
document / image blocks, and reads text files as text. Word, Excel,
PowerPoint and Outlook files it can't read, so each one gets a Markdown copy
next to it (`brd.docx` -> `brd.docx.md`) that agents read instead. Shared by
the CLI's `add-inputs` and, later, the upload API.
"""

from __future__ import annotations

import email
import email.policy
import logging
import re
import shutil
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from agent_engine.config import INPUT_ROUND_PREFIX, INPUTS_DIRNAME, OUTPUTS_DIR, XLSX_MAX_ROWS_PER_SHEET

logger = logging.getLogger(__name__)

# Read by the model as they are (read_file -> image / document block).
NATIVE_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"})
CONVERTED_SUFFIX = ".md"
# Formats we can't read or convert, with what to ask the uploader for instead.
_UNREADABLE_HINTS = {
    ".doc": "old Word format: save it as .docx or PDF",
    ".xls": "old Excel format: save it as .xlsx or CSV",
    ".ppt": "old PowerPoint format: save it as .pptx or PDF",
    ".heic": "save it as JPG or PNG",
    ".heif": "save it as JPG or PNG",
    ".mp3": "audio: upload a transcript",
    ".wav": "audio: upload a transcript",
    ".m4a": "audio: upload a transcript",
    ".mp4": "video: upload a transcript",
    ".mov": "video: upload a transcript",
}


@dataclass(frozen=True)
class AddedInput:
    """One uploaded file. `read_as` is what agents should read: the file
    itself, its Markdown copy, or None when it can't be read (`note` says why).
    """

    path: Path
    read_as: Path | None
    note: str = ""


def round_dir(project_name: str, round_number: int) -> Path:
    return OUTPUTS_DIR / project_name / INPUTS_DIRNAME / f"{INPUT_ROUND_PREFIX}{round_number}"


def existing_rounds(project_name: str) -> list[int]:
    inputs_dir = OUTPUTS_DIR / project_name / INPUTS_DIRNAME
    pattern = re.compile(rf"^{re.escape(INPUT_ROUND_PREFIX)}([1-9][0-9]*)$")
    found = (pattern.match(p.name) for p in inputs_dir.iterdir() if p.is_dir()) if inputs_dir.is_dir() else ()
    return sorted(int(m.group(1)) for m in found if m)


def add_inputs(project_name: str, files: list[Path], round_number: int | None = None) -> tuple[int, list[AddedInput]]:
    """Copies `files` into inputs/round-N/ (a new round when `round_number` is
    None) and converts the formats agents can't read. Checks every file
    before copying any, and never overwrites an uploaded file.
    """
    if round_number is None:
        round_number = max(existing_rounds(project_name), default=0) + 1
    if round_number < 1:
        raise ValueError(f"round must be 1 or more, got {round_number}")
    target_dir = round_dir(project_name, round_number)

    problems: list[str] = []
    taken = {p.name for p in target_dir.iterdir()} if target_dir.is_dir() else set()
    for f in files:
        names = {f.name} | ({f.name + CONVERTED_SUFFIX} if f.suffix.lower() in _CONVERTERS else set())
        if not f.is_file():
            problems.append(f"{f} is not a file")
        elif names & taken:
            problems.append(f"{', '.join(sorted(names & taken))} already exists in {target_dir} (uploaded files are never overwritten)")
        taken |= names
    if problems:
        raise ValueError("; ".join(problems))

    target_dir.mkdir(parents=True, exist_ok=True)
    added = []
    for f in files:
        copy = target_dir / f.name
        shutil.copyfile(f, copy)
        added.append(_make_readable(copy))
        logger.info("added input %s -> %s (%s)", f, copy, added[-1].note or "readable")
    return round_number, added


def _make_readable(path: Path) -> AddedInput:
    suffix = path.suffix.lower()
    if suffix in NATIVE_SUFFIXES:
        return AddedInput(path, path)
    if suffix in _CONVERTERS:
        try:
            markdown = _CONVERTERS[suffix](path)
        except Exception as e:  # a corrupt or password-protected file: keep it, say so
            logger.warning("could not convert %s: %s", path, e)
            return AddedInput(path, None, f"could not convert it ({e}): save it as PDF and upload that")
        converted = path.with_name(path.name + CONVERTED_SUFFIX)
        converted.write_text(f"<!-- {path.name}, converted to Markdown by agent-engine -->\n\n{markdown}", encoding="utf-8")
        return AddedInput(path, converted, f"converted to {converted.name}")
    if suffix in _UNREADABLE_HINTS:
        return AddedInput(path, None, _UNREADABLE_HINTS[suffix])
    if _is_text(path):
        return AddedInput(path, path)
    return AddedInput(path, None, f"agents can't read {suffix or 'this'} files: save it as PDF")


def _is_text(path: Path) -> bool:
    try:
        with path.open("rb") as source:
            source.read(65536).decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


# --- Converters: file -> Markdown ------------------------------------------------


def _docx(path: Path) -> str:
    import mammoth

    with path.open("rb") as f:
        markdown = mammoth.convert_to_markdown(f).value
    # mammoth escapes punctuation that is harmless here ("\(", "\-", "\."); keep
    # only the escapes that change meaning (\* \_ \\ \[ \]), to save tokens.
    return re.sub(r"\\([()\-.+!#>{}])", r"\1", markdown)


def _xlsx(path: Path) -> str:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sections = []
    try:
        for sheet in workbook.worksheets:
            rows, omitted, width = [], 0, 0
            for row in sheet.iter_rows(values_only=True):
                values = ["" if v is None else str(v) for v in row]
                if not any(cell.strip() for cell in values):
                    continue
                width = max(width, len(values))
                if len(rows) <= XLSX_MAX_ROWS_PER_SHEET:
                    rows.append(values)
                else:
                    omitted += 1
            text = _markdown_table([r + [""] * (width - len(r)) for r in rows]) if rows else "(empty)"
            if omitted:
                text += f"\n({omitted} more rows not shown)"
            sections.append(f"## Sheet: {sheet.title}\n\n{text}")
    finally:
        workbook.close()
    return "\n\n".join(sections)


def _markdown_table(rows: list[list[str]]) -> str:
    width = max(len(r) for r in rows)
    kept = rows[: XLSX_MAX_ROWS_PER_SHEET + 1]
    cells = [[c.replace("|", "\\|").replace("\n", " ") for c in r + [""] * (width - len(r))] for r in kept]
    lines = ["| " + " | ".join(cells[0]) + " |", "|" + " --- |" * width]
    lines += ["| " + " | ".join(r) + " |" for r in cells[1:]]
    if len(rows) > len(kept):
        lines.append(f"\n({len(rows) - len(kept)} more rows not shown)")
    return "\n".join(lines)


_DRAWINGML = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _pptx(path: Path) -> str:
    """Text of each slide, plus its speaker notes, in slide order."""
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        slide_re = re.compile(r"^ppt/slides/slide([0-9]+)\.xml$")
        slides = sorted((int(m.group(1)), n) for n in names if (m := slide_re.match(n)))
        sections = []
        for number, name in slides:
            text = _drawing_text(z.read(name))
            notes_name = _notes_for(z, names, name)
            notes = _drawing_text(z.read(notes_name)) if notes_name else ""
            sections.append(f"## Slide {number}\n\n{text or '(no text)'}" + (f"\n\nNotes: {notes}" if notes else ""))
    return "\n\n".join(sections)


def _drawing_text(xml: bytes) -> str:
    paragraphs = ("".join(t.text or "" for t in p.iter(f"{_DRAWINGML}t")) for p in ElementTree.fromstring(xml).iter(f"{_DRAWINGML}p"))
    return "\n".join(p for p in paragraphs if p.strip())


def _notes_for(z: zipfile.ZipFile, names: set[str], slide_name: str) -> str | None:
    rels = slide_name.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    if rels not in names:
        return None
    for rel in ElementTree.fromstring(z.read(rels)):
        target = rel.get("Target", "")
        if "notesSlide" in target:
            name = "ppt/" + target.removeprefix("../")
            return name if name in names else None
    return None


def _eml(path: Path) -> str:
    message = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    body_part = message.get_body(preferencelist=("plain", "html"))
    body = body_part.get_content() if body_part else ""
    if body_part is not None and body_part.get_content_type() == "text/html":
        body = _html_text(body)
    attachments = [a.get_filename() or "(unnamed)" for a in message.iter_attachments()]
    return _email_markdown(
        subject=message.get("subject", ""), sender=message.get("from", ""), to=message.get("to", ""),
        date=message.get("date", ""), body=body, attachments=attachments,
    )


def _msg(path: Path) -> str:
    """Outlook .msg: an OLE file whose properties are streams named by tag
    (001F = UTF-16 string, 001E = 8-bit string)."""
    import olefile

    with olefile.OleFileIO(str(path)) as ole:

        def prop(tag: str) -> str:
            for kind, encoding in (("001F", "utf-16-le"), ("001E", "cp1252")):
                stream = f"__substg1.0_{tag}{kind}"
                if ole.exists(stream):
                    return ole.openstream(stream).read().decode(encoding, errors="replace").rstrip("\x00")
            return ""

        attachments = sorted(
            {
                ole.openstream(entry).read().decode("utf-16-le", errors="replace").rstrip("\x00")
                for entry in ("/".join(e) for e in ole.listdir())
                if entry.startswith("__attach_") and entry.endswith("__substg1.0_3707001F")
            }
        )
        return _email_markdown(
            subject=prop("0037"), sender=prop("0C1A"), to=prop("0E04"), date="", body=prop("1000"), attachments=attachments,
        )


def _email_markdown(*, subject: str, sender: str, to: str, date: str, body: str, attachments: list[str]) -> str:
    header = [f"From: {sender}", f"To: {to}"] + ([f"Date: {date}"] if date else [])
    text = f"# Email: {subject or '(no subject)'}\n\n" + "\n".join(header) + f"\n\n{body.strip()}"
    if attachments:
        text += "\n\nAttachments (not converted; upload them separately): " + ", ".join(attachments)
    return text


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("br", "p", "div", "li", "tr"):
            self.parts.append("\n")


def _html_text(markup: str) -> str:
    parser = _TextOnly()
    parser.feed(markup)
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()


_CONVERTERS = {".docx": _docx, ".xlsx": _xlsx, ".pptx": _pptx, ".eml": _eml, ".msg": _msg}
