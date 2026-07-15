"""PDF 단어장을 파싱해 learning.db 의 wordbook 테이블에 적재한다.

사용법:
    .venv\\Scripts\\python.exe scripts\\import_wordbook.py "C:\\path\\to\\단어장.pdf"

PDF 형식: 표 4열 (No. | 영단어 | 뜻 | 예문/해석) — 예문 셀은 영어 예문 줄 +
한국어 해석 줄로 구성. (pdfplumber 필요: pip install pdfplumber)

이미 단어장에 있는 단어(대소문자 무시)는 건너뛰므로 여러 번 실행해도 안전하다.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber 가 필요합니다:  .venv\\Scripts\\python.exe -m pip install pdfplumber")

HANGUL = re.compile(r"[가-힣]")


def split_example(cell):
    """예문 셀을 (영어 예문, 한국어 해석) 으로 나눈다 — 줄별 한글 포함 여부로 분류."""
    en_lines, kr_lines = [], []
    for line in (cell or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        (kr_lines if HANGUL.search(line) else en_lines).append(line)
    return " ".join(en_lines).strip(), " ".join(kr_lines).strip()


def parse_pdf(path):
    entries = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables({"text_x_tolerance": 2.5}):
                for row in table:
                    if not row or len(row) < 4:
                        continue
                    _, word, meaning, example_cell = (c or "" for c in row[:4])
                    word = " ".join(word.split())
                    meaning = " ".join(meaning.split())
                    if not word or word == "영단어" or not HANGUL.search(meaning):
                        continue  # 헤더/불량 행
                    example, example_kr = split_example(example_cell)
                    entries.append({"word": word, "meaning": meaning,
                                    "example": example, "example_kr": example_kr})
    return entries


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        sys.exit(f"파일을 찾을 수 없습니다: {pdf_path}")

    entries = parse_pdf(pdf_path)
    print(f"PDF 에서 {len(entries)}개 단어를 읽었습니다.")

    db.init_db()
    inserted = db.import_wordbook(entries)
    stats = db.wordbook_stats()
    print(f"새로 적재: {inserted}개 (중복 제외)")
    print(f"단어장 현황: 전체 {stats['total']}개 · 가져감 {stats['added']}개 · 남음 {stats['remaining']}개")
    print("이제 웹의 [단어] 페이지에서 '새 단어 가져오기'로 매일 조금씩 꺼내 외우세요.")
