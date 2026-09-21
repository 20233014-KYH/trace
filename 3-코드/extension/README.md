# Trace 브라우저 확장 (Chrome · MV3) — 뼈대

수집기가 못 보는 것 하나를 채운다: **브라우저 안에서 어느 탭(도메인)에 있는가.** 창 제목 키워드("Claude", "ChatGPT")로 어림하던 것을 도메인으로 정확히.
Learn 모드일 때만 맥락(AI 질문 · 답변 발췌 · 선택 텍스트)을 추가로 보낸다. Proof 모드에서는 탭 도메인만.

```
확장 ──POST 127.0.0.1:5077/event {type:"tab", domain, title}──▶ 수집기(bridge.py) ──▶ 체인 · batch · 서버
    ──POST 127.0.0.1:5077/context {items:[…]} (Learn 만)────▶ 수집기 ──▶ 서버 /sessions/{id}/context
```
확장은 서버 주소·세션 id·로그인을 모른다. 체인 순서를 정하는 곳은 수집기 하나뿐이라 "PC 체인 = 서버 재계산"이 유지된다.

## 설치 (개발 모드)
1. Chrome 주소창에 `chrome://extensions` → 오른쪽 위 **개발자 모드** 켜기
2. **압축해제된 확장 프로그램을 로드** → 이 폴더(`3-코드/extension`) 선택
3. 수집기를 켜고(`1_기록시작.bat`) 탭을 바꾸면 수집기 콘솔에 `tab  [ai] chatgpt.com …  (확장)` 이 찍힌다
4. 툴바의 Trace 아이콘 → 팝업에 모드·맥락 토글 상태

## 파일
| 파일 | 역할 | 상태 |
|---|---|---|
| `manifest.json` | 권한: tabs·storage · 다리(127.0.0.1:5077) · AI 사이트 5곳에 content.js | 뼈대 |
| `background.js` | 탭 활성화·주소 변경·창 포커스 → 도메인 → `/event`. 같은 도메인 연속은 한 번만 | **동작** (다리 테스트 완료) |
| `content.js` | AI 사이트에서 선택 텍스트 · 복사한 답변 · Enter 로 보낸 질문 → `/context`. 수집기가 Learn 모드일 때만 | 뼈대 — 사이트별 입력창 셀렉터 TODO |
| `popup.html/js` | 수집기 상태 · 모드 · 맥락 토글 표시 | 뼈대 |
| `domains.json` | 분류표 (수집기와 같은 파일) | 복사본 — 수집기 것을 기준으로 동기화 |

## 설계 원칙
- URL 전체·페이지 내용은 보내지 않는다. 탭 이벤트는 **도메인 + 제목 80자**.
- 맥락은 항목별 토글(수집기 `config.json`의 `learn_context`)을 따르고, 꺼진 항목은 content.js 가 아예 안 보낸다.
- 수집기가 꺼져 있으면 이벤트를 버린다 (확장이 따로 쌓지 않음 — 기록의 원본은 항상 수집기).

## 다음
- 사이트별 질문 입력창 셀렉터 (claude.ai · chatgpt.com · gemini) → `ai_question` 정확도
- `page` 맥락: 학습자료로 분류된 사이트의 제목·URL·체류 시간
- 7주차: 실사용 20분 테스트 → 오탐 확인 → domains.json 보정
