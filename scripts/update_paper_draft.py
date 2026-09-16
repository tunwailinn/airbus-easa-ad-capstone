#!/usr/bin/env python3
"""Script to update and polish the WebSciX 2026 conference paper draft.

Applies:
1. Publication-grade figures (no internal chart titles, vector-like DPI, elegant color palettes).
2. Professional booktabs styling for Table 1.
3. Addition of Table 2: Retrieval Architecture Ablation (E0 vs E4 vs E5-D).
4. Academic textual enhancements:
   - Formal mathematical definitions for RRF and routing.
   - Clarification of Layer A 17-document test derivation (leakage quarantine & scope filtering).
   - Definition of MSN (Manufacturer Serial Number) and detailed error attribution.
   - Discussion of why naive flat-dense RAG fails (0.0% Recall@5).
   - Cleaner paragraph transitions and elimination of redundant whitespace to prevent orphan page spillover.
"""

import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import parse_xml
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

SRC_DOCX = "/Users/tunwailin/Downloads/WebSciX2026_Full_Paper_Draft_Visuals_v4.docx"
OUT_DOCX = "/Users/tunwailin/Downloads/WebSciX2026_Full_Paper_Draft_Visuals_v5.docx"
TMP_DIR = Path("tmp/paper_update")

def main():
    print(f"Loading source document: {SRC_DOCX}")
    doc = docx.Document(SRC_DOCX)

    # -------------------------------------------------------------------------
    # 1. Format Table 1 with professional booktabs style
    # -------------------------------------------------------------------------
    t1 = doc.tables[0]
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t1._tbl.tblPr

    # Remove existing borders if any
    existing_borders = tblPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblBorders')
    if existing_borders is not None:
        tblPr.remove(existing_borders)

    borders = parse_xml(r'''
        <w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:top w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>
            <w:bottom w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblLook = tblPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblLook')
    if tblLook is not None:
        tblLook.addprevious(borders)
    else:
        tblPr.append(borders)

    # Format Header Row
    header_row = t1.rows[0]
    for cell in header_row.cells:
        # Shading
        shd = parse_xml(r'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="F1F5F9"/>')
        cell._tc.get_or_add_tcPr().append(shd)
        # Margins / padding
        mar = parse_xml(r'''
            <w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:top w:w="120" w:type="dxa"/>
                <w:bottom w:w="120" w:type="dxa"/>
                <w:left w:w="160" w:type="dxa"/>
                <w:right w:w="160" w:type="dxa"/>
            </w:tcMar>
        ''')
        cell._tc.get_or_add_tcPr().append(mar)
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            for r in p.runs:
                r.font.bold = True
                r.font.name = "Times New Roman"
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(15, 23, 42)

    # Format Data Rows
    for row in t1.rows[1:]:
        for cell in row.cells:
            mar = parse_xml(r'''
                <w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                    <w:top w:w="100" w:type="dxa"/>
                    <w:bottom w:w="100" w:type="dxa"/>
                    <w:left w:w="160" w:type="dxa"/>
                    <w:right w:w="160" w:type="dxa"/>
                </w:tcMar>
            ''')
            cell._tc.get_or_add_tcPr().append(mar)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(9)
                    r.font.color.rgb = RGBColor(30, 41, 59)

    print("Table 1 formatted with booktabs styling.")

    # -------------------------------------------------------------------------
    # 2. Textual Improvements across Paragraphs
    # -------------------------------------------------------------------------
    for i, p in enumerate(doc.paragraphs):
        # Section 1 (Introduction): Add note on why standard RAG fails
        if p.text.startswith("Large language models (LLMs) offer a natural interface"):
            p.text = (
                "Large language models (LLMs) offer a natural interface to technical corpora, and "
                "retrieval-augmented generation (RAG) reduces dependence on parametric memory by "
                "grounding generation in retrieved passages [2]. Yet a generic “PDF chatbot” is poorly "
                "matched to regulatory maintenance documents: naive flat dense-only retrieval fails completely "
                "(0.00% Recall@5, see Sect. 5.2), as dense embeddings alone cannot resolve alphanumeric "
                "identifiers across unstructured chunks. First, physically separate PDFs may belong to the "
                "same directive lifecycle; retrieving across versions can mix obsolete and current requirements. "
                "Second, evidence must remain traceable to an exact AD, page, section, and source file rather "
                "than to a paraphrased intermediate representation. Third, corpus-wide discovery must be evaluated "
                "without leaking the target document identifier. Finally, the system must be able to say that evidence "
                "is insufficient when an AD points to an external approved publication instead of reproducing the procedure itself."
            )
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)

        # Section 3.2: Formalize two-mode routing
        if p.text.startswith("Queries are routed into known-document and discovery conditions"):
            p.text = (
                "Queries are routed deterministically into known-document and discovery conditions. "
                "Let q denote the user query. The router parses exact AD identifiers without an LLM: "
                "if an explicit AD number is detected, q is scoped to D_AD; otherwise, q is treated as a discovery "
                "query over the full operational corpus D_corpus. For known-document questions, the detected AD number "
                "constrains the candidate scope, but the identifier itself is removed from the query string used for "
                "passage ranking to prevent trivial keyword bias. For discovery questions, no target identifier is supplied, "
                "forcing retrieval to identify the authoritative source across all 1,786 operational documents. The live "
                "assistant additionally permits one explicit AD context for conversational follow-ups, without injecting "
                "unrestricted conversational history into the frozen retrieval path."
            )
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)

        # Section 3.3: Formalize RRF equation inline
        if p.text.startswith("The selected E5-C candidate generator preserves deterministic"):
            p.text = (
                "The selected E5-C candidate generator preserves deterministic known-document routing and introduces "
                "Qwen3 dense retrieval for identifier-free discovery. For discovery, BM25 sparse scores and normalized "
                "Qwen3-Embedding-0.6B cosine similarities are fused at the document level using Reciprocal Rank Fusion (RRF) [6]. "
                "Formally, for each candidate d in candidate set D, the reciprocal rank score is computed as "
                "RRF(d) = \\sum_{m \\in \\mathcal{M}} 1/(k + r_m(d)), where \\mathcal{M} = {BM25, Dense}, k = 60 is the "
                "smoothing constant, and r_m(d) is the ordinal rank in system m. Lexical and dense passage rankings are "
                "fused again within shortlisted ADs. Dense document vectors are precomputed against the frozen chunk order, "
                "with row alignment and vector norms verified before query execution. This hybrid fusion leverages exact lexical "
                "matching for technical part numbers and modification tags while enabling semantic matching when user query "
                "terminology diverges from the regulatory text."
            )
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)

        # Section 5.1: Clarify Layer A 17 ADs clean test derivation
        if p.text.startswith("On the clean locked Layer A test, prediction coverage"):
            p.text = (
                "On the clean locked Layer A test, prediction coverage and schema validity were both 1.0000 across all "
                "17 evaluated ADs. The clean test partition reflects the rigorous exclusion of two non-Airbus approval-holder "
                "records and one document (2024-0038) quarantined due to development tuning diagnosis, preventing test-set "
                "leakage. Stable metadata macro F1 was 0.9831, applicability-model F1 was 0.9222, reference-number F1 was 0.9000, "
                "and superseded-AD-number F1 was 0.6667. All five difficult raw-section presence measures achieved 1.0000. "
                "Most importantly for evidence grounding, all 74 evaluated source quotations were contained in the declared source "
                "with zero detected contamination. The lower supersedure score indicates that lifecycle normalization remains more "
                "difficult than direct stable metadata extraction, motivating the explicit document-family layer used downstream."
            )
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)

        # Section 5.2: Introduce Table 2 ablation comparison and define MSN
        if p.text.startswith("The final benchmark produced 35/36 Recall@5 (97.22%)"):
            p.text = (
                "The final benchmark produced 35/36 Recall@5 (97.22%) on answerable retrieval questions and 38/40 human semantic "
                "passes (95.0%) end to end. Known-document retrieval remained perfect at 24/24 (100%), while identifier-free discovery "
                "achieved 11/12 Recall@5 (91.67%). As summarized in Table 2, this represents a substantial architectural progression "
                "over the flat dense baseline (E0: 0.00% Recall@5) and section-aware hybrid retrieval without reranking (E4: 40.91% Recall@5). "
                "The two primary final failures had distinct origins: E5F-021 was a retrieval candidate-generation failure, whereas E5F-011 "
                "had sufficient retrieved evidence but failed in answer selection/completeness (the model generated lower-deck cargo door part numbers "
                "rather than specifying the required Manufacturer Serial Numbers (MSNs) up to 09287 and production modification 12046). "
                "A later oracle-evidence diagnostic made both cases answerable, confirming the retrieval bottleneck for E5F-021 and demonstrating "
                "that E5F-011 was sensitive to evidence focus. These diagnostics serve as explanatory audits and do not alter the authoritative 38/40 score."
            )
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)

    print("Paragraph text enhancements applied.")

    # -------------------------------------------------------------------------
    # 3. Insert Table 2 (Retrieval Architecture Ablation) after Fig 3
    # -------------------------------------------------------------------------
    # Find paragraph containing caption for Fig 3
    fig3_p_idx = -1
    for i, p in enumerate(doc.paragraphs):
        if p.text.startswith("Fig. 3."):
            fig3_p_idx = i
            break

    if fig3_p_idx != -1:
        # We will insert Table 2 after the paragraph following Fig 3
        insert_p = doc.paragraphs[fig3_p_idx + 1]

        # Add table title / caption
        p_cap = insert_p.insert_paragraph_before("Table 2. Retrieval architecture ablation on locked AD questions.")
        p_cap.style = 'Caption'
        p_cap.paragraph_format.space_before = Pt(6)
        p_cap.paragraph_format.space_after = Pt(3)
        p_cap.paragraph_format.keep_with_next = True
        for r in p_cap.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(9)
            r.font.bold = True

        # Create Table 2
        t2 = doc.add_table(rows=4, cols=6)
        t2.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr2 = t2._tbl.tblPr
        tblLook2 = tblPr2.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblLook')
        borders2 = parse_xml(r'''
            <w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:top w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>
                <w:bottom w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
                <w:left w:val="none"/>
                <w:right w:val="none"/>
                <w:insideV w:val="none"/>
            </w:tblBorders>
        ''')
        if tblLook2 is not None:
            tblLook2.addprevious(borders2)
        else:
            tblPr2.append(borders2)

        headers2 = ["Architecture Stage", "Chunking Strategy", "Candidate Generator", "Reranker", "Recall@5", "Semantic Acc."]
        data2 = [
            ["E0: Flat Dense Baseline", "Flat (<=350 tokens)", "MiniLM-L6-v2 (Dense only)", "None", "0.00%", "—"],
            ["E4: Section-Aware Hybrid", "Section (<=450 tokens)", "BM25 + MiniLM-L6-v2 (RRF)", "MiniLM Cross-Encoder", "40.91%", "—"],
            ["E5-D: Proposed System", "Section (<=450 tokens)", "BM25 + Qwen3-0.6B (RRF)", "Qwen3-Reranker-0.6B", "97.22%", "95.00%"]
        ]

        for c_idx, title in enumerate(headers2):
            cell = t2.rows[0].cells[c_idx]
            cell.text = title
            shd = parse_xml(r'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:fill="F1F5F9"/>')
            cell._tc.get_or_add_tcPr().append(shd)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.keep_with_next = True
                for r in p.runs:
                    r.font.bold = True
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(8)
                    r.font.color.rgb = RGBColor(15, 23, 42)

        for r_idx, row_vals in enumerate(data2):
            row = t2.rows[r_idx + 1]
            for c_idx, val in enumerate(row_vals):
                cell = row.cells[c_idx]
                cell.text = val
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(1)
                    p.paragraph_format.space_after = Pt(1)
                    if r_idx < 2:
                        p.paragraph_format.keep_with_next = True
                    for r in p.runs:
                        r.font.name = "Times New Roman"
                        r.font.size = Pt(8)
                        if r_idx == 2:  # Highlight E5-D
                            r.font.bold = True
                            r.font.color.rgb = RGBColor(2, 132, 199)
                        else:
                            r.font.color.rgb = RGBColor(51, 65, 85)

        # Move Table 2 to be before insert_p in XML body
        insert_p._p.addprevious(p_cap._p)
        insert_p._p.addprevious(t2._tbl)
        print("Table 2 (Retrieval Ablation) inserted successfully.")

    # -------------------------------------------------------------------------
    # 4. Spacing Optimization & Empty Paragraph Removal
    # -------------------------------------------------------------------------
    # Remove empty paragraphs
    removed_empty = 0
    for p in list(doc.paragraphs):
        if len(p.text.strip()) == 0 and 'w:drawing' not in p._p.xml:
            p._p.getparent().remove(p._p)
            removed_empty += 1
    print(f"Removed {removed_empty} empty paragraphs.")

    # Adjust spacing on captions, headings, and references for tight LNCS typography
    for p in doc.paragraphs:
        if p.style.name.startswith("Heading"):
            p.paragraph_format.space_before = Pt(7)
            p.paragraph_format.space_after = Pt(2.5)
        elif p.style.name == "Caption":
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(4)
            if p.text.startswith("Table"):
                p.paragraph_format.keep_with_next = True
        elif p.style.name == "Reference":
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.0
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(8.5)

        if 'w:drawing' in p._p.xml:
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)

    # -------------------------------------------------------------------------
    # 5. Drawing Extents via python-docx's native lxml elements
    # -------------------------------------------------------------------------
    new_extents = {
        'rId9': (3501750, 1450000),   # Fig 1: 3.83 in x 1.59 in
        'rId10': (3204600, 1050000),  # Fig 2: 3.50 in x 1.15 in
        'rId11': (3222000, 1200000),  # Fig 3: 3.52 in x 1.31 in
        'rId12': (3761100, 1350000),  # Fig 4: 4.11 in x 1.48 in
        'rId13': (3410500, 950000)    # Fig 5: 3.73 in x 1.04 in
    }
    ns = {
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    }
    for p in doc.paragraphs:
        for drawing in p._p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'):
            extent = drawing.find('.//wp:extent', ns)
            blip = drawing.find('.//a:blip', ns)
            a_ext = drawing.find('.//a:ext', ns)
            if extent is not None and blip is not None:
                r_id = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                if r_id in new_extents:
                    cx, cy = new_extents[r_id]
                    extent.attrib['cx'] = str(cx)
                    extent.attrib['cy'] = str(cy)
                    if a_ext is not None:
                        a_ext.attrib['cx'] = str(cx)
                        a_ext.attrib['cy'] = str(cy)

    intermediate_path = TMP_DIR / "doc_clean.docx"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    doc.save(str(intermediate_path))
    print(f"Saved intermediate docx to {intermediate_path}")

    # -------------------------------------------------------------------------
    # 6. Replace Image Media in Zip Archive (Leaves XML pristine)
    # -------------------------------------------------------------------------
    unzip_dir = TMP_DIR / "unpacked_clean"
    if unzip_dir.exists():
        shutil.rmtree(unzip_dir)
    with zipfile.ZipFile(intermediate_path, 'r') as zin:
        zin.extractall(unzip_dir)

    image_replacements = {
        "word/media/image1.png": "tmp/new_visuals/fig1_architecture.png",
        "word/media/image2.png": "tmp/new_visuals/fig2_layer_a.png",
        "word/media/image3.png": "tmp/new_visuals/fig3_e5_final.png",
        "word/media/image4.png": "tmp/new_visuals/fig4_benchmark_vs_unseen.png",
        "word/media/image5.png": "tmp/new_visuals/fig5_latency.png"
    }
    for media_name, new_file in image_replacements.items():
        dst_path = unzip_dir / media_name
        if dst_path.exists():
            shutil.copyfile(new_file, dst_path)

    with zipfile.ZipFile(OUT_DOCX, 'w', zipfile.ZIP_DEFLATED) as zout:
        for file_path in unzip_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(unzip_dir)
                zout.write(file_path, str(rel_path))

    print(f"Successfully generated: {OUT_DOCX}")

if __name__ == "__main__":
    main()
