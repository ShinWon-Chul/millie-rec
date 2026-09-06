"""03-UAT Test 9 gap — 재수집 대상 목록(millie_recollect_list) · --recollect 파일 파서
· collect(only=) 시그니처. 네트워크 0.
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"
BADGE_ID = "ffffffff00000003"


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BADGE_RECORD = {
    "millie_id": BADGE_ID,
    "status": 200,
    "title": "도슨트북",
    "subtitle": "종이책에서 읽던 지점 바로 이어읽기",
    "category": "인문",
    "shelf_count": 110000,
    "image_url": "https://img.millie.co.kr/x.jpg",
    "collected_at": "2026-09-05T02:00:00+00:00",
    "source": "best:0f1e2d3c4b5a6001",
    "url": f"https://www.millie.co.kr/v4/book/{BADGE_ID}",
}


def test_badge_title_rows_picks_only_badge_titles_sorted():
    """배지 제목 레코드만 (millie_id, source) 로, millie_id 사전순. source 없으면 'recollect'."""
    mod = _load("millie_recollect_list")
    records = [
        {"millie_id": "b", "title": "도슨트북", "source": "best:x"},
        {"millie_id": "a", "title": "무료"},
        {"millie_id": "c", "title": "불편한 편의점", "source": "sitemap"},
        {"millie_id": "d", "title": "종료 D-5", "source": "best:y"},
    ]
    assert mod.badge_title_rows(records) == [("a", "recollect"), ("b", "best:x"), ("d", "best:y")]


def test_recollect_list_main_writes_tsv(tmp_path, monkeypatch, capsys):
    """main() 이 JSONL 최신 줄 기준으로 `millie_id\\tsource` TSV 를 쓰고 건수를 출력한다."""
    mod = _load("millie_recollect_list")
    jsonl = tmp_path / "millie_pages.jsonl"
    jsonl.write_text(
        FIXTURE.read_text("utf-8").rstrip("\n")
        + "\n"
        + json.dumps(BADGE_RECORD, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "recollect_badge_titles.txt"
    monkeypatch.setattr(sys, "argv", ["x", "--jsonl", str(jsonl), "--out", str(out)])
    mod.main()
    assert out.exists()
    assert out.read_text(encoding="utf-8") == f"{BADGE_ID}\tbest:0f1e2d3c4b5a6001\n"
    assert "recollect targets=1" in capsys.readouterr().out


def test_read_recollect_parses_id_and_source(tmp_path):
    """--recollect 파일: 빈 줄·# 주석 무시, source 열 없으면 'recollect'."""
    mod = _load("collect_millie")
    assert hasattr(mod, "_read_recollect")
    path = tmp_path / "ids.txt"
    path.write_text("aaaa\tbest:x\n\n# c\nbbbb\n", encoding="utf-8")
    assert mod._read_recollect(path) == {"aaaa": "best:x", "bbbb": "recollect"}


def test_collect_accepts_only_keyword():
    """collect() 에 기본값 None 인 only 키워드가 있다 — 기본 경로는 무변경."""
    mod = _load("collect_millie")
    params = inspect.signature(mod.collect).parameters
    assert "only" in params
    assert params["only"].default is None
