# -*- coding: utf-8 -*-
"""
콜라보·팝업 소식 추출 + 중복 묶기.

- detect_event(): 제목/요약에서 유형(팝업/콜라보/광고·모델/굿즈)과 브랜드 후보를 뽑음.
  브랜드·기간은 문장 패턴으로 "추정"한 값이라 화면에 추정으로 표시됩니다.
- 양도/판매/교환 같은 개인 거래 글은 제외합니다.
- cluster_events(): 같은 소식을 여러 매체/계정이 올린 경우 하나로 묶고 출처 링크를
  모두 보관합니다. DB의 원본 기록은 절대 지우지 않고, 화면용 데이터를 만들 때만 묶습니다.
"""
import re
from datetime import date as _date

from config import CHART_KEYWORDS, MEMBER_KEYWORDS, EVENT_BRAND_ALIASES

KIND_RULES = [
    ("팝업", [r"팝업", r"pop-?\s?up"]),
    ("콜라보", [r"콜라보", r"컬래버", r"컬라보", r"collab", r"협업"]),
    # '모델어워즈', '광고 효과' 같은 잡음을 피하려고 발탁/촬영 등과 함께 쓰인 표현만 인정
    ("광고·모델", [
        r"(?<!아시아)모델(?!어워즈)\s*(?:로|으로)?\s*(?:발탁|선정|낙점|발표|계약|출격|합류|등장)",
        r"(?:모델|뮤즈)(?:로)?\s*(?:발탁|선정|낙점)", r"광고\s*모델", r"광고\s*(?:촬영|공개|캠페인|영상)",
        r"앰버서더", r"엠버서더", r"\bcf\b", r"cf\s*촬영", r"새\s*얼굴",
    ]),
    ("굿즈", [r"굿즈", r"공식\s*md", r"\bmd\b", r"엠디", r"응원봉", r"키링"]),
]

# 개인 거래·잡담 글은 소식이 아니므로 제외
EXCLUDE_WORDS = [
    "양도", "판매", "팝니다", "삽니다", "구해요", "구합니다", "교환", "대리", "나눔",
    "분철", "공구", "급처", "택포", "미개봉 양도", "직캠", "후기", "대리수령",
    "어워즈", "시상식", "수상", "논란", "사과", "미개봉", "일괄", "커미션", "추천템",
    "브랜드평판", "브랜드 평판", "클랜원모집",
]

_GROUP_VARIANTS = [kw.lower() for kw in CHART_KEYWORDS] + ["르센느", "이센느"]

_X_SEP = r"[xX×✕]"
_BRAND_CHARS = r"[가-힣A-Za-z0-9&\.\-]{2,20}"
_BRAND_PATTERNS = [
    re.compile(r"(?:리센느|르센느|RESCENE)\s*" + _X_SEP + r"\s*(" + _BRAND_CHARS + r")", re.I),
    re.compile(r"(" + _BRAND_CHARS + r")\s*" + _X_SEP + r"\s*(?:리센느|르센느|RESCENE)", re.I),
    # "그레인온, 걸그룹 리센느 공식 모델 발탁" / "CU, 걸그룹 리센느 협업" 처럼 맨 앞 브랜드
    re.compile(r"^\W*(" + _BRAND_CHARS + r")\s*[,，]\s*(?:걸그룹\s*)?(?:리센느|르센느|RESCENE)", re.I),
]
_BRAND_STOP = {
    "리센느", "르센느", "이센느", "rescene", "걸그룹", "아이돌", "신인", "그룹", "공식",
    "서울", "성수", "성수동", "홍대", "더현대", "현대백화점", "백화점", "오픈", "개최",
    "진행", "첫", "신규", "최초", "단독", "한정", "팬들", "팬", "리센느가", "리센느의",
    "브랜드", "화장품", "패션", "뷰티", "새", "새로운", "글로벌", "공식", "온라인", "오프라인",
    "멤버", "멤버들", "리마인", "광고", "모델", "화보", "굿즈", "이벤트", "스토어", "컬래버레이션",
}
_PERIOD_RE = re.compile(
    r"(\d{1,2}월\s*\d{1,2}일(?:\s*[~\-부터]+\s*(?:\d{1,2}월\s*)?\d{1,2}일(?:까지)?)?)"
)


def _norm(text):
    return re.sub(r"[^\w가-힣]+", "", text or "").lower()


def is_our_group(text):
    """그룹명, 또는 한글에 붙어있지 않은 단독 멤버 이름(예: '메이크업'의 '메이'는 제외)."""
    text = text or ""
    lowered = text.lower()
    if any(v in lowered for v in _GROUP_VARIANTS):
        return True
    for name in MEMBER_KEYWORDS.keys():
        if re.search(r"(?<![가-힣A-Za-z])" + re.escape(name) + r"(?![가-힣A-Za-z])", text):
            return True
    return False


_KIND_RES = [(k, [re.compile(p, re.I) for p in pats]) for k, pats in KIND_RULES]


def detect_kind(text):
    text = text or ""
    for kind, pats in _KIND_RES:
        if any(p.search(text) for p in pats):
            return kind
    return None


def is_trading_post(text):
    return any(w in (text or "") for w in EXCLUDE_WORDS)


_ALIAS_RES = []
for _canon, _aliases in EVENT_BRAND_ALIASES.items():
    for _al in _aliases:
        if re.fullmatch(r"[A-Za-z0-9 ]+", _al):
            _pat = r"(?<![A-Za-z0-9])" + re.escape(_al) + r"(?![A-Za-z0-9])"
        else:
            _pat = re.escape(_al)
        _ALIAS_RES.append((_canon, re.compile(_pat, re.I)))


def match_aliases(text):
    """제목에 등장한 대표 브랜드 이름들(중복 없이, 등장 순서 무관)."""
    found = []
    for canon, pat in _ALIAS_RES:
        if canon not in found and pat.search(text or ""):
            found.append(canon)
    return found


def match_alias(text):
    """제목의 대표 브랜드. 둘 이상이면 'A × B'처럼 합쳐서(예: 나랑드사이다 × 카사베르디)
    같은 조합의 기사끼리만 묶이게 함. 없으면 ''."""
    return " × ".join(sorted(match_aliases(text)))


_BAD_BRAND_PARTS = ("하세요", "습니다", "합니다", "입니다", "@", "http", "리센느", "rescene")


def _valid_brand(cand):
    if not (2 <= len(cand) <= 12) or cand.isdigit():
        return False
    low = cand.lower()
    if any(b in low for b in _BAD_BRAND_PARTS):
        return False
    if cand in MEMBER_KEYWORDS or _norm(cand) in {_norm(s) for s in _BRAND_STOP}:
        return False
    return True


def extract_brand(text):
    for pat in _BRAND_PATTERNS:
        for m in pat.finditer(text or ""):
            cand = m.group(1).strip(".-&")
            if not _valid_brand(cand):
                continue
            return cand
    return ""


def extract_period(text):
    m = _PERIOD_RE.search(text or "")
    return m.group(1) if m else ""


def detect_event(title, snippet=""):
    """이벤트 후보면 dict, 아니면 None. 판정은 제목 기준(요약은 보조)."""
    title = title or ""
    if not is_our_group(title) and not is_our_group(snippet):
        return None
    if is_trading_post(title):
        return None
    kind = detect_kind(title)
    if kind is None:
        return None
    # 별칭은 제목만 봅니다(요약에는 다른 브랜드 이야기가 섞여 있는 경우가 많음).
    alias = match_alias(title)
    multi = " × " in alias
    brand = alias or extract_brand(title)
    return {
        "kind": kind,
        "brand": brand,
        "brand_known": bool(alias),
        "multi": multi,
        "period_text": extract_period(title) or extract_period(snippet),
    }


# ── 중복 묶기 ────────────────────────────────────────────────
_SUFFIX_RE = re.compile(r"\s*[-–—|]\s*[^-–—|]{1,20}$")
_FILLER = {"리센느", "르센느", "rescene", "팝업스토어", "팝업", "콜라보", "컬래버", "오픈", "개최", "진행", "공개", "협업"}


def _tokens(title):
    base = _SUFFIX_RE.sub("", title or "")
    toks = re.findall(r"[가-힣A-Za-z0-9]{2,}", base.lower())
    return {t for t in toks if t not in _FILLER}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _days_apart(d1, d2):
    try:
        return abs((_date.fromisoformat(d1[:10]) - _date.fromisoformat(d2[:10])).days)
    except ValueError:
        return 9999


_GENERIC = {
    "발탁", "모델", "앰버서더", "엠버서더", "뮤즈", "새얼굴", "공개", "출시", "캠페인", "브랜드", "걸그룹",
    "아이돌", "리센느", "rescene", "팝업", "콜라보", "협업", "굿즈", "광고", "촬영", "이벤트", "화보",
    "프로젝트", "한정판", "에디션", "서울", "전개", "진행", "확대", "시작", "발표", "선정", "속보", "단독",
}
_MEMBER_TOKENS = {n.lower() for n in MEMBER_KEYWORDS.keys()} | {
    kw.lower() for kws in MEMBER_KEYWORDS.values() for kw in kws
}
_RANK_NEWS, _RANK_BLOG, _RANK_OTHER = 1, 2, 3


def _source_rank(m):
    if m.get("is_manual"):
        return 0
    name = m.get("source_name", "")
    if "뉴스" in name:
        return _RANK_NEWS
    if "블로그" in name:
        return _RANK_BLOG
    return _RANK_OTHER


def _sig_tokens(title, df, total):
    out = set()
    for t in _tokens(title):
        if len(t) < 3 or t in _GENERIC or t in _MEMBER_TOKENS:
            continue
        if df.get(t, 0) / max(total, 1) > 0.10:
            continue  # 너무 흔한 단어는 같은 소식의 증거가 못 됨
        out.add(t)
    return out


def _same_event(c, m, m_sig):
    if c["kind"] != m["kind"]:
        return False
    gap = _days_apart(c["date"], m["date"])
    ba, bb = _norm(c["brand"]), _norm(m.get("brand"))
    if ba and bb:
        # 둘 다 브랜드를 알면 같을 때만 (팝업은 몇 주씩 이어지므로 45일)
        return ba == bb and gap <= 45
    # 한쪽이라도 브랜드를 모르면: 가까운 날짜 + 흔치 않은 단어(브랜드명 등)를 공유할 때만.
    # 한쪽만 브랜드를 알면 오해 병합을 막으려고 공유 단어 2개 이상을 요구
    need = 2 if (ba or bb) else 1
    return gap <= 14 and len(c["_sig"] & m_sig) >= need


def cluster_events(mentions):
    """
    mentions: dict 리스트(date, kind, brand, title, link, source_name, period_text, is_manual).
    반환: 날짜 최신순 이벤트 리스트. 각 이벤트는 sources(출처 링크 목록)를 가짐.
    묶는 것은 화면용 데이터에서만이고 원본 기록은 그대로 남습니다.
    대표 제목은 수동 등록 > 뉴스 > 블로그 > 그 외(X·카페) 순으로 고릅니다.
    """
    from collections import Counter

    df = Counter()
    for m in mentions:
        df.update(_tokens(m["title"]))
    total = len(mentions)

    ordered = sorted(mentions, key=lambda m: (m["date"], _source_rank(m)))
    clusters = []
    for m in ordered:
        m_sig = _sig_tokens(m["title"], df, total)
        for c in clusters:
            if _same_event(c, m, m_sig):
                c["_mentions"].append(m)
                c["_sig"] |= m_sig
                if not c["brand"] and m.get("brand"):
                    c["brand"] = m["brand"]
                break
        else:
            clusters.append({"kind": m["kind"], "date": m["date"], "brand": m.get("brand", ""),
                             "_sig": set(m_sig), "_mentions": [m]})

    # 나중에 브랜드가 확인되어 같은 브랜드가 된 묶음끼리 한 번 더 합침
    merged = []
    for c in clusters:
        for t in merged:
            if (t["kind"] == c["kind"] and _norm(t["brand"]) and _norm(t["brand"]) == _norm(c["brand"])
                    and _days_apart(t["date"], c["date"]) <= 45):
                t["_mentions"].extend(c["_mentions"])
                t["date"] = min(t["date"], c["date"])
                break
        else:
            merged.append(c)
    clusters = merged

    result = []
    for c in clusters:
        ms = sorted(c["_mentions"], key=lambda m: (_source_rank(m), m["date"]))
        rep = ms[0]
        seen, sources = set(), []
        for m in ms:
            if m.get("link") and m["link"] not in seen:
                seen.add(m["link"])
                sources.append({"name": m["source_name"], "link": m["link"], "title": m["title"]})
        result.append({
            "date": min(m["date"] for m in ms),
            "kind": c["kind"],
            "brand": c["brand"],
            "title": rep["title"],
            "period_text": next((m["period_text"] for m in ms if m.get("period_text")), ""),
            "note": rep.get("note", ""),
            "is_manual": any(m.get("is_manual") for m in ms),
            "sources": sources,
            "source_count": len(sources),
        })
    result.sort(key=lambda e: e["date"], reverse=True)
    return result
