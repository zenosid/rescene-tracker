# 포토카드 발매 기록 기능 추가 가이드

hallyusuperstore.com 판매 목록(텍스트 정보만, 이미지 제외)을 기준으로
29건의 포토카드 발매 기록을 정리했습니다. (전체 130건 중 최신 30건 —
페이지 1개 분량. 더 필요하시면 2~5페이지도 확인해서 추가해드릴 수 있습니다.)

## 1. config.py — 맨 아래에 추가
`config_addition.py` 내용을 그대로 붙여넣어주세요.

## 2. build_site_data.py

**(a) import에 추가**
```python
from config import (..., PHOTOCARD_RELEASES)
```

**(b) data.js 출력 딕셔너리에 추가**
```python
"photocard_releases": PHOTOCARD_RELEASES,
```

## 3. docs/app.js
`app_addition.js` 내용 중 `renderPhotocards` 함수만 추가해주세요
(맨 위 `escapeHtml` 줄은 이미 app.js에 있으니 그건 빼고 복사).

탭 클릭 핸들러에 추가:
```javascript
if (btn.dataset.tab === "photocards") renderPhotocards();
```

## 4. docs/index.html

**(a) 네비게이션 탭 버튼**
```html
<button class="tab-btn" data-tab="photocards">🎴 포토카드</button>
```

**(b) 뷰 섹션**
```html
<div class="view" id="view-photocards">
  <div class="card" style="padding:14px 20px; margin-bottom:20px;">
    <span style="font-size:12.5px; color:var(--text-muted);">
      🎴 hallyusuperstore.com 판매 기록 기준 포토카드 발매 이력입니다
      (텍스트 정보만, 이미지는 포함하지 않습니다).
    </span>
  </div>
  <div id="photocardContent"></div>
</div>
```

**(c) CSS**: `css_addition.css` 내용을 `<style>` 태그 안에 추가

## 적용 후
```powershell
python build_site_data.py
git add .
git commit -m "add photocard release history (text info only, from hallyusuperstore listing)"
git push
```
