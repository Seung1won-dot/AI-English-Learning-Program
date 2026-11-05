"""학습 콘텐츠(data/*.json) 형식 검사.

사용법:  python scripts/validate_content.py      (문제가 있으면 목록을 출력하고 종료 코드 1)

검사 항목
  toeic_vocab.json : 필수 필드, id·단어 중복, 품사·수준·주제 값, 예문에 표제어 포함 여부
  toeic_part5.json : 빈칸 정확히 1개, 보기 4개·중복 없음, 정답 하나(0~3), 유형·난이도 값, 해설
  opic_bank.json   : 주제·질문 id 중복, 질문 수, 답변 틀·표현·예시 답변
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

HANGUL = re.compile(r"[가-힣]")
BLANK = "___"

VOCAB_LEVELS = ("600", "800", "900")
VOCAB_POS = ("n.", "v.", "adj.", "adv.", "prep.", "conj.", "phr.")
VOCAB_TOPICS = ("사무·인사", "회의·일정", "마케팅·영업", "재무·회계", "생산·물류",
                "고객·서비스", "출장·여행", "계약·법무", "시설·건물", "일반")

P5_CATEGORIES = ("품사", "동사 시제·태", "수 일치", "대명사", "전치사", "접속사",
                 "관계사", "준동사", "비교", "어휘")
P5_LEVELS = ("easy", "medium", "hard")

OPIC_KINDS = ("기본", "설문", "돌발", "롤플레이")
OPIC_TYPES = ("자기소개", "묘사", "루틴", "과거 경험", "비교", "의견", "질문하기", "문제 해결")


def _missing(item, fields):
    return [f for f in fields if not str(item.get(f, "")).strip()]


def validate_vocab(data):
    errors, warnings = [], []
    words = data.get("words")
    if not isinstance(words, list) or not words:
        return ["words 배열이 없습니다."], warnings
    ids, seen = set(), set()
    for i, w in enumerate(words):
        tag = f"vocab[{i}] {w.get('id', '?')} {w.get('word', '?')}"
        miss = _missing(w, ("id", "word", "pos", "meaning", "example", "example_kr", "level", "topic"))
        if miss:
            errors.append(f"{tag}: 빠진 필드 {miss}")
            continue
        if w["id"] in ids:
            errors.append(f"{tag}: id 중복")
        ids.add(w["id"])
        key = w["word"].strip().lower()
        if key in seen:
            errors.append(f"{tag}: 단어 중복")
        seen.add(key)
        if w["level"] not in VOCAB_LEVELS:
            errors.append(f"{tag}: level 값 {w['level']!r}")
        if w["pos"] not in VOCAB_POS:
            errors.append(f"{tag}: pos 값 {w['pos']!r}")
        if w["topic"] not in VOCAB_TOPICS:
            errors.append(f"{tag}: topic 값 {w['topic']!r}")
        if not HANGUL.search(w["meaning"]) or not HANGUL.search(w["example_kr"]):
            errors.append(f"{tag}: 뜻/예문 해석에 한국어가 없습니다")
        if HANGUL.search(w["example"]):
            errors.append(f"{tag}: 영어 예문에 한글이 섞였습니다")
        stem = key.split()[0][:4]
        if stem not in w["example"].lower():
            warnings.append(f"{tag}: 예문에 표제어({stem}…)가 보이지 않음 — 불규칙 변화인지 확인")
    return errors, warnings


def validate_part5(data):
    errors, warnings = [], []
    qs = data.get("questions")
    if not isinstance(qs, list) or not qs:
        return ["questions 배열이 없습니다."], warnings
    ids, texts = set(), set()
    for i, q in enumerate(qs):
        tag = f"part5[{i}] {q.get('id', '?')}"
        miss = _missing(q, ("id", "question", "category", "level", "explanation"))
        if miss:
            errors.append(f"{tag}: 빠진 필드 {miss}")
            continue
        if q["id"] in ids:
            errors.append(f"{tag}: id 중복")
        ids.add(q["id"])
        norm = " ".join(q["question"].lower().split())
        if norm in texts:
            errors.append(f"{tag}: 같은 문제 중복")
        texts.add(norm)
        if q["question"].count(BLANK) != 1 or "____" in q["question"]:
            errors.append(f"{tag}: 빈칸(___)이 정확히 하나여야 합니다")
        choices = q.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            errors.append(f"{tag}: 보기는 4개여야 합니다")
        else:
            cleaned = [str(c).strip() for c in choices]
            if any(not c for c in cleaned):
                errors.append(f"{tag}: 빈 보기")
            if len({c.lower() for c in cleaned}) != 4:
                errors.append(f"{tag}: 보기 중복")
        ans = q.get("answer")
        if not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans <= 3:
            errors.append(f"{tag}: answer 는 0~3 정수 하나여야 합니다")
        if q["category"] not in P5_CATEGORIES:
            errors.append(f"{tag}: category 값 {q['category']!r}")
        if q["level"] not in P5_LEVELS:
            errors.append(f"{tag}: level 값 {q['level']!r}")
        if not HANGUL.search(q["explanation"]) or len(q["explanation"]) < 20:
            errors.append(f"{tag}: 해설이 너무 짧거나 한국어가 아닙니다")
        if HANGUL.search(q["question"]):
            errors.append(f"{tag}: 문제 문장에 한글이 섞였습니다")
        if isinstance(choices, list) and len(choices) == 4 and isinstance(ans, int) and 0 <= ans <= 3:
            if str(choices[ans]).strip().lower() not in q["explanation"].lower():
                warnings.append(f"{tag}: 해설에 정답 보기({choices[ans]})가 언급되지 않음")
    return errors, warnings


def validate_opic(data):
    errors, warnings = [], []
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        return ["topics 배열이 없습니다."], warnings
    tids, qids = set(), set()
    for i, t in enumerate(topics):
        tag = f"opic[{i}] {t.get('id', '?')}"
        miss = _missing(t, ("id", "name", "kind", "sample"))
        if miss:
            errors.append(f"{tag}: 빠진 필드 {miss}")
            continue
        if t["id"] in tids:
            errors.append(f"{tag}: 주제 id 중복")
        tids.add(t["id"])
        if t["kind"] not in OPIC_KINDS:
            errors.append(f"{tag}: kind 값 {t['kind']!r}")
        qs = t.get("questions") or []
        if len(qs) < 3:
            errors.append(f"{tag}: 질문이 3개 미만")
        for q in qs:
            qmiss = _missing(q, ("id", "q", "q_kr", "type", "tip"))
            if qmiss:
                errors.append(f"{tag} 질문 {q.get('id', '?')}: 빠진 필드 {qmiss}")
                continue
            if q["id"] in qids:
                errors.append(f"{tag} 질문 {q['id']}: id 중복")
            qids.add(q["id"])
            if q["type"] not in OPIC_TYPES:
                errors.append(f"{tag} 질문 {q['id']}: type 값 {q['type']!r}")
            if HANGUL.search(q["q"]) or not HANGUL.search(q["q_kr"]):
                errors.append(f"{tag} 질문 {q['id']}: 영어 질문/한국어 번역 확인")
        template = t.get("template") or []
        if len(template) < 3 or any(not str(s).strip() for s in template):
            errors.append(f"{tag}: 답변 틀은 3단계 이상")
        exprs = t.get("expressions") or []
        if len(exprs) < 5:
            errors.append(f"{tag}: 표현이 5개 미만")
        for e in exprs:
            if _missing(e, ("en", "ko")) or HANGUL.search(e.get("en", "")):
                errors.append(f"{tag}: 표현 형식 오류 {e}")
        if HANGUL.search(t["sample"]):
            errors.append(f"{tag}: 예시 답변에 한글이 섞였습니다")
    return errors, warnings


VALIDATORS = {
    "toeic_vocab.json": validate_vocab,
    "toeic_part5.json": validate_part5,
    "opic_bank.json": validate_opic,
}


def validate_all(data_dir=DATA_DIR):
    """{파일명: (errors, warnings, 항목 수)}"""
    report = {}
    for name, fn in VALIDATORS.items():
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            report[name] = ([f"{name} 파일이 없습니다."], [], 0)
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as e:
            report[name] = ([f"JSON 형식 오류: {e}"], [], 0)
            continue
        errors, warnings = fn(data)
        size = len(data.get("words") or data.get("questions") or data.get("topics") or [])
        report[name] = (errors, warnings, size)
    return report


def main():
    report = validate_all(sys.argv[1] if len(sys.argv) > 1 else DATA_DIR)
    failed = False
    for name, (errors, warnings, size) in report.items():
        print(f"{name}: {size}개, 오류 {len(errors)}, 경고 {len(warnings)}")
        for e in errors:
            print("  [오류]", e)
        for w in warnings:
            print("  [경고]", w)
        failed = failed or bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
