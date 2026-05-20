TEXT_STRUCTURING_PROMPT = """
You are an expert in educational data structuring. Your task is to parse the following raw exam question text
into a structured format.
Separate the main statement from its options (if they exist).

Follow these BUSINESS RULES to determine the type:

CATEGORY 1: OBJECTIVE_SINGLE

Classic Multiple Choice: The question has options (a, b, c, d), and the user must select the single correct one.
Set type to OBJECTIVE_SINGLE.

CATEGORY 2: OBJECTIVE_MULTI

Multiple Choice (True/False / Multi-select): The question has options, but multiple can be correct or the user
must judge each as True/False. Set type to OBJECTIVE_MULTI.

CATEGORY 3: SUBJECTIVE

Single Essay: The question is purely a statement asking for an explanation. There are NO options. (Set options to
an empty list).

Multi-item Essay: The question has a main statement and sub-items (e.g., a) Explain X, b) Explain Y) where the
user must write a text response for each item. Parse these sub-items into the options list.

Do not solve the question and do not create the answer key in this step.
Set option.is_correct to null.
Set explanation to null.
Set expected_answer to null.

Ensure the box_ids and exam_order are preserved exactly as provided in the input.
""".strip()
