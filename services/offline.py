"""Rule-based (no AI) evaluators.

They are used when the Gemini API key is missing, the quota is over or the network is down,
so the whole project can still be demonstrated offline. The result has exactly the same
shape as the AI result, only `source` is "offline".
"""

import re

STOPWORDS = set("""
a an the is are was were be been being of in on at to for from by with and or but not no
what why how when where which who whom do does did done can could should would will shall
you your yours i me my we our us it its this that these those as if then than so such
explain describe define tell about give example between difference
""".split())

FILLER_RE = re.compile(
    r"\b(um+|uh+|er+|hmm+|basically|actually|literally|you know|kind of|sort of|i mean)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Key concepts for the built-in question bank. Each inner list = one concept,
# written as alternative keywords (any one of them counts).
# ---------------------------------------------------------------------------
CONCEPTS = {
    "What is the difference between a list and a tuple in Python?": [
        ["mutable", "changeable", "modify"], ["immutable", "cannot be changed", "unchangeable"],
        ["square bracket", "[]"], ["parenthes", "()"], ["faster", "memory", "performance"],
    ],
    "What is Object-Oriented Programming (OOP)? Name its four pillars.": [
        ["encapsulation"], ["inheritance"], ["polymorphism"], ["abstraction"], ["object", "class"],
    ],
    "Explain the difference between SQL and NoSQL databases.": [
        ["table", "relational", "rows"], ["schema"], ["document", "key-value", "key value", "graph"],
        ["scal"], ["acid", "join", "mongodb", "mysql"],
    ],
    "What is the purpose of an operating system?": [
        ["resource", "manage"], ["process", "scheduling", "cpu"], ["memory"],
        ["file"], ["interface", "hardware", "user"],
    ],
    "Explain what Machine Learning is and give one real-world example.": [
        ["data"], ["learn", "train"], ["predict", "pattern", "model"],
        ["without being explicitly", "explicitly programmed", "automatically"],
        ["spam", "recommend", "face", "fraud", "self-driving", "example"],
    ],
    "What is the difference between a process and a thread?": [
        ["program in execution", "running program", "instance of a program"],
        ["lightweight", "smaller unit", "unit of a process", "within a process"],
        ["share", "shared memory", "same memory"], ["separate memory", "own memory", "isolated"],
        ["context switch", "overhead", "concurren", "parallel"],
    ],
    "What is normalization in DBMS and why is it used?": [
        ["redundan", "duplicate"], ["anomal", "insert", "update", "delete"],
        ["1nf", "2nf", "3nf", "normal form", "bcnf"], ["table"], ["integrity", "consisten"],
    ],
    "Explain the difference between an array and a linked list.": [
        ["contiguous", "continuous", "index"], ["node", "pointer", "next"], ["fixed size", "dynamic"],
        ["o(1)", "random access", "constant time"], ["insert", "delet"],
    ],
    "What is a REST API and how does it work?": [
        ["http"], ["get", "post", "put", "delete"], ["resource", "url", "endpoint"],
        ["json", "xml"], ["stateless", "client", "server"],
    ],
    "What is the difference between stack and queue?": [
        ["lifo", "last in first out", "last-in"], ["fifo", "first in first out", "first-in"],
        ["push", "pop"], ["enqueue", "dequeue"], ["undo", "recursion", "bfs", "scheduling", "example"],
    ],
    "Explain what a primary key and a foreign key are.": [
        ["unique"], ["null"], ["identif", "each row", "record"], ["reference", "link", "relationship"],
        ["another table", "other table", "parent", "referential"],
    ],
    "What is time complexity? Explain Big-O with an example.": [
        ["time taken", "input size", "how long", "grows", "execution time"], ["big-o", "big o", "upper bound", "worst case"],
        ["o(n)", "o(1)", "o(log n)", "o(n^2)", "o(n2)"], ["algorithm"], ["linear search", "binary search", "loop", "example"],
    ],
    "What is the difference between TCP and UDP?": [
        ["connection-oriented", "connection oriented", "handshake"], ["connectionless", "no connection"],
        ["reliable", "acknowledg"], ["fast", "faster", "low latency", "overhead"],
        ["video", "streaming", "gaming", "dns", "http", "file transfer", "example"],
    ],
    "What is recursion? Give a simple example.": [
        ["function calls itself", "calls itself", "itself"], ["base case", "termination", "stop condition"],
        ["factorial", "fibonacci", "example"], ["stack"], ["smaller", "sub-problem", "subproblem"],
    ],
    "Explain the difference between GET and POST requests.": [
        ["retrieve", "fetch", "read"], ["send", "submit", "create", "body"], ["url", "query", "visible"],
        ["secure", "sensitive", "password"], ["idempotent", "cach", "bookmark", "length limit"],
    ],
    "What is a deadlock and how can it be avoided?": [
        ["wait", "blocked", "stuck"], ["resource"], ["mutual exclusion", "hold and wait", "circular wait", "no preemption"],
        ["avoid", "prevent", "order", "timeout"], ["process", "thread"],
    ],
    "What is the difference between compiled and interpreted languages?": [
        ["compil"], ["interpret", "line by line", "line-by-line"], ["machine code", "binary", "executable"],
        ["faster", "slower", "speed", "performance"], ["c++", "java", "python", "javascript", "example"],
    ],
    "What are Git branches and why do we use them?": [
        ["parallel", "independent", "isolated", "separate"], ["feature", "bug", "experiment"],
        ["merge"], ["main", "master"], ["collaborat", "team", "conflict"],
    ],
}

RESULT_WORDS = ("result", "outcome", "achiev", "learned", "improved", "increased", "reduced",
                "successfully", "completed", "delivered", "%")
ACTION_WORDS = ("i decided", "i took", "i led", "i organized", "i organised", "i created",
                "i built", "i solved", "i talked", "i worked", "i planned", "i implemented")
EXAMPLE_RE = re.compile(r"\b(for example|e\.g\.|for instance|such as|consider|suppose|let's say)\b", re.I)


def tokens(text):
    return re.findall(r"[a-z0-9\+\#\.\(\)\^]+", text.lower())


def count_fillers(text):
    return len(FILLER_RE.findall(text))


def _concept_hits(answer_lc, concepts):
    hit, missed = [], []
    for alts in concepts:
        if any(alt in answer_lc for alt in alts):
            hit.append(alts[0])
        else:
            missed.append(alts[0])
    return hit, missed


def heuristic_evaluate(question, answer):
    """Return {score, strengths, improvements, sample_answer, source:'offline'}."""
    answer = answer.strip()
    answer_lc = answer.lower()
    words = re.findall(r"\w+", answer)
    n = len(words)
    sentences = [s for s in re.split(r"[.!?\n]+", answer) if len(s.split()) >= 3]
    has_example = bool(EXAMPLE_RE.search(answer))
    length_part = min(n / 60.0, 1.0)
    structure_part = 1.0 if len(sentences) >= 3 else (0.5 if len(sentences) == 2 else 0.0)

    strengths, improvements = [], []
    concepts = CONCEPTS.get(question)

    if concepts:
        hit, missed = _concept_hits(answer_lc, concepts)
        coverage = len(hit) / len(concepts)
        raw = 0.60 * coverage + 0.20 * length_part + 0.10 * (1 if has_example else 0) + 0.10 * structure_part
        if hit:
            strengths.append("Covers key ideas: " + ", ".join(hit[:3]) + ".")
        if missed:
            improvements.append("Also mention: " + ", ".join(missed[:3]) + ".")
        sample = "A strong answer covers: " + ", ".join(a[0] for a in concepts) + "."
    else:
        # Generic rubric (AI-generated or HR questions)
        q_keys = {t for t in tokens(question) if t not in STOPWORDS and len(t) > 2}
        a_tokens = set(tokens(answer))
        overlap = len(q_keys & a_tokens) / max(1, len(q_keys))
        first_person = len(re.findall(r"\bi\b", answer_lc)) >= 2
        result_part = 1.0 if any(w in answer_lc for w in RESULT_WORDS) else 0.0
        action_part = 1.0 if any(w in answer_lc for w in ACTION_WORDS) or first_person else 0.0
        raw = (0.25 * min(overlap * 1.5, 1.0) + 0.25 * length_part + 0.15 * structure_part
               + 0.15 * (1 if has_example else 0) + 0.10 * result_part + 0.10 * action_part)
        if overlap >= 0.4:
            strengths.append("Stays relevant to the question.")
        else:
            improvements.append("Use the key terms from the question so the answer stays on topic.")
        if result_part:
            strengths.append("Mentions a result or outcome.")
        else:
            improvements.append("End with the result / what you learned (STAR method).")
        sample = ("Structure your answer as: short direct answer, one concrete example "
                  "from your projects or college, and the result or learning.")

    if n >= 40:
        strengths.append("Good level of detail.")
    elif n < 25:
        improvements.append("Add more detail - aim for 40-80 words.")
    if has_example:
        strengths.append("Uses an example.")
    else:
        improvements.append("Add a short real-world example.")

    score = max(0, min(10, round(raw * 10)))
    return {
        "score": score,
        "strengths": strengths[:3] or ["You attempted the question."],
        "improvements": improvements[:3],
        "sample_answer": sample,
        "source": "offline",
    }


# ---------------------------------------------------------------------------
# Resume (ATS) heuristic
# ---------------------------------------------------------------------------
ROLE_KEYWORDS = {
    "python": ["python", "flask", "django", "sql", "git", "api", "oop", "pandas", "numpy", "testing"],
    "java": ["java", "spring", "oop", "sql", "git", "rest", "maven", "multithreading", "collections", "junit"],
    "web": ["html", "css", "javascript", "react", "node", "git", "api", "responsive", "bootstrap", "sql"],
    "frontend": ["html", "css", "javascript", "react", "responsive", "git", "typescript", "api", "ui", "testing"],
    "full stack": ["html", "css", "javascript", "react", "node", "sql", "api", "git", "docker", "mongodb"],
    "data": ["python", "sql", "excel", "pandas", "visualization", "power bi", "tableau", "statistics", "numpy", "analysis"],
    "machine learning": ["python", "machine learning", "tensorflow", "scikit-learn", "pandas", "numpy", "deep learning", "model", "nlp", "statistics"],
    "ai": ["python", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "model", "data", "llm", "api"],
    "android": ["java", "kotlin", "android", "xml", "firebase", "api", "git", "sqlite", "mvvm", "ui"],
    "devops": ["linux", "docker", "kubernetes", "ci/cd", "git", "aws", "jenkins", "bash", "monitoring", "terraform"],
    "default": ["data structures", "algorithms", "git", "sql", "oop", "api", "problem solving", "testing", "teamwork", "projects"],
}

SECTION_PATTERNS = {
    "Phone number": r"\b\d{10}\b|\+\d{2}[\s-]?\d|\b\d{5}[\s-]\d{5}\b",
    "Education": r"\b(education|b\.?tech|bachelor|degree|university|college|cgpa|gpa)\b",
    "Skills": r"\b(skills|technical skills|technologies|tools)\b",
    "Projects": r"\b(projects?|academic projects?)\b",
    "Experience / Internship": r"\b(experience|internship|intern|work history|employment)\b",
    "Certifications / Achievements": r"\b(certif\w*|achievements?|awards?|honou?rs?|courses?)\b",
}

ACTION_VERBS = ("developed", "built", "designed", "implemented", "created", "led", "improved",
                "optimized", "optimised", "automated", "analyzed", "analysed", "deployed",
                "integrated", "managed", "reduced", "increased", "achieved", "launched", "tested")


def role_keywords(role):
    role_lc = (role or "").lower()
    for key, words in ROLE_KEYWORDS.items():
        if key != "default" and key in role_lc:
            return words
    return ROLE_KEYWORDS["default"]


def heuristic_resume(text, role):
    text_lc = text.lower()
    words = re.findall(r"\w+", text)
    n = len(words)

    sections = {}
    for name, pattern in SECTION_PATTERNS.items():
        sections[name] = bool(re.search(pattern, text_lc))
    sections["LinkedIn / GitHub link"] = bool(re.search(r"linkedin\.com|github\.com", text_lc))
    sections["Email address"] = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))

    keywords = role_keywords(role)
    matched = [k for k in keywords if k in text_lc]
    missing = [k for k in keywords if k not in text_lc]

    verbs_used = sum(1 for v in ACTION_VERBS if v in text_lc)
    numbers = len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|\+|x|k\b)|\b\d{2,}\b", text_lc))

    if 250 <= n <= 700:
        length_score = 1.0
    elif 150 <= n < 250 or 700 < n <= 900:
        length_score = 0.6
    else:
        length_score = 0.25

    score = (
        35 * (len(matched) / len(keywords))
        + 25 * (sum(sections.values()) / len(sections))
        + 15 * min(verbs_used / 5, 1.0)
        + 10 * min(numbers / 4, 1.0)
        + 15 * length_score
    )
    score = max(0, min(100, round(score)))

    strengths, improvements = [], []
    if matched:
        strengths.append("Role keywords found: " + ", ".join(matched[:6]) + ".")
    if verbs_used >= 4:
        strengths.append("Good use of action verbs (developed, built, implemented...).")
    if numbers >= 3:
        strengths.append("Includes measurable numbers / results.")
    present = [k for k, v in sections.items() if v]
    if len(present) >= 6:
        strengths.append("Covers most standard resume sections.")

    for name, ok in sections.items():
        if not ok:
            improvements.append(f"Add a clear '{name}' section.")
    if verbs_used < 4:
        improvements.append("Start bullet points with action verbs (developed, built, designed...).")
    if numbers < 3:
        improvements.append("Add numbers: users, accuracy %, performance gain, team size.")
    if n < 150:
        improvements.append("Resume is too short - describe projects with 2-3 bullet points each.")
    elif n > 900:
        improvements.append("Resume is too long - a fresher resume should fit on one page.")
    if missing:
        improvements.append("Add relevant keywords if you really know them: " + ", ".join(missing[:5]) + ".")

    summary = (
        f"Your resume scores {score}/100 for the role '{role or 'Software Developer'}'. "
        f"{len(matched)} of {len(keywords)} important keywords were found."
    )
    return {
        "ats_score": score,
        "summary": summary,
        "strengths": strengths[:5] or ["Resume text was read successfully."],
        "improvements": improvements[:8],
        "matched_keywords": matched,
        "missing_keywords": missing,
        "sections": sections,
        "word_count": n,
        "source": "offline",
    }
