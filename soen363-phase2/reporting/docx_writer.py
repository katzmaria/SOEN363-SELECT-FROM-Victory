"""
A small .docx writer that only uses the Python standard library (zipfile + XML text).

Supports what the report needs: title, headings, paragraphs with **bold** and `code` spans, bullet and
numbered lists, code blocks, captions, page breaks and tables (header row repeated on every page).
US Letter, 1-inch margins, page numbers in the footer.
"""

from __future__ import annotations

import re
import zipfile
from xml.sax.saxutils import escape

PIPELINE_VERSION = "2026.11.15-abcd"

PAGE_W, PAGE_H, MARGIN = 12240, 15840, 1440          # twips (1440 = 1 inch), US Letter
TEXT_W = PAGE_W - 2 * MARGIN                         # 9360
FONT = "Times New Roman"


def _t(text):
    return f'<w:t xml:space="preserve">{escape(str(text))}</w:t>'


def _rpr(bold=False, mono=False, color=None, sz=None):
    """Run properties in the order the schema requires: rFonts, b, color, sz, szCs."""
    x = '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>' if mono else ""
    x += "<w:b/>" if bold else ""
    x += f'<w:color w:val="{color}"/>' if color else ""
    x += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>' if sz else ""
    return f"<w:rPr>{x}</w:rPr>" if x else ""


def _runs(text, bold=False, color=None, sz=None):
    """'**bold**' and '`code`' spans -> runs."""
    out = []
    for part in re.split(r"(\*\*.+?\*\*|`[^`]+`)", str(text)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(f"<w:r>{_rpr(True, False, color, sz)}{_t(part[2:-2].replace('`', ''))}</w:r>")
        elif part.startswith("`") and part.endswith("`"):
            out.append(f"<w:r>{_rpr(bold, False, color, sz)}{_t(part[1:-1])}</w:r>")
        else:
            out.append(f"<w:r>{_rpr(bold, False, color, sz)}{_t(part)}</w:r>")
    return "".join(out)


class Docx:
    def __init__(self):
        self.body = []
        self.nums = []                     # numbering instances: (num_id, abstract_id)
        self.table_no = 0

    # ---- blocks -------------------------------------------------------------
    def p(self, text="", style=None, align=None, keep_next=False):
        ppr = ""
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if keep_next:
            ppr += "<w:keepNext/>"
        if align:
            ppr += f'<w:jc w:val="{align}"/>'
        self.body.append(f"<w:p>{'<w:pPr>' + ppr + '</w:pPr>' if ppr else ''}{_runs(text)}</w:p>")

    def title(self, text, subtitle=None):
        self.p(text, "Title")
        if subtitle:
            self.p(subtitle, "Subtitle")

    def h(self, text, level=1):
        self.p(text, f"Heading{level}")

    def bullets(self, items, numbered=False):
        if numbered:
            num_id = len(self.nums) + 2
            self.nums.append(num_id)
        else:
            num_id = 1
        for it in items:
            self.body.append(f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/>'
                             f'<w:numId w:val="{num_id}"/></w:numPr></w:pPr>{_runs(it)}</w:p>')

    def code(self, lines):
        for ln in lines:
            self.body.append(f'<w:p><w:pPr><w:pStyle w:val="Code"/></w:pPr>{_runs(ln.replace("`", ""))}</w:p>')

    def caption(self, text):
        self.p(text, "Caption")

    def page_break(self):
        self.body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def table(self, header, rows, caption=None, widths=None, font_half_pts=17, max_chars=60):
        """rows: list of lists. widths: relative weights per column (default: from the content)."""
        if not rows:
            self.p("_(no rows)_")
            return
        n = len(header)
        cells = [[("" if v is None else str(v)) for v in r] + [""] * (n - len(r)) for r in rows]
        if widths is None:
            widths = []
            for i in range(n):
                longest = max([len(header[i])] + [len(r[i]) for r in cells])
                widths.append(max(7, min(longest, max_chars)))
        tw = [int(TEXT_W * w / sum(widths)) for w in widths]
        tw[-1] += TEXT_W - sum(tw)
        border = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        x = ['<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblBorders>' % TEXT_W
             + "".join(border.format(b) for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
             + '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="30" w:type="dxa"/><w:left w:w="70" w:type="dxa"/>'
             '<w:bottom w:w="30" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
             "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in tw) + "</w:tblGrid>"]

        def row(values, head=False, shade=None):
            trpr = "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>" if head else "<w:trPr><w:cantSplit/></w:trPr>"
            tcs = []
            for v, w in zip(values, tw):
                fill = "F2F2F2" if head else None
                shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
                runs = _runs(v, bold=head, sz=font_half_pts)
                tcs.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}</w:tcPr>'
                           f'<w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>{runs}</w:p></w:tc>')
            return f"<w:tr>{trpr}{''.join(tcs)}</w:tr>"

        x.append(row(header, head=True))
        for i, r in enumerate(cells):
            x.append(row(r))
        x.append("</w:tbl>")
        self.body.append("".join(x))
        if caption:
            self.table_no += 1
            self.caption(f"Figure {self.table_no}: {caption}")
        else:
            self.p("")

    # ---- package ------------------------------------------------------------
    def save(self, path):
        sect = (f'<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/>'
                f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/><w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" '
                f'w:bottom="{MARGIN}" w:left="{MARGIN}" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')
        doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{"".join(self.body)}{sect}</w:body></w:document>')
        nums = '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>' + "".join(
            f'<w:num w:numId="{n}"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0">'
            f'<w:startOverride w:val="1"/></w:lvlOverride></w:num>' for n in self.nums)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/_rels/document.xml.rels", DOC_RELS)
            z.writestr("word/document.xml", doc)
            z.writestr("word/styles.xml", STYLES)
            z.writestr("word/numbering.xml", NUMBERING.replace("{NUMS}", nums))
            z.writestr("word/footer1.xml", FOOTER)
            z.writestr("docProps/core.xml", CORE)


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>SOEN 363 - Project Phase 2 - Tasks 1 and 2</dc:title>
</cp:coreProperties>"""

FOOTER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>
<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>
<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:t>1</w:t></w:r>
<w:r><w:rPr><w:sz w:val="20"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>"""


def _style(sid, name, ppr="", rpr="", based="Normal", kind="paragraph", nxt=None, outline=None):
    o = f'<w:outlineLvl w:val="{outline}"/>' if outline is not None else ""
    return (f'<w:style w:type="{kind}" w:styleId="{sid}"><w:name w:val="{name}"/>'
            + (f'<w:basedOn w:val="{based}"/>' if based else "") + (f'<w:next w:val="{nxt}"/>' if nxt else "")
            + f'<w:qFormat/><w:pPr>{ppr}{o}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>')


BLACK = '<w:color w:val="000000"/>'
STYLES = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}">'
          f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" '
          f'w:eastAsia="{FONT}"/><w:color w:val="000000"/><w:sz w:val="24"/><w:szCs w:val="24"/>'
          '<w:lang w:val="en-CA"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
          '<w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
          + _style("Normal", "Normal", '<w:jc w:val="both"/>', based=None)
          + _style("Title", "Title", '<w:spacing w:before="0" w:after="60"/><w:jc w:val="center"/>',
                   f'<w:b/>{BLACK}<w:sz w:val="32"/><w:szCs w:val="32"/>')
          + _style("Subtitle", "Subtitle", '<w:spacing w:before="0" w:after="240"/><w:jc w:val="center"/>',
                   f'{BLACK}<w:sz w:val="24"/>')
          + _style("Heading1", "heading 1", '<w:keepNext/><w:spacing w:before="300" w:after="120" w:line="240" '
                   'w:lineRule="auto"/><w:jc w:val="left"/>', f'<w:b/>{BLACK}<w:sz w:val="28"/><w:szCs w:val="28"/>',
                   nxt="Normal", outline=0)
          + _style("Heading2", "heading 2", '<w:keepNext/><w:spacing w:before="200" w:after="100" w:line="240" '
                   'w:lineRule="auto"/><w:jc w:val="left"/>', f'<w:b/>{BLACK}<w:sz w:val="24"/><w:szCs w:val="24"/>',
                   nxt="Normal", outline=1)
          + _style("Heading3", "heading 3", '<w:keepNext/><w:spacing w:before="160" w:after="80" w:line="240" '
                   'w:lineRule="auto"/><w:jc w:val="left"/>', f'<w:b/>{BLACK}<w:sz w:val="24"/><w:szCs w:val="24"/>',
                   nxt="Normal", outline=2)
          + _style("Caption", "caption", '<w:spacing w:before="60" w:after="200"/><w:jc w:val="center"/>',
                   f'<w:i/>{BLACK}<w:sz w:val="20"/><w:szCs w:val="20"/>')
          + _style("TableText", "Table Text", '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
                   '<w:jc w:val="left"/>', '<w:sz w:val="18"/><w:szCs w:val="18"/>')
          + _style("Code", "Code", '<w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/>'
                   '<w:ind w:left="720"/><w:jc w:val="left"/>', BLACK)
          + _style("ListParagraph", "List Paragraph", '<w:spacing w:after="60"/><w:ind w:left="720" w:hanging="360"/>'
                   '<w:jc w:val="left"/>')
          + "</w:styles>")

NUMBERING = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="{W}">'
             '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0">'
             '<w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#8226;"/><w:lvlJc w:val="left"/>'
             '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>'
             '</w:rPr></w:lvl></w:abstractNum>'
             '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0">'
             '<w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
             '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
             "{NUMS}</w:numbering>")
