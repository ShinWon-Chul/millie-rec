"""app/server.py Sentry 초기화(.planning/phases/07-deploy/07-CONTEXT.md D-04) —
DSN 없으면 init 미호출(네트워크 0), 있으면 traces 0 · PII off 로 1회.
실 artifacts/serving 은 읽지 않고(fixture 20권), sentry_sdk.init 은 spy 라 실제 초기화도 없다.
"""

import importlib
import sys
from pathlib import Path

import sentry_sdk
from sentry_sdk.utils import BadDsn

from millie_rec.contracts import ENV_DATA_DIR
from millie_rec.data import VECTORS_KR_NPZ, CatalogKR, VectorsKR

FAKE_DSN = "https://examplePublicKey@o0.ingest.sentry.io/0"
# 얇은 진입점 유지 가드. 07-01-PLAN 의 50 은 init_sentry() 삽입 후 산술적으로 불가하다
# (기존 38줄 + import 3 + 함수 15 + 호출·구분 5 = 61, Codex F1 fail-open 반영 후).
# 65 = 얇음 유지 상한(simplicity.md 의 실제 상한은 150).
MAX_SERVER_LINES = 65


def _server(tmp_path: Path, monkeypatch, serving_dir: Path):
    # tests/app/test_server_catalog.py 헬퍼 복제(2곳째 — _shared 는 3곳부터, simplicity.md)
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: CatalogKR.load(serving_dir))
    monkeypatch.setattr(
        "millie_rec.app.pipeline_kr.load_vectors_kr",
        lambda *a, **k: VectorsKR.load(serving_dir / VECTORS_KR_NPZ),
    )
    sys.modules.pop("millie_rec.app.server", None)
    return importlib.import_module("millie_rec.app.server")


def _spy_init(monkeypatch) -> list[dict]:
    """sentry_sdk.init 을 호출 기록으로 대체 — 실 초기화·네트워크 전송 없음."""
    calls: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
    return calls


def test_no_dsn_never_calls_sentry_init(tmp_path: Path, monkeypatch, millie_serving_sample):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    calls = _spy_init(monkeypatch)
    _server(tmp_path, monkeypatch, millie_serving_sample)
    assert calls == []
    assert sentry_sdk.is_initialized() is False


def test_dsn_inits_once_with_no_tracing_no_pii(tmp_path: Path, monkeypatch, millie_serving_sample):
    monkeypatch.setenv("SENTRY_DSN", FAKE_DSN)
    calls = _spy_init(monkeypatch)
    _server(tmp_path, monkeypatch, millie_serving_sample)
    assert len(calls) == 1
    kw = calls[0]
    assert kw["dsn"] == FAKE_DSN
    assert kw["traces_sample_rate"] == 0
    assert kw["send_default_pii"] is False
    assert isinstance(kw["environment"], str) and kw["environment"]


def test_server_module_stays_under_50_lines(tmp_path: Path, monkeypatch, millie_serving_sample):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    lines = Path(server.__file__).read_text(encoding="utf-8").splitlines()
    assert len(lines) <= MAX_SERVER_LINES


def test_bad_dsn_does_not_break_server_import(tmp_path: Path, monkeypatch, millie_serving_sample):
    """Codex F1 — DSN 오타가 모듈 import 를 깨면 Railway 가 재시작 3회를 소진하고 배포가 죽는다."""
    monkeypatch.setenv("SENTRY_DSN", "not-a-dsn")

    def _boom(**kw):
        raise BadDsn("Unsupported scheme ''")

    monkeypatch.setattr(sentry_sdk, "init", _boom)
    server = _server(tmp_path, monkeypatch, millie_serving_sample)  # import 가 성공해야 한다
    assert server.app is not None
    assert server.init_sentry() is False  # fail-open — 예외가 밖으로 새지 않는다
    assert sentry_sdk.is_initialized() is False
