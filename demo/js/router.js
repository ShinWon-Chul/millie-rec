// 해시 → {page, params}. 라우트 표는 이 파일에만 둔다. 기본 "#/" = 쇼케이스(../.claude/rules/demo.md).
export const ROUTES = [
  ["", "showcase"], ["onboarding", "onboarding"], ["home", "home"], ["book/:id", "book"],
  ["reader/:id", "reader"], ["library", "library"], ["refresh", "refresh"], ["dashboard", "dashboard"],
];

/** 알 수 없는 해시는 쇼케이스로 떨어뜨린다(빈 화면 대신 랜딩). `:id`는 카탈로그 book_id라 Number. */
export function parse(hash = location.hash) {
  const path = hash.replace(/^#\/?/, "").replace(/\/$/, "");
  for (const [pat, page] of ROUTES) {
    const a = pat.split("/");
    const b = path.split("/");
    if (a.length !== b.length) continue;
    const params = {};
    let ok = true;
    a.forEach((seg, i) => {
      if (seg.startsWith(":")) params[seg.slice(1)] = Number(b[i]);
      else if (seg !== b[i]) ok = false;
    });
    if (ok) return { page, params };
  }
  return { page: "showcase", params: {} };
}

export function listen(onRoute) {
  addEventListener("hashchange", () => onRoute(parse()));
  onRoute(parse());
}
