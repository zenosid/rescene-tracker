# -*- coding: utf-8 -*-
"""
X 게시물 중 '리센느 소식'이 아닌 글을 가려내는 필터. 세 갈래로 나눕니다.

1) 유해 광고(harmful_keyword): 개인정보·계정 판매/해킹/토토/신분증·학생증 대여 등.
   사이트에는 표시하지 않고, 운영자 점검 목록(moderation_flags)에만 '내용 가린 채' 기록합니다.
2) 거래·대행 글(is_trading_or_spam): 포카 양도·판매/교환 요청, 대리찍사·사후 데이터 판매,
   팬싸컷 상담 등. 조용히 제외합니다.
3) 그 외(공식 MD 판매 안내, 판매량 기사, 팬 나눔 이벤트 등)는 그대로 둡니다.

실제 데이터(X 10,493건) 점검 기준: 약 35%가 1)·2)에 해당했습니다.
'판매·교환' 같은 단어만으로는 제외하지 않고, '판매합니다/교환 원해요'처럼
개인 거래를 뜻하는 동사형일 때만 제외합니다(예: "10만개 판매" 기사, "판매 안내" 공지는 유지).
"""
import re

_HARMFUL = re.compile(
    r"정보\s?판매|ㅈㅂㅍㅁ|ㅈㅂㄱㅎ|해킹|토토|도박|먹튀|"
    r"계정\s?(?:판매|대여|정보)|학생증\s?(?:대여|양도|판매|맞교환)|신분증\s?(?:대여|맞교환)|"
    r"명의\s?(?:대여|도용)|조건\s?만남",
    re.I,
)

_STRONG = re.compile(
    r"대리\s?찍사|대리\s?캠|댈\s?찍|사후\s?데이터|팝니다|삽니다|양도|분철|팬싸\s?컷|급처|택포|"
    r"페이팔|paypal|오픈\s?카톡|구해요|구합니다|매크로|성공초|공방\s?사녹|대리\s?티켓팅|댈구",
    re.I,
)
# 개인 거래를 뜻하는 동사형 (판매합니다 / 교환 원해요 / 대여 해드립니다 …)
_PERSONAL_DEAL = re.compile(
    r"(?:판매|교환|대여|나눔)\s?(?:합니다|합니당|해요|해여|해용|드립니다|해드립니다|해드려요|하실|원합니다|원해요|원해|구합|구해|구함|가능)|"
    r"교환\s?(?:o|⭕|희망)|싸게\s?팔",
    re.I,
)
# '판매/교환/대여' + 가격·거래 정황이 같이 있으면 개인 거래로 봄 (판매량 기사·공식 안내는 해당 없음)
_DEAL_WORD = re.compile(r"판매|교환|대여")
_PRICE_CUE = re.compile(
    r"\d{1,3}\.\d\b|\d+\s?만\s?원|가격|장당|일괄|하자|슬리브|탑로더|인증\s?가능|연락\s?주|디엠|\bDM\b|구하|보증금|대여비|(?<!\d)\d{1,2}\s?&gt;|1장\s?\d",
    re.I,
)
_OFFICIAL_CUE = re.compile(r"판매\s?안내|판매처|운영\s?시간|공식\s?(?:MD|굿즈|스토어)|사전\s?예약|예약\s?판매")
# 공식 공지의 '양도 불가/재판매 금지' 안내문구는 거래 글이 아니므로 판정 전에 지움
_NOTICE = re.compile(r"(?:양도|재판매|대리)[^.\n]{0,10}(?:불가|금지|제한|❌|X\b)")


def harmful_keyword(text):
    """유해 광고로 의심되면 걸린 표현(운영자 점검용), 아니면 None."""
    m = _HARMFUL.search(text or "")
    return re.sub(r"\s+", "", m.group(0)) if m else None


def is_trading_or_spam(text):
    cleaned = _NOTICE.sub("", text or "")
    if _STRONG.search(cleaned) or _PERSONAL_DEAL.search(cleaned) or _HARMFUL.search(cleaned):
        return True
    return bool(_DEAL_WORD.search(cleaned) and _PRICE_CUE.search(cleaned) and not _OFFICIAL_CUE.search(cleaned))
