---
title: ORPHEUS
emoji: 🎼
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# ORPHEUS 🎼

**O**rphan-disease **R**epurposing via **P**lanning · **H**ypothesis · **E**valuation · **U**pdating **S**ystem
— 희귀·난치질환 **약물 재창출**을 위한 멀티 에이전트 폐루프. · Team **BYTEFORCE**

> 제4회 AI 신약개발 경진대회(4th JUMP AI, fourth.py) · 분야 4(융합: 1+2 축 + 얇은 3)
> 이미 **승인된 안전한 약물** 공간에서, 질병→타깃→후보약 가설부터 분자 최적화·평가·임상 타당성까지
> 하나의 폐루프로 자율 수행하고, 실패하면 **스스로 원인을 찾아 되돌아가 고친다**. 전 과정은 기록된다.

---

## 지금 바로 실행 (오프라인, API 키 불필요)

우분투/WSL/데비안은 시스템 파이썬에 직접 설치가 막혀 있어(PEP 668) **가상환경**을 쓴다. 명령은 `python`이 아니라 `python3`.

```bash
# 1) 가상환경 생성 + 활성화  (venv 오류가 나면: sudo apt install python3-venv)
python3 -m venv .venv
source .venv/bin/activate            # 이후로는 'python'·'pip'이 이 환경을 가리킴

# 2) 설치  (venv 안이라 PEP 668 미적용. RDKit은 cp314 휠 제공 → 파이썬 3.14도 OK)
pip install -r requirements.txt

# 3) 실행
python run.py --list                                   # 씨앗 질환 목록
python run.py -d "Pulmonary Arterial Hypertension"     # 폐루프 실행 → 후보 카드
python run.py --eval                                   # 역방향 재발견 벤치마크 (Recall@k · MRR)
python tests/test_smoke.py                             # 스모크 테스트
```

빠져나올 땐 `deactivate`, 다음에 다시 켤 땐 `source .venv/bin/activate`.
라이브 LLM 보강: `export ANTHROPIC_API_KEY=...` (본선 크레딧을 여기에 연결).

> venv 없이 딱 한 번 돌려보려면 `pip install --break-system-packages -r requirements.txt` 도 되지만,
> 시스템 파이썬을 오염시킬 수 있어 권장하지 않음. venv가 정석.

### 실행 예시

`--eval` (역방향 재발견): 과거 실제 재창출 성공을 정답으로 **가려 두고** 다시 찾는지 측정.

```
Recall@1 : 1.0   Recall@3 : 1.0   MRR : 1.0   (씨앗 5쌍)
  Sildenafil    → Pulmonary Arterial Hypertension   PDE5A     rank 1
  Thalidomide   → Multiple Myeloma                  CRBN      rank 1
  Propranolol   → Infantile Hemangioma              ADRB2     rank 1   (top-3: Propranolol, Salbutamol)
  ...
```

`-d "…"` (폐루프): 후보 카드 + Critic 트레이스 출력. 근거(타깃 겹침)가 없는 질환에는
**후보를 지어내지 않고** `no viable candidate`를 반환한다.

---

## 웹 데모 (GitHub → 배포)

하나의 리포로 세 가지 방식으로 실행된다. UI는 라이브/정적을 **자동 감지**해 배지로 표시한다.

| 방식 | 무엇 | 어디에 |
|---|---|---|
| **라이브** (실시간 RDKit 계산) | FastAPI + Docker | Hugging Face Spaces · Render · Railway · Cloud Run |
| **정적 리플레이** (사전 계산, 콜드스타트 0) | `web/static` 정적 호스팅 | Vercel |
| **로컬 라이브** | uvicorn | 내 PC |

> Vercel 단독으로는 RDKit(C++ 컴파일 라이브러리)을 서버리스에서 안정적으로 구동하기 어렵다.
> 그래서 **라이브 계산은 컨테이너 호스트**(HF Spaces 권장), **Vercel은 정적 리플레이**로 역할을 나눈다.

### GitHub 올리기

```bash
cd /mnt/c/dev/orpheus
git init && git add -A
git commit -m "feat: ORPHEUS repurposing agent + web demo"
gh repo create byteforce/orpheus --public --source=. --push     # GitHub CLI 사용 시
# 수동: git remote add origin https://github.com/<you>/orpheus.git && git push -u origin main
```

UI 푸터의 GitHub 링크는 기본값이라, `web/static/index.html`의 `$("#gh").href` 한 줄을 본인 리포 주소로 바꿔주면 된다.

### A) 라이브 데모 — Hugging Face Spaces (권장)

RDKit이 기본 지원되고 무료 공개 URL이 나온다. New Space → **SDK: Docker** → 이 리포 연결(또는 push). Space의 `README.md` 최상단에 프론트매터만 추가하면 끝:

```yaml
---
title: ORPHEUS
emoji: 🎼
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
```

빌드되면 그 URL에서 **아무 질환이나 실시간으로** 돌아간다. Render/Railway는 리포 연결 → Dockerfile 자동 감지 → 배포(포트는 `$PORT` 자동 주입).

### B) 정적 데모 — Vercel (URL 하나로)

`web/static/data/*.json`(사전 계산 결과)이 이미 커밋돼 있다. Vercel에서 리포 import 하면 `vercel.json`이 `web/static`을 정적 호스팅한다.

```bash
npm i -g vercel && vercel --prod
```

라이브가 아니므로 UI가 자동으로 **REPLAY** 배지를 띄우고, 사전 계산된 질환만 실행된다. 씨앗 데이터를 바꾸면 `python web/build_static.py`를 다시 실행해 JSON을 갱신하고 커밋한다.

### C) 로컬 라이브

```bash
source .venv/bin/activate
pip install -r requirements-web.txt
uvicorn web.app:app --port 8000        # http://localhost:8000
```

---

## 아키텍처

```
disease
  → ① 가설      질병 → 타깃 → 승인약 후보 (타깃 겹침 랭킹)
  → ② 분자최적화  RDKit 유사체 생성·물성 (분야 2)
  → ③ 평가      기술자 · ADMET(규칙) · PAINS/Brenk · SA · 결합(surrogate)
  → ④ 임상타당성  개발 경로 기반 feasibility/risk 트리아지 (프로토콜 생성 안 함; 분야 3 얇게)
  → ⑤ Critic    수렴 판정 / 실패 원인 귀속 + 재계획 지시
      ↺ 지정된 상단 단계로 재투입 (config.MAX_ITERATIONS 까지)
Orchestrator가 루프를 돌리고, Provenance Ledger가 모든 단계를 기록.
```

## 무엇이 진짜이고, 무엇이 스왑 포인트인가 (정직성)

| 부분 | 상태 |
|---|---|
| RDKit 화학(기술자·유사도·구조경보·유사체·SA) | **실제 동작** |
| 규칙 기반 ADMET (Lipinski·Veber) | **실제 동작** |
| 타깃 겹침 가설 · 폐루프 · Critic 재계획 | **실제 동작** |
| 역방향 재발견 평가 (Recall@k·MRR) | **실제 수치 산출** |
| 결합 친화도 (도킹) | **surrogate** — 본선에서 AutoDock Vina로 교체 |
| 데이터 (약물·타깃·질병) | 소형 씨앗셋 — 본선에서 ChEMBL/DrugBank/Open Targets로 교체 |
| LLM 추론 보강 | 배선 완료 — 키 있으면 활성, 없으면 결정론적 폴백 |

`ScoreCard.affinity_is_surrogate=True`가 계산값과 추정값을 항상 구분한다.

## 구조

```
orpheus/
  run.py                    # CLI (--disease / --eval / --list)
  CLAUDE.md                 # 에이전트용 프로젝트 헌법 (계약·불변식)
  requirements.txt
  orpheus/
    config.py               # 임계값·경로·시드·루프 설정
    core/
      orchestrator.py       # 폐루프 + 재계획
      ledger.py             # Provenance Ledger (jsonl)
      llm.py                # Anthropic 래퍼 + 오프라인 폴백
      knowledge.py          # 씨앗 KB 로더
      schemas.py            # 에이전트 간 타입 계약
    agents/
      hypothesis.py optimizer.py evaluator.py clinical.py critic.py
    tools/
      chem.py               # RDKit
      docking.py            # 결합 surrogate (스왑 포인트)
      admet.py              # 규칙 ADMET
  data/                     # drugs.json · diseases.json · gold_repurposing.json
  evals/retrospective.py    # 역방향 재발견 벤치마크
  tests/test_smoke.py
  web/
    app.py                  # FastAPI (엔진 래핑 + UI 서빙, 라이브 모드)
    build_static.py         # 사전 계산 → web/static/data/*.json (정적/Vercel)
    static/index.html       # 단일 페이지 UI (라이브·정적 자동 감지)
    static/data/*.json      # 사전 계산 결과 (커밋됨 — Vercel 리플레이용)
  Dockerfile                # 라이브 컨테이너 (HF Spaces·Render·Railway)
  vercel.json               # 정적 배포 설정
  requirements-web.txt      # 웹 계층 의존성 (fastapi·uvicorn)
  LICENSE                   # MIT (BYTEFORCE)
```

## 본선 로드맵

1. `tools/docking.py` → AutoDock Vina (실제 도킹).
2. `core/knowledge.py` → ChEMBL / DrugBank / Open Targets, 데이터 확장.
3. `ANTHROPIC_API_KEY`(본선 크레딧)로 LLM 보강 활성화.
4. Ledger → Reasoning Graph UI (시연, 제안서 §6).
5. `data/gold_repurposing.json` 확장으로 벤치마크 강화.

세부 계약·불변식은 **CLAUDE.md** 참조.
