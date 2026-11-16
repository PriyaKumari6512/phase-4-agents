"""Client files (inputs.py): copied into inputs/round-N/, never overwritten,
and converted to Markdown when agents can't read the original.
"""

import zipfile
from email.message import EmailMessage

import pytest

from agent_engine import cli, inputs

_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
_A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@pytest.fixture(autouse=True)
def outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(inputs, "OUTPUTS_DIR", tmp_path / "outputs")
    return tmp_path / "outputs"


def _docx(path, text):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'))
        z.writestr("_rels/.rels", (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="word/document.xml"/></Relationships>'))
        z.writestr("word/document.xml", f"<w:document {_W}><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>")
    return path


def _pptx(path, slides):
    """slides: list of (text, notes or None)."""
    with zipfile.ZipFile(path, "w") as z:
        for i, (text, notes) in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", f"<p:sld {_A} xmlns:p='p'><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:sld>")
            if notes:
                z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", (
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="rId2" Type="{_REL}/notesSlide" Target="../notesSlides/notesSlide{i}.xml"/>'
                    "</Relationships>"))
                z.writestr(f"ppt/notesSlides/notesSlide{i}.xml", f"<p:notes {_A} xmlns:p='p'><a:p><a:r><a:t>{notes}</a:t></a:r></a:p></p:notes>")
    return path


def test_first_upload_is_round_1_and_next_is_a_new_round(tmp_path):
    (tmp_path / "a.txt").write_text("Members renew online", encoding="utf-8")
    (tmp_path / "b.txt").write_text("WhatsApp reminders", encoding="utf-8")
    assert inputs.add_inputs("gym", [tmp_path / "a.txt"])[0] == 1
    assert inputs.add_inputs("gym", [tmp_path / "b.txt"])[0] == 2
    assert inputs.existing_rounds("gym") == [1, 2]


def test_explicit_round_adds_to_it(tmp_path, outputs):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.txt").write_text("y", encoding="utf-8")
    inputs.add_inputs("gym", [tmp_path / "a.txt"])
    number, _ = inputs.add_inputs("gym", [tmp_path / "b.txt"], round_number=1)
    assert number == 1
    assert sorted(p.name for p in (outputs / "gym/inputs/round-1").iterdir()) == ["a.txt", "b.txt"]


def test_uploaded_files_are_never_overwritten(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    inputs.add_inputs("gym", [tmp_path / "a.txt"])
    with pytest.raises(ValueError, match="never overwritten"):
        inputs.add_inputs("gym", [tmp_path / "a.txt"], round_number=1)


def test_nothing_is_copied_when_one_file_is_missing(tmp_path, outputs):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="is not a file"):
        inputs.add_inputs("gym", [tmp_path / "a.txt", tmp_path / "missing.pdf"])
    assert not (outputs / "gym").exists()


def test_pdf_and_images_are_read_directly(tmp_path):
    (tmp_path / "rfp.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
    (tmp_path / "screen.PNG").write_bytes(b"\x89PNG\r\n\x1a\n")
    _, added = inputs.add_inputs("gym", [tmp_path / "rfp.pdf", tmp_path / "screen.PNG"])
    assert all(a.read_as == a.path for a in added)


def test_word_is_converted_to_markdown(tmp_path):
    _, [added] = inputs.add_inputs("gym", [_docx(tmp_path / "brd.docx", "Members can renew online")])
    assert added.read_as.name == "brd.docx.md"
    assert "Members can renew online" in added.read_as.read_text(encoding="utf-8")


def test_excel_is_converted_to_a_table_per_sheet(tmp_path):
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.active.title = "Plans"
    workbook.active.append(["Plan", "Price | INR"])
    workbook.active.append(["Monthly", 1500])
    workbook.save(tmp_path / "plans.xlsx")
    _, [added] = inputs.add_inputs("gym", [tmp_path / "plans.xlsx"])
    text = added.read_as.read_text(encoding="utf-8")
    assert "## Sheet: Plans" in text and "| Monthly | 1500 |" in text and "Price \\| INR" in text


def test_powerpoint_keeps_slide_order_and_notes(tmp_path):
    deck = _pptx(tmp_path / "pitch.pptx", [("Online sign-up", "Client wants UPI"), ("Owner dashboard", None)])
    _, [added] = inputs.add_inputs("gym", [deck])
    text = added.read_as.read_text(encoding="utf-8")
    assert text.index("## Slide 1") < text.index("Online sign-up") < text.index("## Slide 2")
    assert "Notes: Client wants UPI" in text


def test_email_keeps_subject_body_and_lists_attachments(tmp_path):
    message = EmailMessage()
    message["Subject"] = "Answers to your questions"
    message["From"] = "Owner <owner@example.com>"
    message["To"] = "ba@example.com"
    message.set_content("Reminders on WhatsApp only.")
    message.add_attachment(b"%PDF", maintype="application", subtype="pdf", filename="plans.pdf")
    (tmp_path / "answers.eml").write_bytes(message.as_bytes())
    _, [added] = inputs.add_inputs("gym", [tmp_path / "answers.eml"])
    text = added.read_as.read_text(encoding="utf-8")
    assert "# Email: Answers to your questions" in text
    assert "Reminders on WhatsApp only." in text and "plans.pdf" in text


@pytest.mark.parametrize("name, hint", [("old.doc", "save it as .docx"), ("call.mp3", "upload a transcript"), ("blob.bin", "save it as PDF")])
def test_unreadable_files_are_kept_with_a_hint(tmp_path, name, hint):
    (tmp_path / name).write_bytes(b"\xff\xfe\x00\x81binary")
    _, [added] = inputs.add_inputs("gym", [tmp_path / name])
    assert added.path.is_file() and added.read_as is None and hint in added.note


def test_corrupt_office_file_is_kept_and_flagged(tmp_path):
    (tmp_path / "broken.docx").write_bytes(b"not a zip")
    _, [added] = inputs.add_inputs("gym", [tmp_path / "broken.docx"])
    assert added.read_as is None and "could not convert" in added.note
    assert not (added.path.parent / "broken.docx.md").exists()


def test_cli_prints_what_each_file_became(tmp_path, capsys):
    _docx(tmp_path / "brd.docx", "x")
    (tmp_path / "old.doc").write_bytes(b"\xd0\xcf\x11\xe0")
    assert cli._add_inputs([str(tmp_path / "brd.docx"), str(tmp_path / "old.doc")], "gym", None) == 0
    out = capsys.readouterr().out
    assert "Round 1:" in out and "converted to brd.docx.md" in out and "NOT READABLE: old Word format" in out
