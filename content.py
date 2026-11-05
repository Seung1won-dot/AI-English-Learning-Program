"""
content.py — 학습 콘텐츠(data/*.json) 읽기

  toeic_vocab.json : 토익 빈출 어휘 (뜻·품사·예문·수준·주제)
  toeic_part5.json : 토익 Part 5 스타일 문법·어휘 문제 (정답·해설·유형·난이도)
  opic_bank.json   : 오픽 주제별 질문 은행 + 답변 틀 + 표현 + 예시 답변

모두 직접 작성한 오리지널 문제다. 형식 검사는 scripts/validate_content.py.
파일은 앱 시작 후 처음 쓸 때 한 번 읽어 메모리에 둔다(읽기 전용).
"""

import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

P5_CATEGORIES = ("품사", "동사 시제·태", "수 일치", "대명사", "전치사", "접속사",
                 "관계사", "준동사", "비교", "어휘")
P5_LEVEL_LABEL = {"easy": "기초", "medium": "중급", "hard": "고급"}
VOCAB_LEVELS = ("600", "800", "900")
OPIC_KINDS = ("기본", "설문", "돌발", "롤플레이")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def vocab():
    return tuple(_load("toeic_vocab.json")["words"])


@lru_cache(maxsize=None)
def vocab_by_id():
    return {w["id"]: w for w in vocab()}


@lru_cache(maxsize=None)
def part5():
    return tuple(_load("toeic_part5.json")["questions"])


@lru_cache(maxsize=None)
def part5_by_id():
    return {q["id"]: q for q in part5()}


@lru_cache(maxsize=None)
def opic_topics():
    return tuple(_load("opic_bank.json")["topics"])


def opic_topic(key):
    """주제 id 또는 이름으로 찾는다. 없으면 None."""
    key = (key or "").strip()
    for t in opic_topics():
        if key in (t["id"], t["name"]):
            return t
    return None


def public_question(q):
    """정답·해설을 뺀 문제 (모의 테스트 출제용)."""
    return {k: q[k] for k in ("id", "question", "choices", "category", "level")}
