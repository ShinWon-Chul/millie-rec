"""아키텍처 경계를 정적으로 검사한다 (.claude/rules/architecture.md).

실패하면 규칙을 어긴 것이다 — 이 테스트가 아니라 코드를 고친다.
예외가 필요하면 Advisor 가 PROGRESS.md 에 기록한 뒤 ALLOWED_EXCEPTIONS 에 추가한다.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "millie_rec"
PKG = "millie_rec"
SLICES = {"data", "retrieval", "ranking", "reranking", "evaluation", "serving"}
ALLOWED_EXCEPTIONS: set[tuple[str, str]] = set()  # (파일 상대경로, import 대상)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            out.append(node.module)
    return [m for m in out if m == PKG or m.startswith(PKG + ".")]


def _violations() -> list[str]:
    bad: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC)
        top = rel.parts[0] if len(rel.parts) > 1 else None  # 슬라이스 이름 (contracts.py 는 None)
        for mod in _imports(path):
            if (str(rel), mod) in ALLOWED_EXCEPTIONS:
                continue
            parts = mod.split(".")
            target = parts[1] if len(parts) > 1 else None
            if target == "app" and top != "app":
                bad.append(f"{rel}: '{mod}' — 누구도 app 을 import 하지 않는다")
            elif top in SLICES and target in SLICES and target != top:
                bad.append(f"{rel}: '{mod}' — 슬라이스는 contracts 와 자기 내부만 import 한다")
            elif top == "app" and target in SLICES and len(parts) > 2:
                bad.append(f"{rel}: '{mod}' — app 은 공개 표면(millie_rec.{target})만 import 한다")
    return bad


def test_slice_boundaries() -> None:
    assert _violations() == []


def test_no_layer_folders_inside_slices() -> None:
    forbidden = {
        "domain",
        "application",
        "infrastructure",
        "api",
        "ui",
        "utils",
        "common",
        "helpers",
        "shared",
    }
    found = [p for p in SRC.rglob("*") if p.is_dir() and p.name in forbidden]
    assert found == [], f"계층/공용 폴더 금지: {found}"


def test_contracts_has_no_logic() -> None:
    """contracts.py 는 정의만: 최상위에 함수 정의·I/O 호출이 없어야 한다."""
    tree = ast.parse((SRC / "contracts.py").read_text(encoding="utf-8"))
    top_funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert top_funcs == [], f"contracts.py 에 함수 정의 금지: {top_funcs}"
