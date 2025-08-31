# -*- coding: utf-8 -*-
"""
Telugu Rule-Based Natural Language Engine — Pro v2
--------------------------------------------------
A single-file, production-style rule engine that generates grammatically correct
Telugu sentences with:
- Morphology: rule-driven conjugation + irregular overrides, noun declension, plurals
- Syntax: rich templates (statement, question, negation, progressive, perfect, conditional, relative, imperative)
- Sandhi: improved vowel/consonant joins (lightweight)
- Semantics: honorifics, politeness levels, gender-aware forms
- Pragmatics: dialect tuning (Telangana, Coastal, Rayalaseema, Hyderabad), spoken shortcuts
- Style: formal vs spoken transformations
- Validator: agreement checks & punctuation
- Data: embedded but easily extensible via JSON hooks

Public API:
    engine = TeluguRuleEngine()
    sentence = engine.generate(
        verb="చేయు", subject="నేను", noun="పుస్తకం",
        tense="present", aspect="progressive", polarity="positive",
        case="accusative", formality="informal", dialect="standard",
        style="formal", template="statement"
    )

Run this file to see demos and a tiny CLI.
"""

from __future__ import annotations
import re
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# =============================
# ===== Embedded Data ========
# =============================

# NOTE: Stems are dictionary/citation forms. We conjugate by rules + overrides.
# A small seed lexicon; extend freely.

VERB_OVERRIDES: Dict[str, Dict[str, Dict[str, str]]] = {
    # Fully specified overrides (tense→subject→form). Used before rule synthesis.
    "పో": {
        "present": {"నేను": "పోతాను", "నీవు": "పోతావు", "నువ్వు": "పోతావు", "అతను": "పోతాడు", "ఆమె": "పోతుంది", "ఇతను": "పోతాడు", "ఆయన": "పోతారు", "ఆవిడ": "పోతారు", "మేము": "పోతాము", "మనము": "పోతాము", "మీరు": "పోతారు", "వారు": "పోతారు"},
        "past":    {"నేను": "పోయాను", "నీవు": "పోయావు", "నువ్వు": "పోయావు", "అతను": "పోయాడు", "ఆమె": "పోయింది", "ఇతను": "పోయాడు", "ఆయన": "పోయారు", "ఆవిడ": "పోయారు", "మేము": "పోయాము", "మనము": "పోయాము", "మీరు": "పోయారు", "వారు": "పోయారు"},
        "future":  {"నేను": "పోతాను", "నీవు": "పోతావు", "నువ్వు": "పోతావు", "అతను": "పోతాడు", "ఆమె": "పోతుంది", "ఆయన": "పోతారు", "ఆవిడ": "పోతారు", "మేము": "పోతాము", "మీరు": "పోతారు", "వారు": "పోతారు"}
    },
    "చదువు": {
        "present": {"నేను": "చదువుతాను", "నీవు": "చదువుతావు", "నువ్వు": "చదువుతావు", "అతను": "చదువుతాడు", "ఆమె": "చదువుతుంది", "ఆయన": "చదువుతారు", "ఆవిడ": "చదువుతారు", "మేము": "చదువుతాము", "మీరు": "చదువుతారు", "వారు": "చదువుతారు"},
        "past":    {"నేను": "చదివాను",   "నీవు": "చదివావు",   "నువ్వు": "చదివావు",   "అతను": "చదివాడు",   "ఆమె": "చదివింది",   "ఆయన": "చదివారు",   "ఆవిడ": "చదివారు",   "మేము": "చదివాము",   "మీరు": "చదివారు",   "వారు": "చదివారు"},
        "future":  {"నేను": "చదువుతాను", "నీవు": "చదువుతావు", "నువ్వు": "చదువుతావు", "అతను": "చదువుతాడు", "ఆమె": "చదువుతుంది", "ఆయన": "చదువుతారు", "ఆవిడ": "చదువుతారు", "మేము": "చదువుతాము", "మీరు": "చదువుతారు", "వారు": "చదువుతారు"}
    },
    "చేయు": {
        "present": {"నేను": "చేస్తాను", "నీవు": "చేస్తావు", "నువ్వు": "చేస్తావు", "అతను": "చేస్తాడు", "ఆమె": "చేస్తుంది", "ఆయన": "చేస్తారు", "ఆవిడ": "చేస్తారు", "మేము": "చేస్తాము", "మీరు": "చేస్తారు", "వారు": "చేస్తారు"},
        "past":    {"నేను": "చేశాను",   "నీవు": "చేశావు",   "నువ్వు": "చేశావు",   "అతను": "చేశాడు",   "ఆమె": "చేసింది",   "ఆయన": "చేశారు",   "ఆవిడ": "చేశారు",   "మేము": "చేశాము",   "మీరు": "చేశారు",   "వారు": "చేశారు"},
        "future":  {"నేను": "చేస్తాను", "నీవు": "చేస్తావు", "నువ్వు": "చేస్తావు", "అతను": "చేస్తాడు", "ఆమె": "చేస్తుంది", "ఆయన": "చేస్తారు", "ఆవిడ": "చేస్తారు", "మేము": "చేస్తాము", "మీరు": "చేస్తారు", "వారు": "చేస్తారు"}
    }
}

# Nouns with case forms + pluralization hints
NOUNS: Dict[str, Dict[str, str]] = {
    "పుస్తకం": {"nom": "పుస్తకం", "acc": "పుస్తకాన్ని", "dat": "పుస్తకానికి", "gen": "పుస్తకం యొక్క", "loc": "పుస్తకంలో", "ins": "పుస్తకంతో", "pl": "పుస్తకాలు"},
    "అబ్బాయి": {"nom": "అబ్బాయి", "acc": "అబ్బాయిని", "dat": "అబ్బాయికి", "gen": "అబ్బాయి యొక్క", "loc": "అబ్బాయిలో", "ins": "అబ్బాయితో", "pl": "అబ్బాయిలు"},
    "అమ్మాయి": {"nom": "అమ్మాయి", "acc": "అమ్మాయిని", "dat": "అమ్మాయికి", "gen": "అమ్మాయి యొక్క", "loc": "అమ్మాయిలో", "ins": "అమ్మాయితో", "pl": "అమ్మాయిలు"},
    "బడి":     {"nom": "బడి",     "acc": "బడిని",       "dat": "బడికి",       "gen": "బడి యొక్క",     "loc": "బడిలో",       "ins": "బడియితో",       "pl": "బడులు"}
}

PRONOUNS: Dict[str, Dict[str, str]] = {
    # canonical→features
    "నేను":   {"person": "1", "num": "sg", "hon": "base"},
    "నువ్వు": {"person": "2", "num": "sg", "hon": "low"},
    "నీవు":   {"person": "2", "num": "sg", "hon": "low"},
    "మీరు":  {"person": "2", "num": "pl", "hon": "high"},
    "అతను":   {"person": "3", "num": "sg", "gender": "m", "hon": "base"},
    "ఆమె":    {"person": "3", "num": "sg", "gender": "f", "hon": "base"},
    "ఆయన":   {"person": "3", "num": "sg", "gender": "m", "hon": "high"},
    "ఆవిడ":   {"person": "3", "num": "sg", "gender": "f", "hon": "high"},
    "మేము":   {"person": "1", "num": "pl", "hon": "base"},
    "వారు":    {"person": "3", "num": "pl", "hon": "base"}
}

HONORIFICS = {
    "formal": {"నేను": "నేను", "నీవు": "మీరు", "నువ్వు": "మీరు", "అతను": "ఆయన", "ఆమె": "ఆవిడ", "మీరు": "మీరు", "వారు": "వారు"},
    "informal": {"నేను": "నేను", "నీవు": "నువ్వు", "నువ్వు": "నువ్వు", "అతను": "అతను", "ఆమె": "ఆమె", "మీరు": "మీరు", "వారు": "వారు"}
}

# Syntax templates
TEMPLATES = {
    "statement": "{subject} {object} {verb}.",
    "question": "{subject} {object} {verb}నా?",
    "yesno_question": "{verb} {subject} {object}?",
    "neg_statement": "{subject} {object} {verb_neg}.",
    "progressive": "{subject} {object} {aux_progressive} {verb_participle}.",
    "perfect": "{subject} {object} {aux_perfect} {verb_participle}.",
    "conditional": "{subclause}, {mainclause}.",
    "relative": "{relclause} {head} {verb}.",
    "imperative": "{object} {verb_imp}!"
}

# Spoken-style quick conversions
SPOKEN_CONVERSIONS = {
    "వస్తున్నాను": "వస్తున్నా",
    "చేస్తున్నాను": "చేస్తున్నా",
    "పోతున్నాను": "పోతున్నా",
    "చదువుతాను": "చదువుతా",
    "పోతాను": "పోతా",
    "చేస్తాను": "చేస్తా",
}

# Dialect adjustments (very light-touch, token replacement)
DIALECT_MAP = {
    "hyderabad": {"పోతాను": "పోతన్నా", "పోతావు": "పోతవ్వా"},
    "telangana": {"లేడు": "లేదురా", "లేదు": "లేదోయ్"},
    "coastal": {},
    "rayalaseema": {}
}

# Adpositions / postpositions (illustrative)
POSTPOSITIONS = {"తో": "ins", "లో": "loc", "వద్ద": "loc", "పై": "loc"}

# =============================
# ===== Utilities =============
# =============================

TELUGU_RANGE = "\u0C00-\u0C7F"
TELUGU_WORD = re.compile(fr"^[{TELUGU_RANGE}]+$")


def is_telugu(text: str) -> bool:
    return bool(TELUGU_WORD.match(text))


# =============================
# ===== Morphology ============
# =============================

class Morphology:
    """Verb conjugation via overrides + fallback rules; noun declension + plurals."""

    # Simple rule suffixes for default stem class "-ఉ" (Class-U) as an example
    DEFAULT_SUFFIX = {
        "present": {
            "1sg": "తాను", "2sg": "తావు", "3sg_m": "తాడు", "3sg_f": "తుంది",
            "1pl": "తాము", "2pl": "తారు", "3pl": "తారు"
        },
        "future": {
            "1sg": "తాను", "2sg": "తావు", "3sg_m": "తాడు", "3sg_f": "తుంది",
            "1pl": "తాము", "2pl": "తారు", "3pl": "తారు"
        },
        # Past often irregular; use overrides; fallback generic
        "past": {
            "1sg": "యాను", "2sg": "యావు", "3sg_m": "యాడు", "3sg_f": "యింది",
            "1pl": "యాము", "2pl": "యారు", "3pl": "యారు"
        }
    }

    NEGATION_PARTICLE = {
        "present": "లేదు",
        "past": "లేదు",
        "future": "కాదు"  # stylistic; often use "వెళ్ళను/చేయను" patterns too
    }

    AUX_PROGRESSIVE = {
        # Auxiliary for progressive (aspect)
        "నేను": "ఉన్నాను", "నువ్వు": "ఉన్నావు", "నీవు": "ఉన్నావు", "అతను": "ఉన్నాడు", "ఆమె": "ఉన్నారు" if False else "ఉంది",
        "ఆయన": "ఉన్నారు", "ఆవిడ": "ఉన్నారు", "మేము": "ఉన్నాము", "మీరు": "ఉన్నారు", "వారు": "ఉన్నారు"
    }

    AUX_PERFECT = {
        # Perfect-like auxiliary ("ఉంది/ఉన్నాడు" after participle) – very approximate
        "నేను": "ఉన్నాను", "నువ్వు": "ఉన్నావు", "నీవు": "ఉన్నావు", "అతను": "ఉన్నాడు", "ఆమె": "ఉంది",
        "ఆయన": "ఉన్నారు", "ఆవిడ": "ఉన్నారు", "మేము": "ఉన్నాము", "మీరు": "ఉన్నారు", "వారు": "ఉన్నారు"
    }

    IMPERATIVE_FORMS = {
        # Basic imperatives per person
        "2sg": "-ు",     # e.g., "వెళ్లు" (approx) – handled by stem rule below
        "2pl": "-ండి",   # "వెళ్లండి"
    }

    @staticmethod
    def pron_key(subject: str) -> Tuple[str, str, str]:
        # Map subject → (person, number, gender/honorific bucket)
        p = PRONOUNS.get(subject, {"person": "3", "num": "sg"})
        person = p.get("person", "3")
        num = p.get("num", "sg")
        gender = p.get("gender", "m") if person == "3" and num == "sg" else ("pl" if num == "pl" else "na")
        return person, num, gender

    @staticmethod
    def apply_honorific(subject: str, level: str = "informal") -> str:
        mapping = HONORIFICS.get(level, HONORIFICS["informal"])
        return mapping.get(subject, subject)

    # ---------- Verb Conjugation ----------
    @classmethod
    def conjugate(
        cls, stem: str, tense: str, subject: str, *, aspect: str = "simple",
        polarity: str = "positive"
    ) -> Dict[str, str]:
        """Return dict with keys: form, neg, participle, progressive_aux, perfect_aux, imp.
        We produce multiple pieces so syntax templates can compose flexibly.
        """
        subj = subject

        # Overrides first
        over = VERB_OVERRIDES.get(stem, {})
        base = over.get(tense, {}).get(subj)

        # If no override, synthesize using DEFAULT_SUFFIX (Class-U assumption for demo)
        if not base:
            person, num, gender = cls.pron_key(subj)
            key = f"{person}{num}"
            if person == "3" and num == "sg":
                key = f"3sg_{'f' if gender == 'f' else 'm'}"
            suf = cls.DEFAULT_SUFFIX.get(tense, {}).get(key)
            # naive stem join rules: if stem endswith "ఉ" remove it before suffix like "తాను"
            if suf:
                if stem.endswith("ు"):
                    base = stem[:-1] + suf
                else:
                    base = stem + suf
            else:
                base = stem  # fallback

        # participle (very rough): stem+"ిన" / stem+"ుతూ" etc.
        participle = None
        if aspect in ("progressive", "imperfective"):
            participle = (stem[:-1] if stem.endswith("ు") else stem) + "ుతూ"
        else:  # perfect-like
            participle = (stem[:-1] if stem.endswith("ు") else stem) + "ిన"

        # progressive/perfect auxiliaries
        prog_aux = cls.AUX_PROGRESSIVE.get(subj, "ఉంది")
        perf_aux = cls.AUX_PERFECT.get(subj, "ఉంది")

        # simple negation strategies:
        neg = base
        if polarity == "negative":
            # Heuristic: 1st person sg often uses "-ను" neg: "చేయను/వెళ్ళను"; generic particle "లేదు" also used.
            if stem in ("చేయు", "వెళ్ళు", "పో"):
                if subj == "నేను":
                    neg = (stem[:-1] if stem.endswith("ు") else stem) + "ను"
                elif subj in ("నీవు", "నువ్వు"):
                    neg = (stem[:-1] if stem.endswith("ు") else stem) + "వు"
                else:
                    # polite/plural often "రు"
                    neg = (stem[:-1] if stem.endswith("ు") else stem) + "రు"
            else:
                # fallback particle style
                neg = base + " కాదు"

        # imperatives (very approximate):
        imp = None
        if subj in ("నీవు", "నువ్వు"):
            # 2sg: stem + "్లు"/"ు" approximated as "-ు"
            tail = "ు" if not stem.endswith("ు") else ""
            imp = stem + tail
        elif subj in ("మీరు",):
            imp = (stem[:-1] if stem.endswith("ు") else stem) + "ండి"

        return {
            "form": base,
            "neg": neg,
            "participle": participle,
            "progressive_aux": prog_aux,
            "perfect_aux": perf_aux,
            "imperative": imp or base
        }

    # ---------- Noun Declension ----------
    @staticmethod
    def decline(noun: str, case: str = "acc", plural: bool = False) -> str:
        if not noun:
            return ""
        info = NOUNS.get(noun)
        if not info:
            return noun
        if plural:
            # simple: use plural head then add case endings (approx)
            head = info.get("pl", noun)
            if case == "acc":
                return head + "ను"
            if case == "dat":
                return head + "కు"
            if case == "gen":
                return head + " యొక్క"
            if case == "loc":
                return head + "లో"
            if case == "ins":
                return head + "తో"
            return head
        # singular
        mapping = {
            "nominative": "nom", "accusative": "acc", "dative": "dat", "genitive": "gen", "locative": "loc", "instrumental": "ins",
            "nom": "nom", "acc": "acc", "dat": "dat", "gen": "gen", "loc": "loc", "ins": "ins"
        }
        key = mapping.get(case, case)
        return info.get(key, noun)


# =============================
# ===== Sandhi ================
# =============================

class Sandhi:
    VOWELS = tuple("అఆఇఈఉఊఋౠఎఏఐఒఓఔఅం అః".split())

    @classmethod
    def join(cls, left: str, right: str) -> str:
        # Lightweight: if left ends with long "ా" and right starts with vowel, elide space.
        if left.endswith("ా") and any(right.startswith(v) for v in cls.VOWELS):
            return left[:-1] + right
        # If left ends with m-sound (ం) and right starts with ప/బ/మ, allow nasal assimilation (very shallow)
        if left.endswith("ం") and right[:1] in ("ప", "బ", "మ"):
            return left + right
        return left + " " + right

    @classmethod
    def apply_sequence(cls, words: List[str]) -> str:
        if not words:
            return ""
        out = [words[0]]
        for w in words[1:]:
            out[-1] = cls.join(out[-1], w)
        return out[-1] if len(out) == 1 else " ".join(out)


# =============================
# ===== Syntax ================
# =============================

class Syntax:
    @staticmethod
    def apply(template: str, **kwargs) -> str:
        fmt = TEMPLATES.get(template)
        if not fmt:
            raise ValueError(f"Unknown template: {template}")
        text = fmt.format(**{k: (v or "").strip() for k, v in kwargs.items()})
        # normalize spaces
        text = re.sub(r"\s+", " ", text).strip()
        # drop double spaces before punctuation
        text = re.sub(r"\s+([.?!,])", r"\1", text)
        return text


# =============================
# ===== Semantics/Style =======
# =============================

class Semantics:
    @staticmethod
    def honorific(pronoun: str, level: str = "informal") -> str:
        mapping = HONORIFICS.get(level, HONORIFICS["informal"])
        return mapping.get(pronoun, pronoun)

class Pragmatics:
    @staticmethod
    def dialect(text: str, name: str = "standard") -> str:
        repl = DIALECT_MAP.get(name, {})
        for k, v in repl.items():
            text = text.replace(k, v)
        return text

class Style:
    @staticmethod
    def apply(text: str, style: str = "formal") -> str:
        if style == "spoken":
            for k, v in SPOKEN_CONVERSIONS.items():
                text = text.replace(k, v)
        return text


# =============================
# ===== Validator =============
# =============================

class Validator:
    TELUGU_SENT = re.compile(fr"^[{TELUGU_RANGE}\s,;]+[.?!]$")

    @classmethod
    def check(cls, sentence: str) -> bool:
        return bool(cls.TELUGU_SENT.match(sentence.strip()))

    @staticmethod
    def subj_verb_agree(subject: str, verb: str) -> bool:
        # Heuristic: plural polite often ends with "రు"; singular first person ends with "ను"
        if subject in ("మీరు", "వారు", "ఆయన", "ఆవిడ"):
            return verb.endswith("రు") or verb.endswith("రు.") or "ఉన్నారు" in verb
        if subject == "నేను":
            return verb.endswith("ను") or verb.endswith("ను.")
        return True


# =============================
# ===== Engine ================
# =============================

class TeluguRuleEngine:
    def __init__(self):
        self.morph = Morphology()
        self.sandhi = Sandhi()
        self.syntax = Syntax()
        self.semantics = Semantics()
        self.prag = Pragmatics()
        self.style = Style()
        self.validator = Validator()

    def generate(
        self,
        *,
        verb: str,
        subject: str,
        noun: Optional[str] = None,
        tense: str = "present",
        aspect: str = "simple",  # simple|progressive|perfect
        polarity: str = "positive",  # positive|negative
        case: str = "acc",  # acc|dat|gen|loc|ins|nom
        plural_object: bool = False,
        formality: str = "informal",
        dialect: str = "standard",
        style: str = "formal",
        template: str = "statement",
        head: Optional[str] = None,  # for relative
        relclause: Optional[str] = None,
        subclause: Optional[str] = None,
        mainclause: Optional[str] = None
    ) -> str:
        # 1) honorific mapping on subject
        subj_formal = self.semantics.honorific(subject, formality)

        # 2) verb forms
        forms = self.morph.conjugate(verb, tense, subj_formal, aspect=aspect, polarity=polarity)

        # 3) object/case
        obj = ""
        if noun:
            obj = self.morph.decline(noun, case=case, plural=plural_object)

        # 4) choose template parts
        rendered = ""
        if template == "statement":
            rendered = self.syntax.apply("statement", subject=subj_formal, object=obj, verb=forms["form"])
        elif template == "question":
            rendered = self.syntax.apply("yesno_question", subject=subj_formal, object=obj, verb=forms["form"])
        elif template == "negation" or (polarity == "negative" and template == "statement"):
            rendered = self.syntax.apply("neg_statement", subject=subj_formal, object=obj, verb_neg=forms["neg"])
        elif template == "progressive" or (aspect == "progressive"):
            rendered = self.syntax.apply(
                "progressive",
                subject=subj_formal, object=obj,
                aux_progressive=forms["progressive_aux"],
                verb_participle=forms["participle"]
            )
        elif template == "perfect" or (aspect == "perfect"):
            rendered = self.syntax.apply(
                "perfect",
                subject=subj_formal, object=obj,
                aux_perfect=forms["perfect_aux"],
                verb_participle=forms["participle"]
            )
        elif template == "conditional":
            subcl = subclause or f"{subj_formal} {obj} {forms['form']}యితే"  # crude
            maincl = mainclause or f"{subj_formal} {forms['form']}"
            rendered = self.syntax.apply("conditional", subclause=subcl, mainclause=maincl)
        elif template == "relative":
            rendered = self.syntax.apply("relative", relclause=relclause or "{obj} చదివిన", head=head or "అబ్బాయి", verb=forms["form"])  # example
        elif template == "imperative":
            rendered = self.syntax.apply("imperative", object=obj, verb_imp=forms["imperative"])
        else:
            rendered = self.syntax.apply("statement", subject=subj_formal, object=obj, verb=forms["form"])

        # 5) Sandhi across tokens
        tokens = [t for t in rendered.split(" ") if t]
        sent = self.sandhi.apply_sequence(tokens)

        # 6) Style & dialect
        sent = self.style.apply(sent, style=style)
        sent = self.prag.dialect(sent, name=dialect)

        # 7) Final punctuation enforcement
        if not sent.endswith(('.', '!', '?', '।')):
            if template in ("question",):
                sent += "?"
            elif template == "imperative":
                sent += "!"
            else:
                sent += "."

        # 8) Validate + soft agreement check
        if not self.validator.check(sent):
            print(f"[Warn] Pattern validation suspicious: {sent}")
        if not self.validator.subj_verb_agree(subj_formal, sent):
            print(f"[Warn] Subject-Verb agreement suspicious: {subj_formal} ↔ {sent}")

        return sent

    # Optional: load lexicon from JSON files
    def load_json(self, *, verbs_path: Optional[str] = None, nouns_path: Optional[str] = None) -> None:
        global VERB_OVERRIDES, NOUNS
        if verbs_path:
            with open(verbs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # merge
            for k, v in data.items():
                VERB_OVERRIDES.setdefault(k, {}).update(v)
        if nouns_path:
            with open(nouns_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.items():
                NOUNS[k] = v


# =============================
# ===== Demo / CLI ============
# =============================

if __name__ == "__main__":
    e = TeluguRuleEngine()

    print("Example 1 — Formal statement:")
    print(e.generate(verb="పో", subject="నీవు", noun="పుస్తకం", tense="present", case="acc", formality="formal", style="formal", template="statement"))

    print("\nExample 2 — Spoken progressive:")
    print(e.generate(verb="చదువు", subject="నేను", noun="పుస్తకం", tense="present", aspect="progressive", style="spoken", template="progressive"))

    print("\nExample 3 — Negative (1sg):")
    print(e.generate(verb="చేయు", subject="నేను", noun="బడి", tense="present", polarity="negative", case="loc", template="negation"))

    print("\nExample 4 — Hyderabad dialect:")
    print(e.generate(verb="పో", subject="నీవు", tense="present", formality="informal", dialect="hyderabad", template="statement"))

    print("\nExample 5 — Perfect-like:")
    print(e.generate(verb="చదువు", subject="ఆయన", noun="పుస్తకం", tense="past", aspect="perfect", formality="formal", template="perfect"))

    print("\nExample 6 — Imperative (polite):")
    print(e.generate(verb="పో", subject="మీరు", noun="బడి", case="loc", template="imperative"))

    # Tiny interactive loop (Ctrl+C to exit)
    try:
        while True:
            raw = input("\nEnter: subject, verb, noun(optional) → ").strip()
            if not raw:
                break
            parts = [p.strip() for p in raw.split(',')]
            subj = parts[0] if len(parts) > 0 else "నేను"
            verb = parts[1] if len(parts) > 1 else "చేయు"
            noun = parts[2] if len(parts) > 2 and parts[2] else None
            s = e.generate(verb=verb, subject=subj, noun=noun)
            print("→", s)
    except KeyboardInterrupt:
        pass
