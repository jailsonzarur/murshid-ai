LAYOUT_EXTRACTION_PROMPT = """
Analyze this exam page and extract its layout information.

Return two lists:

1. question_markers — each numbered question that STARTS on this page.
   - number: the question number as an integer (e.g., 1, 2, 15)
   - y_normalized: vertical position [0.0–1.0] where 0.0 = top of page, 1.0 = bottom
   - Recognize patterns: "Questão 1", "Q1", "1.", "1)", "01.", "QUESTÃO 01", "1 -", "1 –" etc.
   - Only report each question number ONCE, at its first occurrence on this page.
   - If this page is a continuation (no numbered question starts at the top), return an empty list.

2. visual_elements — non-text visual content embedded in the exam questions.
   - type: one of "image", "table", "figure", "chart", "diagram"
   - bbox: bounding box as [x1, y1, x2, y2] with ALL values normalized [0.0–1.0]
     * (0.0, 0.0) = top-left corner of the page
     * (1.0, 1.0) = bottom-right corner of the page
   - Include: photographs, scientific diagrams, data tables, graphs, maps,
     chemical structures presented as images, anatomical figures.
   - EXCLUDE: page headers, footers, institution logos, decorative borders,
     question text blocks, answer option text, watermarks, page numbers.
   - Be generous with bbox — include the complete element plus a small margin.

COORDINATE FORMAT: ALL bbox values MUST be in the range [0.0, 1.0]. Never use percentages (0–100).
""".strip()
