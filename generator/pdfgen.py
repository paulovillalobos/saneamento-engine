"""Native PDF generation for simulated expedientes: text pages (Helvetica, WinAnsi), simple vector drawings, an image
saved with a .pdf name, PDF/A identification, hidden form fields and a detached CMS signature with the test PKI
(exam/pki). No browser: thousands of documents per minute, and every line's page is known at write time.

finish() and sign() are copied verbatim from exam/build.py (rjue-engine day one); only the PKI path and dates are ours.
"""
import io
import re
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKI = ROOT / "exam" / "pki"
ICC = Path("/System/Library/ColorSync/Profiles/sRGB Profile.icc")
FIXED = "2026-10-27T12:00:00Z"
PDF_DATE = "D:20261027120000Z"
BANNER = "DOCUMENTO SIMULADO - SANEAMENTO-ENGINE - SEM VALOR LEGAL"
W, H, M, LH, FS = 595, 842, 56, 14, 11
CHARS = 88  # Helvetica 11 pt: about this many characters per line between the margins


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _enc(s):
    return s.encode("cp1252", "replace").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def wrap(text, width=CHARS):
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            out.append(line); line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out or [""]


class Doc:
    """Pages of text lines; `page_of` records on which page each paragraph landed (1-based)."""

    def __init__(self, title):
        self.title, self.pages, self.cur, self.y, self.paragraphs = title, [], None, 0, []
        self._new_page()
        self.text(title, bold=True, size=14)
        self.gap(6)

    def _new_page(self):
        self.cur = []
        self.pages.append(self.cur)
        self.y = H - M
        self.cur.append(("text", M, self.y, 7, False, BANNER))
        self.y -= LH

    def gap(self, pts=LH):
        self.y -= pts
        if self.y < M:
            self._new_page()

    def text(self, s, bold=False, size=FS, tag=None):
        """One paragraph; returns the page number it starts on."""
        if self.y - LH < M:
            self._new_page()
        start = len(self.pages)
        for line in wrap(s, int(CHARS * FS / size)):
            if self.y - LH < M:
                self._new_page()
            self.cur.append(("text", M, self.y, size, bold, line))
            self.y -= LH * size / FS
        self.y -= 4
        self.paragraphs.append({"page": start, "text": s, "tag": tag})
        return start

    def rect(self, x, y, w, h, filled=False):
        self.cur.append(("rect", x, y, w, h, filled))

    def line(self, x1, y1, x2, y2):
        self.cur.append(("line", x1, y1, x2, y2))

    def image(self, png_bytes, x, y, w, h):
        self.cur.append(("image", x, y, w, h, png_bytes))

    def render(self):
        objs = []  # list of bytes; object n = index + 1

        def add(b):
            objs.append(b); return len(objs)
        font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        page_ids, images = [], {}
        pages_obj = add(b"")  # placeholder, filled below
        for items in self.pages:
            ops, xobjs = [], {}
            for it in items:
                if it[0] == "text":
                    _, x, y, size, bold, s = it
                    ops.append(b"BT /F%d %d Tf %d %d Td (%s) Tj ET" % (2 if bold else 1, size, x, y, _enc(s)))
                elif it[0] == "rect":
                    _, x, y, w, h, filled = it
                    ops.append(b"%s %d %d %d %d re %s" % (b"0.85 g" if filled else b"0 G 1.2 w", x, y, w, h, b"f 0 g" if filled else b"S"))
                elif it[0] == "line":
                    _, x1, y1, x2, y2 = it
                    ops.append(b"0 G 1 w %d %d m %d %d l S" % (x1, y1, x2, y2))
                elif it[0] == "image":
                    _, x, y, w, h, png_b = it
                    key = id(png_b)
                    if key not in images:
                        iw, ih = struct.unpack(">II", png_b[16:24])
                        raw = _png_rgb(png_b)
                        images[key] = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length %d >>stream\n" % (iw, ih, len(raw)) + raw + b"\nendstream")
                    name = b"/Im%d" % images[key]
                    xobjs[name] = images[key]
                    ops.append(b"q %d 0 0 %d %d %d cm %s Do Q" % (w, h, x, y, name))
            content = b"\n".join(ops)
            cid = add(b"<< /Length %d >>stream\n" % len(content) + content + b"\nendstream")
            res = b"<< /Font << /F1 %d 0 R /F2 %d 0 R >>" % (font1, font2)
            if xobjs:
                res += b" /XObject << " + b" ".join(b"%s %d 0 R" % (n, o) for n, o in xobjs.items()) + b" >>"
            res += b" >>"
            page_ids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R /Resources %s >>" % (pages_obj, W, H, cid, res)))
        objs[pages_obj - 1] = b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % p for p in page_ids) + b"] /Count %d >>" % len(page_ids)
        catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_obj)
        out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, b in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + b + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
        out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, catalog, xref)
        return bytes(out)


def png(width, height, tint):
    """A flat PNG (RGB) of one tint: the 'photograph' and the image-saved-as-pdf trap."""
    raw = b"".join(b"\x00" + bytes([tint, (tint * 3) % 256, (tint * 7) % 256]) * width for _ in range(height))

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _png_rgb(png_b):
    """Raw RGB bytes of a png() image (one IDAT, no filtering beyond the per-row 0 byte)."""
    iw, ih = struct.unpack(">II", png_b[16:24])
    pos, idat = 8, b""
    while pos < len(png_b):
        ln, = struct.unpack(">I", png_b[pos:pos + 4]); kind = png_b[pos + 4:pos + 8]
        if kind == b"IDAT":
            idat += png_b[pos + 8:pos + 8 + ln]
        pos += 12 + ln
    rows = zlib.decompress(idat)
    return b"".join(rows[r * (iw * 3 + 1) + 1: (r + 1) * (iw * 3 + 1)] for r in range(ih))


XMP = """<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:pdf="http://ns.adobe.com/pdf/1.3/">
<pdfaid:part>2</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance>
<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
<xmp:CreatorTool>rjue-engine exam builder</xmp:CreatorTool><xmp:CreateDate>{date}</xmp:CreateDate>
<xmp:ModifyDate>{date}</xmp:ModifyDate><pdf:Producer>rjue-engine exam builder</pdf:Producer>
</rdf:Description></rdf:RDF></x:xmpmeta>
<?xpacket end="w"?>"""


def finish(pdf, title, pdfa=True, fields=None):
    """Normalise with pypdf; optionally add PDF/A identification and hidden form fields."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject,
                               TextStringObject, FloatObject)
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    w.add_metadata({"/Title": title, "/Producer": "rjue-engine exam builder", "/Creator": "rjue-engine exam builder",
                    "/CreationDate": PDF_DATE, "/ModDate": PDF_DATE})
    if pdfa:
        meta = DecodedStreamObject()
        meta.set_data(XMP.format(title=esc(title), date=FIXED).encode("utf-8"))
        meta.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
        w._root_object[NameObject("/Metadata")] = w._add_object(meta)
        icc = DecodedStreamObject()
        icc.set_data(ICC.read_bytes())
        icc.update({NameObject("/N"): NumberObject(3)})
        intent = DictionaryObject({NameObject("/Type"): NameObject("/OutputIntent"), NameObject("/S"): NameObject("/GTS_PDFA1"),
                                   NameObject("/OutputConditionIdentifier"): TextStringObject("sRGB IEC61966-2.1"),
                                   NameObject("/DestOutputProfile"): w._add_object(icc)})
        w._root_object[NameObject("/OutputIntents")] = ArrayObject([w._add_object(intent)])
    if fields:
        page = w.pages[0]
        refs = ArrayObject()
        for name, value in fields:
            field = DictionaryObject({
                NameObject("/FT"): NameObject("/Tx"), NameObject("/T"): TextStringObject(name),
                NameObject("/V"): TextStringObject(value), NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"), NameObject("/F"): NumberObject(4),
                NameObject("/Rect"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(0), FloatObject(0)]),
                NameObject("/P"): page.indirect_reference})
            refs.append(w._add_object(field))
        annots = page.get("/Annots")
        page[NameObject("/Annots")] = ArrayObject((list(annots.get_object()) if annots else []) + list(refs))
        w._root_object[NameObject("/AcroForm")] = DictionaryObject({NameObject("/Fields"): refs})
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()




def sign(pdf, signer_key, field_name="Assinatura1"):
    """Append a detached CMS signature (adbe.pkcs7.detached) as an incremental update."""
    import re
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, NumberObject
    reader = PdfReader(io.BytesIO(pdf))
    size = int(reader.trailer["/Size"])
    root_ref = reader.trailer.raw_get("/Root")
    page_ref = reader.pages[0].indirect_reference
    prev = int(re.findall(rb"startxref\s+(\d+)", pdf)[-1])
    n_sig, n_field, n_acro = size, size + 1, size + 2

    def ser(obj):
        s = io.BytesIO()
        obj.write_to_stream(s)
        return s.getvalue()

    root = DictionaryObject(reader.trailer["/Root"])
    acro_old = root.get("/AcroForm")
    acro = DictionaryObject(acro_old.get_object()) if acro_old is not None else DictionaryObject()
    fields = list(acro.get("/Fields", ArrayObject()).get_object()) if "/Fields" in acro else []
    acro[NameObject("/Fields")] = ArrayObject(fields + [IndirectObject(n_field, 0, reader)])
    acro[NameObject("/SigFlags")] = NumberObject(3)
    root[NameObject("/AcroForm")] = IndirectObject(n_acro, 0, reader)
    page = DictionaryObject(reader.pages[0])
    annots = page.get("/Annots")
    page[NameObject("/Annots")] = ArrayObject((list(annots.get_object()) if annots is not None else [])
                                              + [IndirectObject(n_field, 0, reader)])
    hexlen = 16384
    sig_body = (b"<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /adbe.pkcs7.detached "
                b"/M (" + PDF_DATE.encode() + b") /ByteRange [0 0000000000 0000000000 0000000000] /Contents <"
                + b"0" * hexlen + b"> >>")
    field_body = (f"<< /FT /Sig /T ({field_name}) /V {n_sig} 0 R /Type /Annot /Subtype /Widget "
                  f"/Rect [0 0 0 0] /F 132 /P {page_ref.idnum} 0 R >>").encode()
    out = bytearray(pdf if pdf.endswith(b"\n") else pdf + b"\n")
    offsets = {}
    for num, body in ((root_ref.idnum, ser(root)), (page_ref.idnum, ser(page)), (n_sig, sig_body),
                      (n_field, field_body), (n_acro, ser(acro))):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n"
    for num in sorted(offsets):
        out += f"{num} 1\n{offsets[num]:010d} 00000 n \n".encode()
    trailer = DictionaryObject({NameObject("/Size"): NumberObject(n_acro + 1),
                                NameObject("/Root"): root_ref, NameObject("/Prev"): NumberObject(prev)})
    if "/ID" in reader.trailer:
        trailer[NameObject("/ID")] = reader.trailer["/ID"]
    out += b"trailer\n" + ser(trailer) + f"\nstartxref\n{xref_at}\n%%EOF\n".encode()
    start = out.index(b"/Contents <", offsets[n_sig]) + len(b"/Contents ")
    end = start + hexlen + 2
    byte_range = f"[0 {start:010d} {end:010d} {len(out) - end:010d}]".encode()
    br_at = out.index(b"/ByteRange [", offsets[n_sig]) + len(b"/ByteRange ")
    out[br_at:br_at + len(byte_range)] = byte_range
    signed = bytes(out[:start]) + bytes(out[end:])
    with tempfile.TemporaryDirectory() as tmp:
        data, der = Path(tmp) / "data", Path(tmp) / "sig.der"
        data.write_bytes(signed)
        subprocess.run(["openssl", "cms", "-sign", "-binary", "-noattr", "-md", "sha256", "-in", str(data),
                        "-signer", str(PKI / f"{signer_key}.pem"), "-inkey", str(PKI / f"{signer_key}.key"),
                        "-certfile", str(PKI / "ca.pem"), "-outform", "DER", "-out", str(der)], check=True, capture_output=True)
        sig_hex = der.read_bytes().hex().encode()
        assert len(sig_hex) <= hexlen, "signature larger than the reserved space"
        out[start + 1:start + 1 + len(sig_hex)] = sig_hex
        check = subprocess.run(["openssl", "cms", "-verify", "-binary", "-inform", "DER", "-in", str(der),
                                "-content", str(data), "-CAfile", str(PKI / "ca.pem"), "-out", "/dev/null"],
                               capture_output=True, text=True)
        if "Verification successful" not in check.stderr:
            raise RuntimeError(f"signature self-check failed: {check.stderr.strip()}")
    return bytes(out)


