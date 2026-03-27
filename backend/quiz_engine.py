import random
import re


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "their",
    "them",
    "these",
    "those",
    "which",
    "will",
    "would",
    "can",
    "could",
    "should",
    "about",
    "there",
    "here",
    "your",
    "you",
    "our",
    "they",
    "but",
    "not",
    "also",
    "than",
    "then",
    "its",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
}


def _sentences(text):
    cleaned = re.sub(r"\s+", " ", text.strip())
    chunks = re.split(r"(?<=[.!?])\s+", cleaned)
    return [c for c in chunks if len(c.split()) >= 8]


def _keywords(text):
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())
    words = [t for t in tokens if t not in STOPWORDS and len(t) > 4]
    return list(dict.fromkeys(words))


def _difficulty_for_sentence(sentence):
    word_count = len(sentence.split())
    if word_count < 12:
        return "easy"
    if word_count < 20:
        return "medium"
    return "hard"


def _mcq_from_sentence(sentence, pool):
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", sentence)
    candidates = [t for t in tokens if len(t) > 4]
    if not candidates:
        return None
    answer = random.choice(candidates)
    distractors = random.sample(pool, k=min(3, len(pool))) if pool else []
    options = list(dict.fromkeys([answer] + distractors))
    while len(options) < 4:
        options.append(random.choice(candidates))
        options = list(dict.fromkeys(options))
    random.shuffle(options)
    question = sentence.replace(answer, "_____", 1)
    return {
        "qtype": "mcq",
        "question": question,
        "options": options[:4],
        "answer": answer,
        "source": sentence,
    }


def _fill_blank(sentence):
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", sentence)
    candidates = [t for t in tokens if len(t) > 4]
    if not candidates:
        return None
    answer = random.choice(candidates)
    question = sentence.replace(answer, "_____", 1)
    return {
        "qtype": "fill_blank",
        "question": question,
        "options": [],
        "answer": answer,
        "source": sentence,
    }


def _true_false(sentence):
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]+", sentence)
    if len(tokens) < 6:
        return None
    if " not " in sentence:
        statement = sentence.replace(" not ", " ", 1)
        answer = "False"
    else:
        statement = sentence
        answer = "True"
    return {
        "qtype": "true_false",
        "question": statement,
        "options": ["True", "False"],
        "answer": answer,
        "source": sentence,
    }


def generate_questions(text, types, difficulty, count):
    sentences = _sentences(text)
    if not sentences:
        return []
    keyword_pool = _keywords(text)
    random.shuffle(sentences)

    generated = []
    for sentence in sentences:
        sentence_difficulty = _difficulty_for_sentence(sentence)
        if difficulty and sentence_difficulty != difficulty:
            continue
        for qtype in types:
            if qtype == "mcq":
                item = _mcq_from_sentence(sentence, keyword_pool)
            elif qtype == "fill_blank":
                item = _fill_blank(sentence)
            else:
                item = _true_false(sentence)
            if item:
                item["difficulty"] = sentence_difficulty
                generated.append(item)
            if len(generated) >= count:
                return generated
    return generated[:count]


def suggest_difficulty(performance, default_pref):
    attempts = performance.get("attempts", 0) if performance else 0
    correct = performance.get("correct", 0) if performance else 0
    if attempts < 5:
        return default_pref or "medium"
    accuracy = correct / max(attempts, 1)
    if accuracy >= 0.8:
        return "hard"
    if accuracy <= 0.5:
        return "easy"
    return "medium"
