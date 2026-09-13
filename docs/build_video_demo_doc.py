"""Build the editable demo-script Word document using standard Open XML."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ET.register_namespace("w", W)


def node(parent, tag, **attributes):
    return ET.SubElement(parent, f"{{{W}}}{tag}", {f"{{{W}}}{key}": value for key, value in attributes.items()})


def paragraph(parent, text, style="Normal"):
    item = node(parent, "p")
    properties = node(item, "pPr")
    node(properties, "pStyle", val=style)
    run = node(item, "r")
    node(run, "t").text = text


def build():
    source = (ROOT / "VIDEO_DEMO_SCRIPT.md").read_text(encoding="utf-8")
    document = ET.Element(f"{{{W}}}document")
    body = node(document, "body")
    spoken_words = 0
    in_main = True
    for line in source.splitlines():
        if not line.strip():
            continue
        if line.startswith("## Recording Setup"):
            in_main = False
        if line.startswith("# "):
            paragraph(body, line[2:], "Title")
        elif line.startswith("## "):
            paragraph(body, line[3:], "Heading1")
        elif line.startswith("> "):
            paragraph(body, line[2:], "Narration")
            if in_main:
                spoken_words += len(re.findall(r"\S+", line[2:]))
        elif line.startswith("On screen:"):
            paragraph(body, line, "StageDirection")
        elif line.startswith("- "):
            paragraph(body, line, "Normal")
        else:
            paragraph(body, line)

    section = node(body, "sectPr")
    node(section, "pgSz", w="12240", h="15840")
    node(section, "pgMar", top="1000", right="1080", bottom="1000", left="1080")

    styles = ET.Element(f"{{{W}}}styles")
    for name, size, color, bold, italic in (
        ("Normal", "22", "243434", False, False),
        ("Title", "40", "0B7169", True, False),
        ("Heading1", "27", "0B7169", True, False),
        ("Narration", "24", "162E2C", False, False),
        ("StageDirection", "20", "536A67", False, True),
    ):
        style = node(styles, "style", type="paragraph", styleId=name)
        node(style, "name", val=name)
        if name != "Normal":
            node(style, "basedOn", val="Normal")
        properties = node(style, "pPr")
        node(properties, "spacing", before="100" if name == "Heading1" else "0", after="100", line="276", lineRule="auto")
        if name in {"Heading1", "Title", "StageDirection"}:
            node(properties, "keepNext")
        if name == "Heading1":
            node(properties, "outlineLvl", val="0")
        run = node(style, "rPr")
        node(run, "rFonts", ascii="Calibri", hAnsi="Calibri")
        node(run, "sz", val=size)
        node(run, "color", val=color)
        if bold:
            node(run, "b")
        if italic:
            node(run, "i")

    parts = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''',
        "word/_rels/document.xml.rels": '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''',
        "word/document.xml": ET.tostring(document, encoding="utf-8", xml_declaration=True),
        "word/styles.xml": ET.tostring(styles, encoding="utf-8", xml_declaration=True),
    }
    output = ROOT / "VIDEO_DEMO_SCRIPT.docx"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            ET.fromstring(archive.read(name))
        saved_text = "\n".join(ET.fromstring(archive.read("word/document.xml")).itertext())
        assert "1,012" in saved_text and "Shorter Backup Cut" in saved_text
    print(f"Created {output.name}; verified ZIP and XML. Main narration: {spoken_words} words.")


if __name__ == "__main__":
    build()
