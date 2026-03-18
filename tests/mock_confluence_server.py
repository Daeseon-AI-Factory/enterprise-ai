"""
Mock Confluence Server — 실제 Confluence 없이 연동 테스트용.

사용법:
    python tests/mock_confluence_server.py

브라우저:  http://localhost:9090   (Confluence UI)
API:       http://localhost:9090/rest/api/...

UI에서 입력:
    URL:        http://localhost:9090
    사용자명:   test@company.internal
    API 토큰:   any-value-works
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="Mock Confluence Server")

# ── Data ─────────────────────────────────────────────────

SPACES = [
    {"key": "DEV", "name": "개발팀 위키",    "type": "global", "icon": "💻"},
    {"key": "HR",  "name": "인사팀 문서",    "type": "global", "icon": "👥"},
    {"key": "MES", "name": "MES/WMS 운영",  "type": "global", "icon": "🏭"},
    {"key": "IT",  "name": "IT 지원 가이드","type": "global", "icon": "🔧"},
]

PAGES = {
    "DEV": [
        {
            "id": "10001", "title": "온보딩 가이드",
            "body": {"storage": {"value": """
                <h2>신규 입사자 온보딩 가이드</h2>
                <p>개발팀에 오신 것을 환영합니다. 첫 2주간 해야 할 일을 안내합니다.</p>
                <h3>1주차</h3>
                <ul>
                  <li>사내 VPN 설정 — IT팀 내선 1234</li>
                  <li>GitHub 조직 초대 — 팀장에게 요청</li>
                  <li>개발 환경 구성 — /wiki/DEV/dev-setup 참고</li>
                  <li>Jira 접근 권한 요청</li>
                </ul>
                <h3>2주차</h3>
                <ul>
                  <li>첫 PR 제출 — 작은 버그 수정으로 시작</li>
                  <li>코드 리뷰 프로세스 숙지</li>
                  <li>스프린트 회의 참여 (매주 월요일 10시)</li>
                </ul>
            """}},
            "version": {"number": 5, "when": "2024-11-01T09:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "onboarding"}]}},
        },
        {
            "id": "10002", "title": "배포 프로세스",
            "body": {"storage": {"value": """
                <h2>배포 프로세스 가이드</h2>
                <p>운영 배포는 매주 수요일 오후 2시에 진행합니다.</p>
                <h3>배포 전 체크리스트</h3>
                <ol>
                  <li>develop 브랜치 테스트 통과 확인</li>
                  <li>QA 팀 승인 (Jira 티켓 상태: QA완료)</li>
                  <li>DB 마이그레이션 스크립트 준비</li>
                  <li>롤백 플랜 문서화</li>
                </ol>
                <h3>배포 명령어</h3>
                <pre>git checkout main
git merge develop
./deploy.sh production</pre>
                <h3>배포 후</h3>
                <p>모니터링 대시보드 30분 감시. 오류율 1% 초과 시 즉시 롤백.</p>
            """}},
            "version": {"number": 12, "when": "2024-12-15T14:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "devops"}]}},
        },
        {
            "id": "10003", "title": "코드 리뷰 가이드",
            "body": {"storage": {"value": """
                <h2>코드 리뷰 가이드</h2>
                <h3>리뷰어 기준</h3>
                <ul>
                  <li>PR 크기: 변경 파일 10개 이하, 라인 300줄 이하 권장</li>
                  <li>응답 시간: 영업일 기준 1일 이내</li>
                  <li>승인 기준: 최소 1명 Approve 필요</li>
                </ul>
                <h3>리뷰 시 확인 항목</h3>
                <ul>
                  <li>비즈니스 로직 정확성</li>
                  <li>예외 처리 및 에러 핸들링</li>
                  <li>SQL 인젝션 등 보안 취약점</li>
                  <li>테스트 코드 존재 여부</li>
                  <li>네이밍 컨벤션 준수</li>
                </ul>
                <h3>코멘트 규칙</h3>
                <p><b>Nit:</b> 사소한 의견 (머지 블로킹 아님) &nbsp;|&nbsp; <b>Must:</b> 반드시 수정 &nbsp;|&nbsp; <b>Question:</b> 질문</p>
            """}},
            "version": {"number": 3, "when": "2025-01-10T11:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "process"}]}},
        },
    ],

    "HR": [
        {
            "id": "20001", "title": "연차 사용 규정",
            "body": {"storage": {"value": """
                <h2>연차 사용 규정</h2>
                <h3>연차 발생 기준</h3>
                <ul>
                  <li>입사 1년 미만: 매월 1일 발생 (최대 11일)</li>
                  <li>입사 1년 이상: 15일 (이후 2년마다 1일 추가, 최대 25일)</li>
                </ul>
                <h3>신청 방법</h3>
                <p>ERP 시스템 &gt; 근태관리 &gt; 연차신청에서 최소 3일 전 신청.</p>
                <h3>소멸 기준</h3>
                <p>미사용 연차는 12월 31일 소멸. 회사 귀책사유 미사용분은 수당 지급.</p>
            """}},
            "version": {"number": 2, "when": "2024-03-01T09:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "hr"}]}},
        },
    ],

    "MES": [
        {
            "id": "30001", "title": "생산 지시 처리 프로세스",
            "body": {"storage": {"value": """
                <h2>생산 지시 처리 프로세스</h2>
                <p>MES에서 생산 지시(Work Order)를 처리하는 표준 절차입니다.</p>
                <h3>생산 지시 상태 흐름</h3>
                <p><b>대기</b> → <b>확정</b> → <b>작업 시작</b> → <b>작업 중</b> → <b>완료</b> → <b>마감</b></p>
                <h3>처리 절차</h3>
                <ol>
                  <li>ERP에서 생산 계획 수신 (자동 연동, 1시간 주기)</li>
                  <li>자재 가용성 확인 — 부족 시 구매 요청 자동 생성</li>
                  <li>설비 배정 — 가용 설비 우선, 병목 설비는 스케줄러 참고</li>
                  <li>작업자 배정 — 자격증 보유자 우선 배정</li>
                  <li>작업 시작 → 바코드 스캔으로 실적 입력</li>
                  <li>완료 수량 확정 → 품질 검사 요청 자동 발행</li>
                </ol>
                <h3>긴급 지시 처리</h3>
                <p>우선순위 1 설정 시 현재 작업 뒤에 즉시 삽입. 생산팀장 승인 필요.</p>
            """}},
            "version": {"number": 8, "when": "2025-02-10T08:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "mes"}, {"name": "production"}]}},
        },
        {
            "id": "30002", "title": "창고 입출고 규칙",
            "body": {"storage": {"value": """
                <h2>창고 입출고 규칙 (WMS)</h2>
                <h3>입고 프로세스</h3>
                <ol>
                  <li>발주서(PO) 기준 입고 예정 목록 확인</li>
                  <li>실물 수량 검수 — 발주 수량 대비 오차 ±3% 허용</li>
                  <li>바코드/QR 스캔으로 WMS 입고 등록</li>
                  <li>로케이션 자동 배정 (FIFO 기준, 중량/부피 제한 준수)</li>
                  <li>불량/파손 시 반품 처리 — 품질팀 승인 후 반품 지시 생성</li>
                </ol>
                <h3>출고 프로세스</h3>
                <ol>
                  <li>생산 지시 or 출하 지시 기준 피킹 목록 생성</li>
                  <li>피킹 — 로케이션 최적 경로 순서로 출력</li>
                  <li>스캔 검증 후 출고 확정</li>
                  <li>재고 자동 차감 및 ERP 연동</li>
                </ol>
                <h3>재고 실사</h3>
                <p>월 1회 전수 실사, 주 1회 순환 실사(ABC 분류 기준). 오차 발생 시 창고팀장 보고.</p>
            """}},
            "version": {"number": 6, "when": "2025-01-20T09:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "wms"}]}},
        },
        {
            "id": "30003", "title": "품질 검사 기준",
            "body": {"storage": {"value": """
                <h2>품질 검사 기준</h2>
                <h3>검사 종류</h3>
                <ul>
                  <li>수입 검사: 외부 구매 자재 입고 시</li>
                  <li>공정 검사: 주요 공정 완료 후</li>
                  <li>완제품 검사: 생산 완료 후 출하 전</li>
                </ul>
                <h3>샘플링 기준 (AQL)</h3>
                <ul>
                  <li>로트 크기 1~50: 전수 검사</li>
                  <li>로트 크기 51~500: AQL 1.0 (샘플 13개)</li>
                  <li>로트 크기 501~: AQL 1.0 (샘플 32개)</li>
                </ul>
                <h3>불합격 처리</h3>
                <p>불합격 시 빨간 태그 부착 후 격리 보관소 이동. 처리: 재작업 / 특채 / 폐기 — 품질팀장 결재.</p>
                <h3>검사 성적서</h3>
                <p>MES에서 자동 생성, PDF 저장. 고객사 요청 시 즉시 제출.</p>
            """}},
            "version": {"number": 4, "when": "2025-03-01T10:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "quality"}]}},
        },
    ],

    "IT": [
        {
            "id": "40001", "title": "장애 대응 매뉴얼",
            "body": {"storage": {"value": """
                <h2>IT 장애 대응 매뉴얼</h2>
                <h3>장애 등급</h3>
                <ul>
                  <li><b>P1 (Critical):</b> 전체 서비스 중단 — 15분 내 대응, 즉시 임원 보고</li>
                  <li><b>P2 (Major):</b> 주요 기능 장애 — 1시간 내 대응</li>
                  <li><b>P3 (Minor):</b> 일부 기능 저하 — 4시간 내 대응</li>
                </ul>
                <h3>대응 절차</h3>
                <ol>
                  <li>장애 감지 (모니터링 알람 or 사용자 신고)</li>
                  <li>담당자 즉시 확인 및 초기 영향 범위 파악</li>
                  <li>장애 대응 채널 개설 (Slack #incident-YYYYMMDD)</li>
                  <li>원인 파악 → 임시 조치 → 서비스 복구</li>
                  <li>복구 완료 후 사후 보고서 작성 (24시간 내)</li>
                </ol>
                <h3>주요 연락처</h3>
                <ul>
                  <li>인프라팀: 내선 2001 &nbsp;|&nbsp; DB팀: 내선 2002 &nbsp;|&nbsp; 보안팀: 내선 2003</li>
                </ul>
            """}},
            "version": {"number": 7, "when": "2025-02-01T09:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "incident"}]}},
        },
        {
            "id": "40002", "title": "DB 접근 권한 신청",
            "body": {"storage": {"value": """
                <h2>DB 접근 권한 신청 가이드</h2>
                <h3>권한 종류</h3>
                <ul>
                  <li><b>READ:</b> 조회 전용 (기본 신청 가능)</li>
                  <li><b>READ/WRITE:</b> 데이터 변경 (팀장 승인 필요)</li>
                  <li><b>DBA:</b> DB 관리자 권한 (CTO 승인 필요)</li>
                </ul>
                <h3>신청 절차</h3>
                <ol>
                  <li>Jira IT 프로젝트에서 "DB 권한 신청" 템플릿으로 티켓 생성</li>
                  <li>필수 입력: DB명, 스키마명, 권한 종류, 사용 목적, 사용 기간</li>
                  <li>팀장 승인 → DB팀 처리 (영업일 2일 이내)</li>
                  <li>계정 정보 이메일 수신 (임시 비밀번호, 최초 접속 시 변경 필수)</li>
                </ol>
                <h3>보안 규칙</h3>
                <ul>
                  <li>운영 DB 접근 시 반드시 VPN 사용</li>
                  <li>계정 공유 금지 — 위반 시 즉시 권한 회수</li>
                  <li>대량 데이터 조회 (10만 건 이상) 시 DBA 사전 문의</li>
                </ul>
            """}},
            "version": {"number": 5, "when": "2025-01-15T11:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "db"}]}},
        },
        {
            "id": "40003", "title": "사내 시스템 계정 신청",
            "body": {"storage": {"value": """
                <h2>사내 시스템 계정 신청</h2>
                <h3>신청 대상 시스템</h3>
                <ul>
                  <li>ERP (SAP): 입사 시 자동 생성, 권한은 별도 신청</li>
                  <li>MES: 현장 작업자 — 생산팀장 승인 / 개발자 — IT팀 직접 처리</li>
                  <li>WMS: 물류팀장 승인 후 IT팀 처리</li>
                  <li>Confluence/Jira: 입사 시 자동 생성</li>
                  <li>GitHub: 개발팀 한정, 팀장 요청 시 즉시 처리</li>
                </ul>
                <h3>퇴사 시 계정 처리</h3>
                <p>퇴사일 당일 모든 계정 자동 비활성화. HR팀이 퇴사 예정 3일 전 IT팀에 통보.</p>
                <h3>비밀번호 정책</h3>
                <ul>
                  <li>최소 12자, 대소문자 + 숫자 + 특수문자 포함</li>
                  <li>90일마다 변경 필수, 이전 5개 재사용 불가</li>
                </ul>
            """}},
            "version": {"number": 3, "when": "2025-02-20T10:00:00Z"},
            "metadata": {"labels": {"results": [{"name": "account"}]}},
        },
    ],
}

# ── HTML helpers ─────────────────────────────────────────

_NAV = """<nav style="background:#0052cc;padding:0 24px;display:flex;align-items:center;height:48px">
  <a href="/" style="color:white;font-weight:700;font-size:18px;text-decoration:none;letter-spacing:-0.5px">Confluence</a>
  <span style="color:rgba(255,255,255,.5);margin:0 12px">|</span>
  <span style="color:rgba(255,255,255,.7);font-size:13px">Mock Server — test@company.internal</span>
</nav>"""

_STYLE = """<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f5f7;color:#172b4d}
  a{color:#0052cc;text-decoration:none} a:hover{text-decoration:underline}
  h2{font-size:20px;margin:0 0 16px} h3{font-size:15px;margin:20px 0 8px;color:#172b4d}
  p,li{line-height:1.7;font-size:14px}
  ul,ol{padding-left:20px} li{margin:4px 0}
  pre{background:#f4f5f7;border:1px solid #dfe1e6;border-radius:4px;padding:12px 16px;font-size:13px;overflow-x:auto}
  b{color:#172b4d}
</style>"""


# ── UI routes ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    space_cards = ""
    for s in SPACES:
        pages = PAGES.get(s["key"], [])
        links = "".join(
            f'<li><a href="/page/{p["id"]}">{p["title"]}</a></li>'
            for p in pages
        )
        space_cards += f"""
        <div style="background:white;border-radius:8px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <span style="font-size:22px">{s['icon']}</span>
            <div>
              <a href="/space/{s['key']}" style="font-weight:600;font-size:15px">{s['name']}</a>
              <div style="font-size:12px;color:#6b778c">{s['key']} · {len(pages)}개 페이지</div>
            </div>
          </div>
          <ul style="margin:0;padding-left:18px">{links}</ul>
        </div>"""

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Confluence</title>{_STYLE}</head>
    <body>{_NAV}
    <div style="max-width:960px;margin:32px auto;padding:0 24px">
      <h2>스페이스 ({len(SPACES)}개)</h2>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px">{space_cards}</div>
    </div></body></html>"""


@app.get("/space/{space_key}", response_class=HTMLResponse)
async def space_view(space_key: str):
    space = next((s for s in SPACES if s["key"] == space_key.upper()), None)
    if not space:
        return HTMLResponse("Space not found", status_code=404)
    pages = PAGES.get(space_key.upper(), [])
    rows = "".join(
        f'<li style="padding:10px 0;border-bottom:1px solid #f0f0f0">'
        f'<a href="/page/{p["id"]}" style="font-size:15px">{p["title"]}</a>'
        f'<span style="font-size:12px;color:#6b778c;margin-left:8px">v{p["version"]["number"]} · {p["version"]["when"][:10]}</span>'
        f'</li>'
        for p in pages
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{space['name']}</title>{_STYLE}</head>
    <body>{_NAV}
    <div style="max-width:860px;margin:32px auto;padding:0 24px">
      <div style="color:#6b778c;font-size:13px;margin-bottom:8px">
        <a href="/">스페이스</a> / {space['name']}
      </div>
      <h2>{space['icon']} {space['name']}</h2>
      <div style="background:white;border-radius:8px;padding:8px 24px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
        <ul style="list-style:none;padding:0;margin:0">{rows}</ul>
      </div>
    </div></body></html>"""


@app.get("/page/{page_id}", response_class=HTMLResponse)
async def page_view(page_id: str):
    for space_key, space_pages in PAGES.items():
        for p in space_pages:
            if p["id"] == page_id:
                space = next(s for s in SPACES if s["key"] == space_key)
                labels = " ".join(
                    f'<span style="background:#e3f2fd;color:#0052cc;border-radius:3px;padding:2px 8px;font-size:11px">{lb["name"]}</span>'
                    for lb in p["metadata"]["labels"]["results"]
                )
                return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{p['title']}</title>{_STYLE}</head>
                <body>{_NAV}
                <div style="display:flex;min-height:calc(100vh - 48px)">
                  <div style="width:220px;background:white;border-right:1px solid #dfe1e6;padding:20px 16px;flex-shrink:0">
                    <div style="font-size:12px;font-weight:600;color:#6b778c;margin-bottom:8px">{space['icon']} {space['name']}</div>
                    {"".join(f'<div style="padding:6px 8px;border-radius:4px;font-size:13px;{"background:#e3f2fd;color:#0052cc;font-weight:600" if pp["id"]==page_id else "color:#172b4d"}"><a href="/page/{pp["id"]}" style="color:inherit;text-decoration:none">{pp["title"]}</a></div>' for pp in space_pages)}
                  </div>
                  <div style="flex:1;padding:32px 40px;max-width:800px">
                    <div style="color:#6b778c;font-size:12px;margin-bottom:12px">
                      <a href="/">스페이스</a> / <a href="/space/{space_key}">{space['name']}</a> / {p['title']}
                    </div>
                    <h1 style="font-size:24px;margin:0 0 8px">{p['title']}</h1>
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #f0f0f0">
                      <span style="font-size:12px;color:#6b778c">v{p['version']['number']} · {p['version']['when'][:10]}</span>
                      <div style="display:flex;gap:4px">{labels}</div>
                    </div>
                    {p['body']['storage']['value']}
                  </div>
                </div></body></html>"""
    return HTMLResponse("페이지를 찾을 수 없습니다", status_code=404)


# ── REST API (for actual sync) ────────────────────────────

@app.get("/rest/api/space")
async def api_list_spaces():
    return {"results": [{"key": s["key"], "name": s["name"], "type": s["type"]} for s in SPACES],
            "start": 0, "limit": 25, "size": len(SPACES)}


@app.get("/rest/api/content")
async def api_list_content(spaceKey: str = "", limit: int = 50, start: int = 0, expand: str = ""):
    pages = PAGES.get(spaceKey.upper(), [])
    page_slice = pages[start:start + limit]
    return {
        "results": [{"id": p["id"], "title": p["title"], "body": p["body"],
                     "version": p["version"], "metadata": p["metadata"]} for p in page_slice],
        "start": start, "limit": limit, "size": len(page_slice), "_links": {},
    }


@app.get("/rest/api/content/{page_id}")
async def api_get_content(page_id: str, expand: str = ""):
    for space_pages in PAGES.values():
        for p in space_pages:
            if p["id"] == page_id:
                return {"id": p["id"], "title": p["title"],
                        "body": p["body"], "version": p["version"]}
    return JSONResponse(status_code=404, content={"message": "Page not found"})


if __name__ == "__main__":
    print("=" * 50)
    print("  Mock Confluence: http://localhost:9090")
    print(f"  스페이스: {', '.join(s['key'] for s in SPACES)}")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=9090)
