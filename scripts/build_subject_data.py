import json
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import md5
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_JSON = PROJECT_ROOT / "data" / "processed" / "questions.json"
OUT_JSON = PROJECT_ROOT / "web" / "data" / "maths_data.json"

# Exactly 14 chapters as requested for Maths, but we'll include all subjects now.
MATH_CHAPTERS = [
    "Real Numbers",
    "Polynomials",
    "Pair of Linear Equations",
    "Quadratic Equations",
    "Arithmetic Progressions",
    "Triangles",
    "Coordinate Geometry",
    "Trigonometry",
    "Circles",
    "Constructions",
    "Areas Related to Circles",
    "Surface Areas and Volumes",
    "Statistics",
    "Probability",
]

SCIENCE_CHAPTERS = [
    "Chemical Reactions and Equations",
    "Acids, Bases and Salts",
    "Metals and Non-metals",
    "Carbon and its Compounds",
    "Life Processes",
    "Control and Coordination",
    "How do Organisms Reproduce?",
    "Heredity and Evolution",
    "Light – Reflection and Refraction",
    "Human Eye and Colorful World",
    "Electricity",
    "Magnetic Effects of Electric Current",
    "Our Environment",
]

SOCIAL_CHAPTERS = [
    "Rise of Nationalism in Europe",
    "Nationalism in India",
    "The Making of a Global World",
    "The Age of Industrialisation",
    "Print Culture and the Modern World",
    "Resources and Development",
    "Forest and Wildlife Resources",
    "Water Resources",
    "Agriculture",
    "Minerals and Energy Resources",
    "Manufacturing Industries",
    "Lifelines of National Economy",
    "Power Sharing",
    "Federalism",
    "Gender, Religion and Caste",
    "Political Parties",
    "Outcomes of Democracy",
    "Development",
    "Sectors of the Indian Economy",
    "Money and Credit",
    "Globalization and the Indian Economy",
    "Consumer Rights",
]

ENGLISH_CHAPTERS = [
    "Reading Skills",
    "Writing Skills",
    "Grammar",
    "Literature - First Flight",
    "Literature - Footprints Without Feet",
]

CHAPTERS_BY_SUBJECT = {
    "Mathematics": MATH_CHAPTERS,
    "Science": SCIENCE_CHAPTERS,
    "Social Science": SOCIAL_CHAPTERS,
    "English": ENGLISH_CHAPTERS,
}

# Mapping subject directory name to display name
SUBJECT_DISPLAY_NAME = {
    "maths": "Mathematics",
    "science": "Science",
    "social": "Social Science",
    "social_science": "Social Science",
    "english": "English",
}

MATH_CHAPTER_RULES = [
    ("Real Numbers", ["hcf", "lcm", "euclid", "fundamental theorem of arithmetic", "irrational", "surds"]),
    ("Polynomials", ["polynomial", "zeroes", "zeros", "quadratic polynomial"]),
    (
        "Pair of Linear Equations",
        [
            "pair of linear equations",
            "linear equation",
            "elimination",
            "substitution",
            "cross multiplication",
        ],
    ),
    ("Quadratic Equations", ["quadratic equation", "discriminant", "roots of", "factorisation", "factorization"]),
    # Note: normalize_text() removes punctuation, so "A.P." often becomes "a p".
    ("Arithmetic Progressions", ["arithmetic progression", "common difference", "a p", "ap"]),
    ("Coordinate Geometry", ["coordinates", "x axis", "y axis", "distance between", "distance formula", "section formula", "midpoint"]),
    (
        "Trigonometry",
        [
            "sin",
            "cos",
            "trigonometry",
            "angle of elevation",
            "angle of depression",
            "trigonometrical",
        ],
    ),
    ("Circles", ["circle", "tangent", "chord", "radius", "diameter", "secant"]),
    # Put constructions before triangles, because many questions mention "triangle" while being a construction task.
    ("Constructions", ["construct", "construction", "bisect", "locus"]),
    ("Triangles", ["similar triangles", "pythagoras", "bpt", "thales", "triangle"]),
    # Avoid the bare word "segment" because it matches "line segment" from coordinate geometry.
    ("Areas Related to Circles", ["sector", "segment of a circle", "area of circle", "circumference", "arc"]),
    (
        "Surface Areas and Volumes",
        [
            "cylinder",
            "cone",
            "sphere",
            "hemisphere",
            "frustum",
            "volume",
            "surface area",
        ],
    ),
    ("Statistics", ["mean", "median", "mode", "frequency", "ogive", "histogram"]),
    ("Probability", ["probability", "coin", "dice", "card", "at random"]),
]

CHAPTER_OSWAAL = {
    "Real Numbers": {
        "errors": [
            "Forgetting to show Euclid's division steps clearly.",
            "Mixing up HCF and LCM in word problems.",
            "Not stating the final HCF/LCM explicitly.",
        ],
        "secrets": [
            "Write the algorithm steps in a vertical chain to avoid mistakes.",
            "Mention the theorem name before applying it.",
            "End with a clean concluding statement: 'Hence, ...'.",
        ],
        "mind_map_note": "Add a mind map: Euclid Algorithm, prime factorization, HCF/LCM links.",
    },
    "Polynomials": {
        "errors": [
            "Not using the correct relation between zeroes and coefficients.",
            "Skipping factorisation steps (loses presentation marks).",
            "Sign errors while expanding or multiplying factors.",
        ],
        "secrets": [
            "Write the relation formula first, then substitute values.",
            "Box the zeroes clearly at the end.",
            "Show one verification step if time permits.",
        ],
        "mind_map_note": "Add a mind map: types, zeroes, factor theorem, remainder theorem.",
    },
    "Pair of Linear Equations": {
        "errors": [
            "Mixing up signs while eliminating variables.",
            "Not aligning equations properly before subtraction/addition.",
            "Forgetting to verify the solution by substitution.",
        ],
        "secrets": [
            "Write (1) and (2), then show elimination step clearly.",
            "Box the final ordered pair (x, y).",
            "Add a 1-line verification if time permits.",
        ],
        "mind_map_note": "Add a mind map: graphical meaning, elimination, substitution, cross-multiplication.",
    },
    "Quadratic Equations": {
        "errors": [
            "Wrong factorisation or sign mistake in splitting the middle term.",
            "Using the quadratic formula with incorrect b or discriminant.",
            "Not writing both roots clearly.",
        ],
        "secrets": [
            "Prefer factorisation when easy; otherwise use formula neatly.",
            "Write D = b^2 - 4ac first, then substitute.",
            "Box both roots separately.",
        ],
        "mind_map_note": "Add a mind map: factorisation, quadratic formula, nature of roots.",
    },
    "Arithmetic Progressions": {
        "errors": [
            "Using wrong n (term number) or wrong formula for nth term/sum.",
            "Mixing up a (first term) and d (common difference).",
            "Arithmetic mistakes in sum calculations.",
        ],
        "secrets": [
            "Write a and d explicitly from the series before solving.",
            "Use T_n = a + (n-1)d and S_n = n/2[2a+(n-1)d].",
            "Keep steps aligned to avoid arithmetic slips.",
        ],
        "mind_map_note": "Add a mind map: nth term, sum, AP word-problem patterns.",
    },
    "Triangles": {
        "errors": [
            "Applying similarity criteria without mentioning the reason.",
            "Mixing up corresponding sides/angles.",
            "Forgetting to conclude the result at the end.",
        ],
        "secrets": [
            "Write the similarity statement first (e.g., ΔABC ~ ΔPQR).",
            "List corresponding sides in the same order.",
            "End with a clear 'Hence proved'.",
        ],
        "mind_map_note": "Add a mind map: similarity criteria, BPT, Pythagoras and applications.",
    },
    "Coordinate Geometry": {
        "errors": [
            "Swapping x and y while applying distance/section formula.",
            "Sign mistakes in subtraction under the square root.",
            "Not simplifying the final value.",
        ],
        "secrets": [
            "Write the formula first, then substitute points.",
            "Keep brackets while subtracting coordinates.",
            "Box the final answer with units if any.",
        ],
        "mind_map_note": "Add a mind map: distance, section, midpoint, common patterns.",
    },
    "Trigonometry": {
        "errors": [
            "Using wrong trigonometric ratio for an angle.",
            "Forgetting to simplify expressions properly.",
            "Skipping diagram/labels for heights and distances.",
        ],
        "secrets": [
            "Draw the triangle/diagram and label sides relative to the angle.",
            "Use standard values table where needed.",
            "Simplify step-by-step; avoid skipping algebra.",
        ],
        "mind_map_note": "Add a mind map: ratios, identities, heights & distances.",
    },
    "Circles": {
        "errors": [
            "Not using the tangent-radius perpendicular property correctly.",
            "Skipping theorem names in proofs.",
            "Wrong angle assumptions for chord/tangent results.",
        ],
        "secrets": [
            "Write the theorem line explicitly before applying.",
            "Draw a clean figure and mark equal angles/lengths.",
            "Keep proofs concise: statement, reason, conclusion.",
        ],
        "mind_map_note": "Add a mind map: tangents, chord properties, angle theorems.",
    },
    "Constructions": {
        "errors": [
            "Not writing steps in order or missing key measurements.",
            "Inaccurate scale/arc intersections.",
            "Not marking the required points/labels clearly.",
        ],
        "secrets": [
            "Write steps as numbered lines and keep the diagram neat.",
            "Mention scale/ratio used in construction.",
            "Highlight the final constructed line/point.",
        ],
        "mind_map_note": "Add a mind map: division, similarity-based constructions, tangents.",
    },
    "Areas Related to Circles": {
        "errors": [
            "Mixing up radius and diameter.",
            "Not converting units before computing area/perimeter.",
            "Forgetting to subtract segments correctly.",
        ],
        "secrets": [
            "Write the formula first and substitute neatly.",
            "Keep π value consistent.",
            "Box the final answer with square units.",
        ],
        "mind_map_note": "Add a mind map: sector, segment, ring area patterns.",
    },
    "Surface Areas and Volumes": {
        "errors": [
            "Using CSA vs TSA incorrectly.",
            "Unit conversion mistakes (cm to m, etc.).",
            "Missing units in final answers (cm^2, cm^3).",
        ],
        "secrets": [
            "Draw the solid and write the formula first.",
            "List given values (r, h, l) before substituting.",
            "Box the final answer with correct units.",
        ],
        "mind_map_note": "Add a mind map: TSA/CSA/Volume for cone, cylinder, sphere, frustum.",
    },
    "Statistics": {
        "errors": [
            "Using wrong method/formula for mean or median.",
            "Incorrect cumulative frequency while drawing ogive.",
            "Not writing the final value clearly.",
        ],
        "secrets": [
            "Make a clean table: x, f, fx (or u), cumulative frequency.",
            "Label axes and scales properly for graphs.",
            "Box mean/median/mode at the end.",
        ],
        "mind_map_note": "Add a mind map: mean, median, mode, ogive steps.",
    },
    "Probability": {
        "errors": [
            "Wrong sample space or missing outcomes.",
            "Not reducing the probability to simplest form.",
            "Confusing mutually exclusive vs independent events.",
        ],
        "secrets": [
            "Write sample space S explicitly (or count outcomes).",
            "Probability = favourable / total (then simplify).",
            "State the final probability clearly.",
        ],
        "mind_map_note": "Add a mind map: coins/dice/cards patterns, complementary probability.",
    },
    # Science
    "Chemical Reactions and Equations": {
        "errors": ["Incorrect balanced coefficients.", "Wrong state symbols.", "Mixing up oxidation and reduction."],
        "secrets": ["Count atoms on both sides separately.", "Label states: (s), (l), (g), (aq)."],
        "mind_map_note": "Mind Map: Combination, Decomposition, Displacement, Double Displacement, Redox."
    },
    "Life Processes": {
        "errors": ["Incomplete diagrams.", "Wrong labeling of parts.", "Missing key enzymes in digestion."],
        "secrets": ["Draw large, neat diagrams.", "Underline technical terms like Peristalsis, Transpiration."],
        "mind_map_note": "Mind Map: Nutrition, Respiration, Transportation, Excretion."
    },
    "Light – Reflection and Refraction": {
        "errors": ["Sign convention mistakes (u, v, f).", "Arrow missing on ray diagrams.", "Incorrect lens/mirror formula."],
        "secrets": ["Always draw the principal axis first.", "Object is always on the left (-ve u)."],
        "mind_map_note": "Mind Map: Mirror formula, Lens formula, Ray diagrams, Refractive index."
    },
    # Social Science
    "Nationalism in India": {
        "errors": ["Incorrect dates/years.", "Mixing up Non-Cooperation and Civil Disobedience.", "Vague location descriptions."],
        "secrets": ["Use a timeline to remember events.", "Highlight leaders like Gandhiji, Nehru, Bose."],
        "mind_map_note": "Mind Map: Rowlatt Act, Jallianwala Bagh, Dandi March, Quit India."
    },
    "Political Parties": {
        "errors": ["Confusing national vs regional parties.", "Incomplete list of party functions.", "Vague challenges to political parties."],
        "secrets": ["Learn at least 7 national parties and symbols.", "Use bullet points for functions."],
        "mind_map_note": "Mind Map: Functions, Types, Challenges, Reforms."
    },
    # English
    "Grammar": {
        "errors": ["Subject-verb agreement issues.", "Tense inconsistency.", "Incorrect reported speech conversions."],
        "secrets": ["Identify the tense of the reporting verb first.", "Read the full sentence before choosing a determiner."],
        "mind_map_note": "Mind Map: Tenses, Modals, Determiners, Reported Speech."
    },
    "Literature - First Flight": {
        "errors": ["Vague character sketches.", "Misinterpreting the central theme.", "Incorrect poem-poet pairings."],
        "secrets": ["Quote 1-2 lines from the poem if possible.", "Focus on the 'message' of the story."],
        "mind_map_note": "Mind Map: Lencho, Mandela, Anne Frank, Poets & Themes."
    },
}

DEFAULT_CHAPTER_META = {
    "errors": [
        "Arithmetic slips (signs, fractions, simplification).",
        "Not writing the correct formula/theorem before applying.",
        "Messy layout: unclear steps or missing final answer box.",
    ],
    "secrets": [
        "Underline the given and what is asked.",
        "Keep steps short and aligned; avoid skipping logic.",
        "Write units/conditions and box the final answer.",
    ],
    "mind_map_note": "Add a chapter mind map image/link here.",
}


def normalize_text(text: str) -> str:
    cleaned = (text or "").lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


_STOPWORDS = {
    "the",
    "and",
    "or",
    "to",
    "of",
    "a",
    "an",
    "is",
    "are",
    "in",
    "that",
    "then",
    "if",
    "find",
    "show",
    "prove",
    "given",
    "using",
}


def token_set(norm: str) -> set[str]:
    toks = []
    for t in (norm or "").split():
        if t in _STOPWORDS:
            continue
        if len(t) <= 2:
            continue
        toks.append(t)
    return set(toks)


def clean_question_text(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^[\s\.:;,\-]+", "", text)
    return text


_PUA_GREEK_MAP = {
    "": "α",
    "": "β",
    "": "γ",
    "": "θ",
    "": "π",
    "": "∴",
    "": "=",
    "": "(",
    "": ")",
    "": "=>",
    "": "+",
    "": "-",
    "": "Since",
    "": "±",
    "": "×",
    "": " not equal ",
    "": "∠",
    "": "=>",
    "": "∴",
    "": "∵",
    "": "√",
    "": "α",
    "": "β",
    "": "γ",
    "": "δ",
    "": "λ",
    "": "μ",
    "": "σ",
    "": "ω",
    "": "Δ",
    "": "π",
    "": "θ",
    "": "φ",
    "": "φ",
    "": "ρ",
    "": "τ",
    "": "ε",
    "": "η",
    "": "ψ",
    "": "ξ",
    "": "ζ",
    "": "ι",
    "": "κ",
    "": "ν",
    "": "ο",
    "": "υ",
    "": "χ",
    "": "α",
    "": "β",
    "": "χ",
    "": "δ",
    "": "ε",
    "": "φ",
    "": "γ",
    "": "η",
    "": "ι",
    "": "φ",
    "": "κ",
    "": "λ",
    "": "μ",
    "": "ν",
    "": "ο",
    "": "π",
    "": "θ",
    "": "ρ",
    "": "σ",
    "": "τ",
    "": "υ",
    "": "ω",
    "": "ξ",
    "": "ψ",
    "": "ζ",
    "": "∴",
    "": "∵",
    "": "=",
    "": "+",
    "": "-",
    "": "×",
    "": "÷",
    "": "±",
    "": "√",
    "": "∞",
    "": " not equal ",
    "": "∠",
    "": "V",
    "": "Ω",
    "": "μ",
    "": "π",
    "": "φ",
    "": "θ",
    "": "γ",
    "": "α",
    "": "β",
    "": "=>",
    "": "=>",
    "": "<=",
    "": "∧",
    "": "∨",
    "": "⊂",
    "": "⊆",
    "": "∈",
    "": "∉",
    "": "∪",
    "": "∩",
    "": "∅",
    "": "∇",
    "": "∂",
    "": "∫",
    "": "∑",
    "": "∏",
    "": "√",
    "": "≡",
    "": "≈",
    "": "∝",
    "∝": "∝",
    "": "\"",
    "": "÷",
    "": " not equal ",
    "": "≤",
    "": "¤",
    "": "∞",
    "": "¦",
    "§": "§",
    "¨": "¨",
    "©": "©",
    "ª": "ª",
    "«": "«",
    "¬": "¬",
    "­": "­",
    "®": "®",
    "¯": "¯",
    "°": "°",
    "±": "±",
    "²": "²",
    "³": "³",
    "´": "´",
    "µ": "µ",
    "¶": "¶",
    "·": "·",
    "¸": "¸",
    "¹": "¹",
    "º": "º",
    "»": "»",
    "¼": "¼",
    "½": "½",
    "¾": "¾",
    "¿": "¿",
    "": "<=>",
    "": "<=>",
    "": "↑",
    "": "↓",
    "": "→",
    "": "←",
    "": "↔",
    "": "↘",
    "": "↙",
    "": "↖",
    "": "↗",
    "": " not equal ",
    "\uf0b9": " not equal ",
    "\uf0b4": " ",
}


def _split_question_solution_heuristic(text: str) -> tuple[str, str]:
    """
    Some solved papers embed worked steps right after the question with no delimiter.
    If we detect common solution-language, split and move it into the solution area.
    """
    t = text or ""
    # First split on explicit answer label if present.
    m_ans = re.search(r"(?i)\bans\.?\b", t)
    if m_ans:
        left = t[: m_ans.start()].strip()
        right = t[m_ans.start() :].strip()
        if len(left) >= 20 and len(right) >= 20:
            return left, right

    markers = [
        r"\bPrime factor\b",
        r"\bPrime factorisation\b",
        r"\bLeast exponent\b",
        r"\bGreatest exponent\b",
        r"\bTo find the LCM\b",
        r"\bTo find the HCF\b",
        r"\bWe list all prime factors\b",
        r"\bSolution\b",
        r"\bSol\.\b",
        # Euclid's algorithm / division algorithm worked steps often get appended to the question text.
        r"\bSince\s+\d+\s*>\s*\d+\b",
        r"\bSince remainder\b",
        r"\bThe remainder has now become zero\b",
        r"\bUsing division algorithm\b",
        r"\bLet\s+[a-z]\s+be\b",
    ]
    m = re.search("|".join(markers), t, flags=re.IGNORECASE)
    if not m:
        return t, ""

    left = t[: m.start()].strip()
    right = t[m.start() :].strip()
    if len(left) < 40 or len(right) < 30:
        return t, ""
    return left, right


def format_embedded_solution(text: str) -> str:
    """
    The question cleaner collapses whitespace, so embedded solutions become hard to read.
    Re-introduce minimal line breaks and normalize common Euclid-division equations.
    """
    s = (text or "").strip()
    if not s:
        return ""

    # Put OR on its own line.
    s = re.sub(r"\s+\bOR\b\s+", "\nOR\n", s, flags=re.IGNORECASE)

    # Break before common narrative steps.
    s = re.sub(r"\s+(Since\b)", r"\n\1", s)
    s = re.sub(r"\s+(Let\b)", r"\n\1", s)
    s = re.sub(r"\s+(Using\b)", r"\n\1", s)
    s = re.sub(r"\s+(Therefore\b|\u2234\b|Hence\b)", r"\n\1", s)
    s = re.sub(r"\s+(The remainder\b)", r"\n\1", s, flags=re.IGNORECASE)

    # Normalize Euclid division pattern:
    # "7344 1260 5 1044 = × +" -> "7344 = 1260×5 + 1044"
    s = re.sub(
        r"\b(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*=\s*×\s*\+",
        r"\1 = \2×\3 + \4",
        s,
    )

    # Remove corrupted trailing tokens like "= ×+" that sometimes survive mapping.
    s = re.sub(r"\s*=\s*×\s*\+", "", s)

    # Fix any remaining 4-number Euclid steps even when they are embedded mid-line.
    def _fix_four_nums_any(m: re.Match) -> str:
        a, b, c, d = m.group(1), m.group(2), m.group(3), m.group(4)
        try:
            if int(a) < 100 or int(b) < 10:
                return m.group(0)
        except ValueError:
            return m.group(0)
        return f"{a} = {b}×{c} + {d}"

    s = re.sub(r"\b(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\b", _fix_four_nums_any, s)

    # Put each Euclid equation on its own line.
    s = re.sub(r"(\d+\s*=\s*\d+×\d+\s*\+\s*\d+)\s+(?=\d+\s*=)", r"\1\n", s)

    # Some lines lose the '=' entirely: "216 180 1 36" -> "216 = 180×1 + 36"
    def _fix_four_nums(line: str) -> str:
        m = re.fullmatch(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line.strip())
        if not m:
            return line
        a, b, c, d = m.group(1), m.group(2), m.group(3), m.group(4)
        return f"{a} = {b}×{c} + {d}"

    # Fix "a = 4q + r" line that often extracts as "4 a q r = +"
    s = re.sub(r"\b4\s+a\s+q\s+r\s*=\s*\+", "a = 4q + r", s, flags=re.IGNORECASE)
    # Ensure line break after "b = 4" when "a = 4q + r" follows immediately.
    s = re.sub(r"\bb\s*=\s*4\s+a\s*=\s*", "b = 4\na = ", s, flags=re.IGNORECASE)
    # Fix missing space/newline before "Since" when glued: "rSince" -> "r\nSince"
    s = re.sub(r"([a-zA-Z])Since\b", r"\1\nSince", s)

    # Strip corrupted trailing tokens like "= ×+".
    s = re.sub(r"\s*=\s*×\s*\+\s*$", "", s)

    # Cleanup any leftover multi-space, preserve newlines.
    lines = []
    for ln in s.splitlines():
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        ln = _fix_four_nums(ln)
        lines.append(ln)
    s = "\n".join(lines).strip()
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def clean_science_formulas(t: str) -> str:
    """Specialized builder for Science formulas and equations."""
    if not t:
        return ""

    # Fix common PUA/corrupted characters for reaction arrows
    t = re.sub(r"[\uf0be\uf0ae]+", " \\\\rightarrow ", t)

    # Chemical formulas: CO 2 -> CO2, H 2 O -> H2O
    # Handle common cases like H2SO4, KMnO4
    # We want to catch CapitalLetter (optional lower) followed by optional space and digits
    # Avoid matching temperatures like 443K
    t = re.sub(r"\b([A-Z][a-z]?)\s*(\d+)\b(?![A-Zg-z])", r"\1$_{\2}$", t)

    # Ions: Na + -> Na$^+$, Cl - -> Cl$^-$, Ca 2+ -> Ca$^{2+}$
    t = re.sub(r"\b([A-Z][a-z]?)\s*(\d?)\s*([+\-])\b", r"\1$^{\2\3}$", t)

    # Physical states: (s), (l), (g), (aq)
    t = re.sub(r"\b\(([slg]|aq)\)\b", r"$(\1)$", t)
    # Sometimes they are extracted without parentheses but followed by a chemical
    t = re.sub(r"\b\s+([slg])\s+(?=[A-Z])", r" $(\1)$ ", t)

    # Multiple atoms/molecules at start of formula: 2 H2 -> 2H$_2$
    # Also 2C H3COOH -> 2CH$_3$COOH
    t = re.sub(r"\b(\d+)\s*([A-Z][a-z]?)\s*(\d*)\b",
               lambda m: f"{m.group(1)}{m.group(2)}$_{{{m.group(3)}}}$" if m.group(3) else f"{m.group(1)}{m.group(2)}", t)

    # Reaction arrows
    t = t.replace("-->", " \\\\rightarrow ")
    t = t.replace("->", " \\\\rightarrow ")
    t = t.replace("→", " \\\\rightarrow ")
    t = t.replace("==>", " \\\\Rightarrow ")

    # Electricity formulas: V = IR, P = VI, R = V/I
    if any(word in t.lower() for word in ["circuit", "resistance", "voltage", "current", "ohm"]):
        t = re.sub(r"\bV\s*=\s*I\s*R\b", r"$V = IR$", t)
        t = re.sub(r"\bP\s*=\s*V\s*I\b", r"$P = VI$", t)
        t = re.sub(r"\bR\s*=\s*ρ\s*l/A\b", r"$R = \rho \frac{l}{A}$", t)

    # Lens/Mirror formula: 1/v - 1/u = 1/f
    if any(word in t.lower() for word in ["lens", "mirror", "focal", "image", "object"]):
        t = re.sub(r"1/v\s*([+\-])\s*1/u\s*=\s*1/f", r"$\frac{1}{v} \1 \frac{1}{u} = \frac{1}{f}$", t)
        t = re.sub(r"\bm\s*=\s*h'/h\b", r"$m = \frac{h'}{h}$", t)
        t = re.sub(r"\bm\s*=\s*v/u\b", r"$m = \frac{v}{u}$", t)

    # Clean up any empty subscripts
    t = t.replace("$_{}$", "")

    return t


def clean_display_question(text: str, subject: str = "Mathematics") -> str:
    # Make PDF-extracted strings readable in the UI.
    t = text or ""
    had_web_noise = bool(re.search(r"(?i)www\\.|\\.com\\b|vedantu", t))

    # Replace common private-use glyphs (from some PDF fonts).
    for src, dst in _PUA_GREEK_MAP.items():
        t = t.replace(src, dst)

    # Normalize dashes/bullets.
    t = t.replace("\uf0b4", " ")  # private-use bullet seen in some extracts
    t = t.replace("−", "-")

    # Remove explicit marks labels.
    t = re.sub(r"(?i)\b[1-5]\s*marks?\b", "", t)
    # Remove marks that appear right after a colon: "... distribution: 2 Class 10-20 ..."
    t = re.sub(r"([:])\s*([1-5])\s+(?=[A-Za-z(])", r"\1 ", t)

    # Drop embedded answer keys from the question block (handles \"Ans:\", \"A n s:\", etc.).
    t = re.sub(r"(?is)\ba\s*n\s*s\s*:\s*.*$", "", t).strip()
    t = re.sub(r"(?is)\banswer\s*:\s*.*$", "", t).strip()
    t = re.sub(r"(?is)\bsection\s*[- ]?\s*[a-d]\b.*$", "", t).strip()

    # Remove common paper headers that sometimes get captured as "questions".
    t = re.sub(r"(?is)\buse of calculators is not permitted\b.*$", "", t).strip()
    t = re.sub(r"(?is)\bgeneral instructions\b.*$", "", t).strip()

    # Collapse whitespace (including PDF line separators).
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace("\u200b", "")  # zero-width space

    # FIX: Ensure LaTeX delimiters are properly escaped for JSON and JS.
    # The UI uses:
    # { left: '$$', right: '$$', display: true },
    # { left: '\\\\(', right: '\\\\)', display: false },
    # { left: '\\\\[', right: '\\\\]', display: true },
    # { left: '$', right: '$', display: false },
    
    # Often, PDF extraction loses the $ delimiters or uses weird characters.
    # We should encourage $...$ for inline math.
    
    # Fix common math symbols that should be in LaTeX
    t = t.replace("≠", " not equal ")
    t = t.replace("√", r"$\sqrt{}$") # Placeholder
    t = t.replace("π", r"$\pi$")
    t = t.replace("α", r"$\alpha$")
    t = t.replace("β", r"$\beta$")
    t = t.replace("γ", r"$\gamma$")
    t = t.replace("θ", r"$\theta$")
    t = t.replace("±", r"$\pm$")
    t = t.replace("×", r"$\times$")
    t = t.replace("÷", r"$\div$")
    t = t.replace("°", r"$^\circ$")
    t = t.replace("≤", r"$\le$")
    t = t.replace("≥", r"$\ge$")
    
    # Fix corrupted linear equation symbols: "xa and y = b" -> "x = a and y = b"
    t = re.sub(r"\bxa\b", "x = a", t)
    t = re.sub(r"\byb\b", "y = b", t)
    if "intersecting" in t.lower():
        t = re.sub(r"x\s*a\b", "x = a", t)
        t = re.sub(r"y\s*b\b", "y = b", t)
        t = t.replace("(a, b)", " (a, b) ")
        t = t.replace("a not equal b", " a not equal b ")
    
    # Fix common patterns like x^2, x^3
    t = re.sub(r"\b([a-z])([23])\b", r"$\1^\2$", t)

    # Fix prime-factorization groups that often get extracted like:
    # "( ) 32 3 5 ××" meaning "(2^3 × 3 × 5)" and "( ) 4 2 5 7 ××" meaning "(2^4 × 5 × 7)".
    def _format_factor_group(seq: str) -> str:
        raw = (seq or "").strip()
        raw = raw.replace("×", " ")
        toks = [x for x in raw.split() if x]
        out: list[str] = []
        i = 0
        while i < len(toks):
            tok = toks[i]
            # Compact base+exponent token: could be extracted as "23" (2^3) or sometimes reversed.
            # Prefer the interpretation that doesn't immediately duplicate the next prime factor.
            if re.fullmatch(r"[2-9]{2}", tok):
                a, b = tok[0], tok[1]
                next_tok = toks[i + 1] if i + 1 < len(toks) else ""
                candidates: list[tuple[str, str]] = []
                # Keep exponent range tight; otherwise pairs like "57" (meaning 5 and 7) get misread as 7^5.
                if a in "2357" and b in "2345":
                    candidates.append((a, b))
                if b in "2357" and a in "2345":
                    candidates.append((b, a))
                if candidates:
                    base, exp = candidates[0]
                    if len(candidates) == 2:
                        # If next token equals the candidate base, pick the other candidate.
                        if next_tok == candidates[0][0] and next_tok != candidates[1][0]:
                            base, exp = candidates[1]
                    out.append(f"{base}^{{{exp}}}")
                    i += 1
                    continue
                # If it looks like concatenated primes (e.g., "57"), split it.
                if a in "2357" and b in "2357":
                    out.append(a)
                    out.append(b)
                    i += 1
                    continue
            # Swapped exponent/base tokens: "4 2" => 2^4
            # Restrict to the most common case we actually see in the PDFs: exponent then base=2 at start of group.
            if i == 0 and i + 1 < len(toks) and re.fullmatch(r"[2345]", tok) and toks[i + 1] == "2":
                exp = tok
                out.append(f"2^{{{exp}}}")
                i += 2
                continue
            # Plain prime factor.
            if re.fullmatch(r"[2357]", tok):
                out.append(tok)
                i += 1
                continue
            out.append(tok)
            i += 1

        if not out:
            return ""
        expr = r" \times ".join(out)
        return f"$({expr})$"

    t = re.sub(
        r"\(\s*\)\s*([0-9\s×]+?)(?=\s+(?:and|or|is|are)\b|,|$)",
        lambda m: _format_factor_group(m.group(1)),
        t,
        flags=re.IGNORECASE,
    )

    # Light math readability fixes (low risk).
    t = re.sub(r"\bx\s+x\b", "x^2", t, flags=re.IGNORECASE)
    # Common extraction: "x2" or "px2" instead of "x^2" / "px^2".
    # Keep conservative: only rewrite when it looks like a math token (letter(s) + x2).
    t = re.sub(r"\b([a-zA-Z]+)x2\b", r"\1x^2", t)
    t = re.sub(r"\bx2\b", "x^2", t)
    t = re.sub(r"\b(\d+)\s+(\d+)\s*-\s*(?=\(|$)", r"-\1/\2 ", t)

    # Clean up a very common "empty parentheses" placeholder from PDF fonts.
    # Example: "form( ) ( ) 4q 1 ..." should not show "( )".
    t = re.sub(r"\(\s*\)", "", t)

    # Normalize "4q+1 / 4q+3" formatting for division-algorithm theorem statements.
    t = re.sub(r"\b4q\s*\+\s*1\b", "4q + 1", t)
    t = re.sub(r"\b4q\s*\+\s*3\b", "4q + 3", t)
    t = re.sub(r"\b4q\s+1\b", "4q + 1", t)
    t = re.sub(r"\b4q\s+3\b", "4q + 3", t)
    t = re.sub(r"\b4q\s*\+\s*3\s*\+\s*,", "4q + 3,", t)
    t = re.sub(r"\b4q\s*\+\s*3\s*\+\b", "4q + 3", t)

    # Normalize a common HCF/LCM fill-in-the-blank formatting from PDFs.
    # Example: "HCF(2520,6600) 40 = and LCM(2520,6600) 252 k = ×"
    t = re.sub(r"(?i)\bHCF\(([^)]+)\)\s*(\d+)\s*=", r"HCF(\1)=\2", t)
    t = re.sub(r"(?i)\bLCM\(([^)]+)\)\s*(\d+)\s*([a-zA-Z])\s*=\s*[×x]", r"LCM(\1)=\2×\3", t)
    # Render multiplication in KaTeX when it looks like "252×k".
    t = re.sub(r"(?<!\$)\b(\d+)\s*×\s*([a-zA-Z])\b", r"$\1\\\\times \2$", t)

    # Remove common website/footer noise.
    t = re.sub(r"(?i)\bwww\.[a-z0-9\.-]+\b", "", t)
    t = re.sub(r"(?i)\b[a-z0-9\.-]+\.com\b", "", t)
    if had_web_noise:
        t = re.sub(r"\s+\d+\s*$", "", t).strip()

    # Convert common surd patterns that often lose the radical in PDF extraction.
    # Only do this in "irrational" style questions to reduce false positives.
    if "irrational" in t.lower() or "root" in t.lower():
        # Very common PDF-loss pattern: "Given that 2 is irrational" really means "Given that √2 is irrational".
        # Trigger for small integers only, to reduce the chance of corrupting normal statements.
        t = re.sub(
            r"(?i)\bgiven that\s+([2-9]|1[0-3])\s+is\s+an?\s+irrational\b",
            r"Given that $\\\\sqrt{\1}$ is irrational",
            t,
        )
        # NEW: Catch "given that √2 is irrational" which might already be correct but without $
        t = re.sub(
            r"(?i)\bgiven that\s*[√\\]\s*(\d+)\s+is\s+an?\s+irrational\b",
            r"Given that $\\\\sqrt{\1}$ is irrational",
            t,
        )
        # Handle "given that 2 is irrational" even if not preceded by "given that"
        t = re.sub(
            r"(?i)\b([2-9]|1[0-3])\s+is\s+an?\s+irrational\b",
            r"$\\\\sqrt{\1}$ is irrational",
            t,
        )

        # Another common pattern: "(7 2 3) −−" should be "(7 - 2√3)" (minus got pushed to the end).
        t = re.sub(
            r"\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)\s*[-−]{1,2}",
            r"$(\1 - \2\\\\sqrt{\3})$",
            t,
        )

        # Same as above, but without parentheses (some extracts drop them).
        t = re.sub(
            r"(?i)\bprove that\s+(\d+)\s+(\d+)\s+(\d+)\s*[-−]{1,2}",
            r"Prove that $(\1 - \2\\\\sqrt{\3})$",
            t,
        )

        # Pattern: "Show that 5+2 7 is an irrational number, where 7 is given to be an irrational number."
        # Reconstruct the missing radical in both the expression and the "where/given" clause.
        def _plus_surd(m):
            a, b, c = m.group(1), m.group(2), m.group(3)
            return f"$({a} + {b}\\\\sqrt{{{c}}})$"

        def _minus_surd(m):
            a, b, c = m.group(1), m.group(2), m.group(3)
            return f"$({a} - {b}\\\\sqrt{{{c}}})$"

        # Keep conservative: only rewrite when it looks like a + b c (with whitespace between b and c)
        # and we do NOT see a multiplication sign in the string (to avoid corrupting 7×11×13 patterns).
        if "×" not in t and " x " not in t.lower():
            t = re.sub(r"\b(\d+)\s*\+\s*(\d+)\s+(\d+)\b", _plus_surd, t)
            t = re.sub(r"\b(\d+)\s*-\s*(\d+)\s+(\d+)\b", _minus_surd, t)

        # If the statement says the radicand is irrational, fix that too: "where 7 is given..." -> "where √7 is given..."
        t = re.sub(r"(?i)\bwhere\s+(\d+)\s+is\s+given\s+to\s+be\s+an?\s+irrational\b", r"where $\\\\sqrt{\1}$ is given to be an irrational", t)
        t = re.sub(r"(?i)\bgiven that\s+(\d+)\s+is\s+an?\s+irrational\b", r"Given that $\\\\sqrt{\1}$ is an irrational", t)

        # Assertion/Reason formatting cleanups inside irrational questions.
        t = re.sub(r"(?i)\bAssertion\s*\(\s*A\s*\)\s*:", "Assertion (A):", t)
        t = re.sub(r"(?i)\bReason\s*\(\s*R\s*\)\s*:", "\nReason (R):", t)
        t = re.sub(r"(?i)\bAssertion\s*:?", "Assertion:", t)
        # Remove stray mark token right before Reason in assertion-reason questions.
        t = re.sub(r"([.?!])\s*([1-5])\s+(?=Reason\b)", r"\1 ", t, flags=re.IGNORECASE)
        t = re.sub(r"\s+([1-5])\s+(?=Reason\b)", " ", t, flags=re.IGNORECASE)

        # Reconstruct missing radical in patterns like: "2(5 2) -" -> "2(5 - √2)"
        t = re.sub(
            r"\b(\d+)\s*\(\s*(\d+)\s+(\d+)\s*\)\s*[-−]{1,2}",
            r"$\1(\2 - \\\\sqrt{\3})$",
            t,
        )

        # Specific common question: "( ) 5 3 2 +" -> "$(5 + 3\\sqrt{2})$"
        t = re.sub(
            r"(?i)prove that\s*\(\s*\)\s*5\s*3\s*2\s*\+",
            r"prove that $(5 + 3\\sqrt{2})$",
            t,
        )

        # NEW: Handle "5 3 2 +" as "$(5 + 3\sqrt{2})$" when not preceded by parentheses too.
        t = re.sub(
            r"(?i)\b(\d+)\s+(\d+)\s+(\d+)\s*\+",
            r"$(\1 + \2\\\\sqrt{\3})$",
            t,
        )

    # Quadratic-equation roots: some PDFs drop the radical sign in coefficients like "2 √5 px",
    # and we get "2 5px". Attempt this repair only when the text looks like a quadratic equation.
    looks_quadratic = bool(re.search(r"(?i)\bquadratic equation\b", t) or (("x^2" in t) and re.search(r"=\s*0\b", t)))
    if (looks_quadratic or subject == "Science") and "×" not in t:
        # Example: "px2 - 2 5px + 15 = 0" -> "px2 - 2√5px + 15 = 0"
        t = re.sub(
            r"([+\-])\s*(\d+)\s+([23571113])\s*([a-zA-Z]*x\b)",
            r"\1 \2√\3\4",
            t,
        )

    # Specific Science formula cleanups: CO 2 -> CO2, H 2 O -> H2O, etc.
    if subject == "Science" or any(c in t for c in "→= "):
        t = clean_science_formulas(t)

    # English-specific cleanups: "Answer ANY ONE of the following" headers
    if subject == "English":
        t = re.sub(r"(?i)\bAnswer\s+ANY\s+ONE\s+of\s+the\s+following\s+in\s+about\s+\d+\s+words:?", "", t)
        t = re.sub(r"(?i)\bRead\s+the\s+extract\s+given\s+below\s+and\s+answer\s+the\s+questions\s+that\s+follow:?", "", t)

    # Social Science-specific cleanups
    if subject == "Social Science":
        t = re.sub(r"(?i)\bMap\s+Skill\s+Based\s+Question\b", "", t)

    # Improve MCQ readability: put each option on a new line.
    t = re.sub(r"\s*\((A|B|C|D)\)\s*", r"\n(\1) ", t)
    t = re.sub(r"\s*\((a|b|c|d)\)\s*", r"\n(\1) ", t)
    t = re.sub(r"\n{2,}", "\n", t).strip()

    # Remove trailing marks indicator like a lone '1' before options in many papers.
    t = re.sub(r"(?i)\b(is|are|equals?)\s+([1-5])\s*(?=\n\([A-Da-d]\))", r"\1 ", t)
    t = re.sub(r"(?m)^\s*[1-5]\s*$", "", t)  # mark on its own line
    t = re.sub(r"\n{2,}", "\n", t).strip()
    # Remove marks as a trailing token after the sentence: "... . 2" or "... ? 1"
    t = re.sub(r"(?s)([.?!])\s*([1-5])\s*$", r"\1", t).strip()

    # Remove marks digit that appears right before an embedded-solution marker.
    # Example: "Find LCM ... prime factorization. 2 Prime factor = ..."
    t = re.sub(
        r"([.?!])\s*([1-5])\s+(?=(prime factor|prime factorisation|least exponent|to find the lcm|to find the hcf|solution|sol\.))",
        r"\1 ",
        t,
        flags=re.IGNORECASE,
    )

    # Remove marks digit right before OR choices: "... . 2 OR" -> "... . OR"
    t = re.sub(r"([.?!])\s*([1-5])\s+(?=OR\b)", r"\1 ", t, flags=re.IGNORECASE)

    # Assertion/Reason formatting cleanup (global): put Reason on its own line, normalize labels.
    t = re.sub(r"(?i)\s+Reason\s*\(\s*R\s*\)\s*:\s*", "\nReason (R): ", t)
    # Convert "Assertion: (A) :" -> "Assertion (A):"
    t = re.sub(r"(?i)\bAssertion\s*:?\s*\(\s*A\s*\)\s*:\s*", "Assertion (A): ", t)
    # If we still have a standalone "Assertion:" followed by "(A) :", collapse it.
    t = re.sub(r"(?i)\bAssertion\s*:\s*\(?A\)?\s*:\s*", "Assertion (A): ", t)
    # Remove redundant "(A) :" when already inside an assertion block.
    t = re.sub(r"(?m)^Assertion\s*:\s*\\(A\\)\\s*:\\s*", "Assertion (A): ", t)
    # Normalize "Assertion:" header alone.
    t = re.sub(r"(?i)\bAssertion\s*:\s*\(A\)\s*:", "Assertion (A):", t)
    t = re.sub(r"(?i)\bAssertion\s*:\s*\(A\)\s*:\s*", "Assertion (A): ", t)
    # Common extracted pattern: "Assertion: (A) : ..." (spaces around colon)
    t = re.sub(r"(?i)\bAssertion\s*:\s*\(A\)\s*:\s*", "Assertion (A): ", t)
    # If line starts with "(A) :", replace it.
    t = re.sub(r"(?m)^\(A\)\s*:\s*", "Assertion (A): ", t)

    # Try to reconstruct common quadratic-equation layout: coefficients spread across lines/tokens.
    # Example extracted segment might look like: "2 2 k 4 0 x x + - ="
    m = re.search(r"(?i)\bquadratic equation\b(.{0,120}?)\bhas\b", t.replace("\n", " "))
    if m:
        seg = m.group(1)
        seg = re.sub(r"\s+", " ", seg).strip()
        seg = seg.replace("x x", "x^2")
        # If it looks like the classic "2x^2 + kx - 4 = 0" pattern, rewrite it.
        if "x^2" in seg and "k" in seg and "4" in seg and ("=" in seg or "0" in seg):
            pretty = " 2x^2 + kx - 4 = 0 "
            t = re.sub(r"(?i)\bquadratic equation\b.{0,120}?\bhas\b", "quadratic equation" + pretty + "has", t, count=1)

    # Specific cleanup for the common rational-roots MCQ in many papers.
    if re.search(r"(?i)quadratic equation 2x\^2 \+ kx - 4 = 0", t):
        t = re.sub(r"\(A\)\s*2\s*2\s*±", "(A) ±2√2", t)
        t = re.sub(r"\(C\)\s*2\s*±", "(C) ±2", t)
        t = re.sub(r"\(D\)\s*2\b", "(D) √2", t)

    # KaTeX-friendly fractions for sqrt denominators: 1/√2 -> $\frac{1}{\sqrt{2}}$
    def _sqrt_frac(m):
        num = m.group(1)
        den = m.group(2)
        return f"$\\\\frac{{{num}}}{{\\\\sqrt{{{den}}}}}$"

    t = re.sub(r"\b(\d+)\s*/\s*√\s*(\d+)\b", _sqrt_frac, t)

    # KaTeX-friendly simple fractions in MCQs: -6/5 -> $\frac{-6}{5}$
    # Keep it conservative to avoid accidentally converting years or question numbers.
    def _simple_frac(m):
        num = m.group(1)
        den = m.group(2)
        return f"$\\\\frac{{{num}}}{{{den}}}$"

    t = re.sub(r"(?<!\d)(-?\d{1,3})\s*/\s*(\d{1,3})(?!\d)", _simple_frac, t)

    # Render square roots with KaTeX when the glyph exists (common in some extracts).
    # Examples: √2, 3√2 -> $\sqrt{2}$, $3\sqrt{2}$
    t = re.sub(r"(?<!\$)(\d+)\s*√\s*(\d+)(?=\\b|[a-zA-Z])", r"$\1\\\\sqrt{\2}$", t)
    t = re.sub(r"(?<!\$)√\s*(\d+)(?=\\b|[a-zA-Z])", r"$\\\\sqrt{\1}$", t)

    # If it looks like a math expression with x^2, try to wrap it in $.
    t = re.sub(r"\b([a-z]\s*[+\-*/]\s*[a-z])\b", r"$\1$", t)
    t = re.sub(r"\b([a-z]\^\{?\d+\}?)\b", r"$\1$", t)

    # Avoid double $$
    t = t.replace("$$", "$")

    t = t.strip()
    t = t.replace("≠", " not equal ")
    return t


def infer_chapter(question_text: str, subject: str = "Mathematics") -> str:
    norm = normalize_text(question_text)
    
    if subject == "Mathematics":
        rules = MATH_CHAPTER_RULES
    elif subject == "Science":
        # Simplified rules for Science
        rules = [
            ("Chemical Reactions and Equations", ["chemical reaction", "equation", "oxidat", "reduc", "displacement"]),
            ("Acids, Bases and Salts", ["acid", "base", "salt", "ph", "litmus"]),
            ("Metals and Non-metals", ["metal", "non-metal", "ore", "calcination", "roasting", "alloy"]),
            ("Carbon and its Compounds", ["carbon", "hydrocarbon", "alkane", "alkene", "alkyne", "functional group"]),
            ("Life Processes", ["life process", "photosynthesis", "respiration", "circulation", "excretion"]),
            ("Control and Coordination", ["nervous system", "hormone", "brain", "reflex", "neuron"]),
            ("How do Organisms Reproduce?", ["reproduce", "reproduction", "asexual", "sexual", "fission", "gamete"]),
            ("Heredity and Evolution", ["heredity", "evolution", "mendel", "gene", "chromosome"]),
            ("Light – Reflection and Refraction", ["light", "reflection", "refraction", "mirror", "lens", "focal length"]),
            ("Human Eye and Colorful World", ["human eye", "cornea", "retina", "myopia", "hypermetropia", "rainbow"]),
            ("Electricity", ["electricity", "electric current", "resistance", "ohm's law", "potential difference"]),
            ("Magnetic Effects of Electric Current", ["magnetic", "field", "solenoid", "motor", "generator", "induction"]),
            ("Our Environment", ["environment", "ecosystem", "food chain", "food web", "ozone"]),
        ]
    elif subject == "Social Science":
        rules = [
            ("Rise of Nationalism in Europe", ["nationalism", "europe", "napoleon", "unification", "italy", "germany"]),
            ("Nationalism in India", ["nationalism", "india", "gandhiji", "satyagraha", "congress", "civil disobedience"]),
            ("The Making of a Global World", ["global world", "silk route", "migration", "indentured labour", "bretton woods"]),
            ("The Age of Industrialisation", ["industrialisation", "factories", "labour", "industrial revolution"]),
            ("Print Culture and the Modern World", ["print culture", "books", "manuscripts", "gutenberg", "vernacular"]),
            ("Resources and Development", ["resources", "development", "land", "soil", "sustainable"]),
            ("Forest and Wildlife Resources", ["forest", "wildlife", "conservation", "biodiversity"]),
            ("Water Resources", ["water resources", "dams", "irrigation", "rainwater harvesting"]),
            ("Agriculture", ["agriculture", "crops", "farming", "kharif", "rabi"]),
            ("Minerals and Energy Resources", ["minerals", "energy", "coal", "petroleum", "solar"]),
            ("Manufacturing Industries", ["manufacturing", "industries", "textile", "iron", "steel"]),
            ("Lifelines of National Economy", ["national economy", "transport", "railways", "roadways", "ports"]),
            ("Power Sharing", ["power sharing", "belgium", "sri lanka", "majoritarianism", "federalism"]),
            ("Federalism", ["federalism", "central government", "state government", "panchayat"]),
            ("Gender, Religion and Caste", ["gender", "religion", "caste", "patriarchy", "secular"]),
            ("Political Parties", ["political parties", "elections", "alliance", "manifesto"]),
            ("Outcomes of Democracy", ["outcomes of democracy", "accountable", "legitimate", "inequality"]),
            ("Development", ["development", "per capita income", "bmi", "hdi"]),
            ("Sectors of the Indian Economy", ["sectors", "indian economy", "primary", "secondary", "tertiary", "gdp", "nrega"]),
            ("Money and Credit", ["money", "credit", "banks", "shg", "informal"]),
            ("Globalization and the Indian Economy", ["globalization", "indian economy", "mnc", "liberalization", "wto"]),
            ("Consumer Rights", ["consumer rights", "copra", "consumer forums", "isi", "agmark"]),
        ]
    elif subject == "English":
        rules = [
            ("Reading Skills", ["reading", "passage", "comprehension"]),
            ("Writing Skills", ["writing", "letter", "report", "article", "paragraph"]),
            ("Grammar", ["grammar", "tense", "determiner", "modal", "reporting"]),
            ("Literature - First Flight", ["first flight", "lencho", "mandela", "anne frank"]),
            ("Literature - Footprints Without Feet", ["footprints", "triumph", "surgery", "thief's story"]),
        ]
    else:
        rules = []

    for chapter, keywords in rules:
        if any(k in norm for k in keywords):
            return chapter
            
    # Fallback to general chapter names per subject
    return "Miscellaneous"


def marks_from_text(question_text: str) -> int:
    # If options are present, treat as 1-mark (as per your rule).
    t = question_text or ""
    # Standard MCQ format: (A) (B) (C) (D)
    if re.search(r"(?m)^\s*\(([A-D])\)\s+", t):
        return 1
    # Assertion/Reason MCQ: has the well-known (a) Both A and R... options.
    if "Assertion" in t and (
        "Both A and R" in t
        or "A is true" in t
        or "A is false" in t
    ):
        if re.search(r"(?m)^\s*\(([a-d])\)\s+", t) and len(re.findall(r"(?m)^\s*\(([a-d])\)\s+", t)) >= 3:
            return 1

    # Heuristic when dataset doesn't store marks.
    n = len((question_text or "").strip())
    if n < 90:
        return 1
    if n < 220:
        return 2
    if n < 420:
        return 3
    return 4


def split_steps(solution_text: str) -> list[str]:
    lines = [ln.strip() for ln in (solution_text or "").splitlines()]
    return [ln for ln in lines if ln]


@dataclass
class Rec:
    id: str
    chapter: str
    subject: str
    year: str
    question_number: str
    text: str
    norm: str
    solution: str
    source_file: str


def build_records(raw: list[dict]) -> list[Rec]:
    out: list[Rec] = []
    for q in raw:
        subject_dir = q.get("subject", "maths")
        subject = SUBJECT_DISPLAY_NAME.get(subject_dir, "Mathematics")
        year = str(q.get("year", "") or "")
        qn = str(q.get("question_number", "") or "")
        text = clean_display_question(clean_question_text(q.get("question_text", "") or ""))
        chapter = infer_chapter(text, subject)
        norm = normalize_text(text)
        key = f"{subject}|{chapter}|{year}|{qn}|{norm[:240]}"
        rid = md5(key.encode("utf-8")).hexdigest()[:16]
        out.append(
            Rec(
                id=rid,
                chapter=chapter,
                subject=subject,
                year=year,
                question_number=qn,
                text=text,
                norm=norm,
                solution=q.get("solution_text", "") or "",
                source_file=q.get("source_file", "") or "",
            )
        )
    return out


def cluster_by_similarity(records: list[Rec], subject_chapters: list[str], threshold: float = 0.82):
    grouped: dict[str, list[Rec]] = defaultdict(list)
    for r in records:
        grouped[r.chapter].append(r)

    clusters: list[list[Rec]] = []
    for chapter in subject_chapters:
        items = grouped.get(chapter, [])
        local: list[list[Rec]] = []
        for item in items:
            assigned = False
            for cl in local:
                rep = cl[0].norm
                if rep and item.norm:
                    # Dynamic threshold helps short questions cluster without forcing long ones to over-merge.
                    sim_threshold = threshold
                    if len(item.norm) < 120 or len(rep) < 120:
                        sim_threshold = min(sim_threshold, 0.78)
                    if len(item.norm) < 70 or len(rep) < 70:
                        sim_threshold = min(sim_threshold, 0.75)

                    sim = SequenceMatcher(None, rep, item.norm).ratio()

                    # Guardrails to avoid false merges while increasing recall.
                    rep_toks = token_set(rep)
                    item_toks = token_set(item.norm)
                    common = len(rep_toks.intersection(item_toks))
                    min_tok = max(1, min(len(rep_toks), len(item_toks)))
                    # For short questions, token sets are small, so require fewer common tokens.
                    common_needed = 5 if min_tok >= 10 else 3 if min_tok >= 7 else 2

                    rep_tok_ratio = common / min_tok

                    rep_len = max(1, len(rep))
                    len_ratio = abs(len(rep) - len(item.norm)) / rep_len
                    len_ratio_ok = len_ratio <= (0.55 if (len(rep) < 120 or len(item.norm) < 120) else 0.45)

                    if (sim >= sim_threshold and common >= common_needed and len_ratio_ok) or (rep_tok_ratio > 0.85 and common >= 4):
                        cl.append(item)
                        assigned = True
                        break
            if not assigned:
                local.append([item])
        clusters.extend(local)

    return clusters


def choose_rep(items: list[Rec]) -> Rec:
    def score(x: Rec):
        y = int(x.year) if x.year.isdigit() else 0
        return (y, len(x.text))

    return sorted(items, key=score, reverse=True)[0]


def main() -> None:
    if not SRC_JSON.exists():
        raise SystemExit(f"Missing source dataset: {SRC_JSON}")

    raw = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    all_records = build_records(raw)

    processed_subjects = set()
    for sub_dir, sub_display in SUBJECT_DISPLAY_NAME.items():
        if sub_display in processed_subjects:
            continue
        
        records = [r for r in all_records if r.subject == sub_display]
        if not records:
            continue

        processed_subjects.add(sub_display)

        subject_chapters = CHAPTERS_BY_SUBJECT.get(sub_display, [])
        clusters = cluster_by_similarity(records, subject_chapters)

        questions = []
        years_all: set[str] = set()

        for cl in clusters:
            rep = choose_rep(cl)
            question_text = clean_display_question(rep.text, sub_display)

            # Always apply the heuristic split; many PDFs embed steps in the question text,
            # even when a separate solution field exists.
            question_text, extra_solution = _split_question_solution_heuristic(question_text)
            if extra_solution:
                extra_solution = format_embedded_solution(extra_solution)
            years = sorted({x.year for x in cl if x.year})
            for y in years:
                years_all.add(y)
            frequency = len(years) if years else 1

            # Per-question Oswaal hints default to chapter hints.
            chapter_meta = CHAPTER_OSWAAL.get(rep.chapter, DEFAULT_CHAPTER_META)

            combined_solution = clean_display_question(rep.solution or "", sub_display)
            if extra_solution:
                combined_solution = (combined_solution + "\n" + extra_solution).strip()

            # Manual override for known missing solutions
            if not combined_solution and "linear equations x = a and y = b" in question_text.lower():
                combined_solution = (
                    "The equation x = a represents a vertical line passing through (a, 0).\n"
                    "The equation y = b represents a horizontal line passing through (0, b).\n"
                    "These two lines are perpendicular to each other and intersect at the point (a, b).\n"
                    "Since a ≠ b, they are distinct lines and they are not coincident or parallel.\n"
                    "Therefore, the lines intersect at (a, b).\n"
                    "Correct Option: (A)"
                )

            questions.append(
                {
                    "id": f"{rep.chapter}|{md5(rep.norm.encode('utf-8')).hexdigest()[:10]}",
                    "chapter": rep.chapter,
                    "marks": marks_from_text(question_text),
                    "text": question_text,
                    "solution": combined_solution,
                    "solution_steps": split_steps(combined_solution),
                    "frequency": frequency,
                    "years": years,
                    "occurrences": [
                        {
                            "year": x.year,
                            "question_number": x.question_number,
                            "source_file": x.source_file,
                        }
                        for x in sorted(cl, key=lambda z: (z.year, z.question_number))
                    ],
                    "common_errors": chapter_meta["errors"],
                    "toppers_secrets": chapter_meta["secrets"],
                }
            )

        chapters = []
        for name in subject_chapters:
            meta = CHAPTER_OSWAAL.get(name, DEFAULT_CHAPTER_META)
            chapters.append(
                {
                    "name": name,
                    "errors": meta["errors"],
                    "secrets": meta["secrets"],
                    "mind_map_note": meta["mind_map_note"],
                }
            )

        out = {
            "meta": {
                "source": str(SRC_JSON.relative_to(PROJECT_ROOT)),
                "years": sorted(years_all),
                "note": "Frequency is computed across available years in this dataset.",
            },
            "chapters": chapters,
            "questions": questions,
        }

        # Determine output file path
        if sub_display == "Mathematics":
            out_file = PROJECT_ROOT / "web" / "data" / "maths_data.json"
        elif sub_display == "Science":
            out_file = PROJECT_ROOT / "web" / "data" / "science.json"
        elif sub_display == "Social Science":
            out_file = PROJECT_ROOT / "web" / "data" / "social_science.json"
        elif sub_display == "English":
            out_file = PROJECT_ROOT / "web" / "data" / "english.json"
        else:
            out_file = PROJECT_ROOT / "web" / "data" / f"{sub_dir}.json"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote: {out_file} (chapters={len(chapters)} questions={len(questions)})")


if __name__ == "__main__":
    main()
