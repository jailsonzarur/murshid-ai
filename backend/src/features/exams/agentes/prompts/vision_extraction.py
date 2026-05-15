VISION_EXTRACTION_PROMPT = """
Extract the exam questions into raw text blocks. I have drawn red boxes with numeric IDs over non-text elements.
RULES:

TEXT EXTRACTION: Extract all printed text for a question (including its options, if any) into a single
raw_text string. IGNORE handwriting, circles, or scribbles.

IMAGE SPLITS: If an image visually splits a question's text, merge all the text into the same raw_text until
the next numbered question begins.

QUESTION BOUNDARIES: A question remains active until the next numbered question begins. A page break does NOT
end the current question.

CROSS-PAGE CONTINUATION: If a page starts with an image, table, graph, or diagram before any new numbered question
appears on that page, associate that red box with the previous question from the previous page.

BOX IDs: If the question refers to or contains red boxes, list their IDs in box_ids. Group them if they belong
to the same figure (e.g., [1, 2]).
""".strip()
