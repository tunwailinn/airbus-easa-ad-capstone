# Verified PDF visual review

Reviewed: 2026-07-30  
Scope: all 20 frozen extension PDFs / all 66 pages

## Result

- Every PDF matched the frozen SHA-256 and expected page count before review.
- Every page was rendered from the verified binary and reviewed in a
  full-document contact sheet.
- Every cover shows the selected AD number and an explicit
  `Supersedure: None`.
- No missing, blank, clipped, or unreadable source page was found.
- No selected publication is a revision, correction, duplicate, or
  near-duplicate-candidate endpoint.
- No incoming or outgoing supersedure edge is present in the Step 1 manifest.

## Coverage confirmed visually

- Table-dependent or appendix cases include `2009-0171`, `2013-0011`,
  `2016-0175`, `2021-0221`, `2022-0058`, and `2025-0181`.
- `2021-0221` contains six ATA chapters and two compliance tables.
- `2022-0058` is a six-page, five-table windshield case.
- `2025-0181` contains an affected-serial-number appendix.
- `2011-0098` is a six-page multi-manufacturer applicability case.
- `2021-0286` is conditioned on Airbus Defence and Space MRTT STCs.

## Supersedure wording notes

- `2019-0188` discusses a possible future AD that could supersede the current
  AD, but identifies no actual successor publication and creates no present
  supersedure edge.
- `2024-0001` explicitly states that four earlier ADs are *not* superseded by
  it. This is negative evidence and creates no supersedure edge.

These two wording cases remain valid no-link examples. Their future annotation
must not fabricate supersedure relationships from conditional or explicitly
negative statements.
