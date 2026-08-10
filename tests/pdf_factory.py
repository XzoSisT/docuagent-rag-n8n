"""Small PDF fixture builder shared by ingestion tests."""


def build_text_pdf(page_texts: list[str]) -> bytes:
    """Build a tiny valid PDF without adding a PDF generator dependency."""

    page_ids = [4 + index * 2 for index in range(len(page_texts))]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
            f"/Count {len(page_ids)} >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    for page_id, text in zip(page_ids, page_texts, strict=True):
        content_id = page_id + 1
        escaped_text = (
            text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        content = f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET".encode("latin-1")
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii"),
                b"<< /Length "
                + str(len(content)).encode("ascii")
                + b" >>\nstream\n"
                + content
                + b"\nendstream",
            ]
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
