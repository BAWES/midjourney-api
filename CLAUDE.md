# midjourney-api

> AI-augmented project with Prospec Skills and structured AI Knowledge

## 語言規定

- **AI 回應語言**：繁體中文
- **Commit message**：英文，conventional commits 格式
- **程式碼命名**：英文
- **程式碼註解**：英文
- **文件（.md）**：繁體中文

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI
- **Package Manager**: pnpm (for prospec tooling), pip/poetry (for Python)
- **Database**: PostgreSQL + SQLAlchemy 2.x async
- **Testing**: pytest + pytest-asyncio

## Core Resources

### Constitution
讀取專案原則與約束: [`prospec/CONSTITUTION.md`](prospec/CONSTITUTION.md)

### AI Knowledge Base
模組索引與專案結構: [`prospec/ai-knowledge/_index.md`](prospec/ai-knowledge/_index.md)

### Coding Conventions
程式碼規範與最佳實踐: [`prospec/ai-knowledge/_conventions.md`](prospec/ai-knowledge/_conventions.md)

## Available Prospec Skills

此專案配備以下 Prospec Skills，可透過 slash command 觸發:

### /prospec-explore

探索模式 — 作為思考夥伴，協助釐清需求、調查問題、比較方案。

**Type**: Lifecycle

### /prospec-new-story

建立新的變更需求。引導使用者描述需求，呼叫 prospec change story 建立結構化的 proposal.md 和 metadata.yaml。

**Type**: Planning
**References**: `.prospec/skills/prospec-new-story/references/`

### /prospec-plan

基於變更需求生成實作計劃。讀取 proposal.md、相關模組的 AI Knowledge 和 Constitution，產出結構化的 plan.md 和 delta-spec.md。

**Type**: Planning
**References**: `.prospec/skills/prospec-plan/references/`

### /prospec-design

設計階段 — 從 proposal 產出視覺與互動規格（Generate Mode），或從設計工具反向萃取規格（Extract Mode）。支援 pencil/Figma/Penpot/HTML 平台。Design phase, UI/UX specification generation and extraction.

**Type**: Planning
**References**: `.prospec/skills/prospec-design/references/`

### /prospec-tasks

將實作計劃拆分為可執行的任務清單。按架構層次排序，使用 checkbox 格式，含複雜度估算和並行標記。

**Type**: Planning
**References**: `.prospec/skills/prospec-tasks/references/`

### /prospec-ff

快速前進 — 一次生成所有 planning artifacts（story → plan → tasks）。適合需求明確時快速推進。

**Type**: Planning

### /prospec-implement

按 tasks.md 逐項實作任務。讀取任務清單，按順序實作，完成後勾選 checkbox。

**Type**: Execution
**References**: `.prospec/skills/prospec-implement/references/`

### /prospec-verify

驗證實作是否符合規格和計劃。執行 Constitution 完整驗證、tasks.md 完成度、spec 一致性、測試通過率。

**Type**: Execution

### /prospec-knowledge-generate

生成 AI Knowledge。讀取 raw-scan.md，分析專案結構，自主決定模組切割並產出模組 README 和索引。

**Type**: Lifecycle
**References**: `.prospec/skills/prospec-knowledge-generate/references/`

### /prospec-archive

歸檔已完成的變更。掃描 changes 目錄，將 verified 狀態的變更搬移至 archive，生成 summary.md 並提示 Knowledge 更新。

**Type**: Lifecycle
**References**: `.prospec/skills/prospec-archive/references/`

### /prospec-knowledge-update

增量更新 AI Knowledge。解析 delta-spec.md 識別受影響模組，掃描原始碼後更新模組 README、_index.md 和 module-map.yaml。Incremental knowledge update, delta-spec driven.

**Type**: Lifecycle
**References**: `.prospec/skills/prospec-knowledge-update/references/`

## Available Prospec Skills

透過 `/skill-name` 觸發專用工作流程：

| Skill | 用途 | 類型 |
|-------|------|------|
| `/prospec-explore` | 釐清需求、調查問題、比較方案 | Lifecycle |
| `/prospec-new-story` | 建立新的變更需求 | Planning |
| `/prospec-plan` | 生成實作計劃 | Planning |
| `/prospec-design` | 視覺與互動規格 | Planning |
| `/prospec-tasks` | 拆分為可執行任務清單 | Planning |
| `/prospec-ff` | 快速前進（story → plan → tasks 一次完成） | Planning |
| `/prospec-implement` | 按 tasks.md 逐項實作 | Execution |
| `/prospec-verify` | 驗證實作符合規格 | Execution |
| `/prospec-knowledge-generate` | 生成模組 AI Knowledge | Lifecycle |
| `/prospec-knowledge-update` | 增量更新 AI Knowledge | Lifecycle |
| `/prospec-archive` | 歸檔已完成的變更 | Lifecycle |

## 知識分層載入（Critical）

本專案採用**漸進式知識載入**，避免一次讀取所有文件造成 context window 浪費。AI Agent **必須**按層次讀取：

```
Layer 0 ─ CLAUDE.md（本檔案）
  │       Always loaded，提供全局方向與入口指引
  │       ⚠️ 不要在這層做任何實作決策
  │
  ├─ Layer 1 ─ 按需載入，每次任務開始前讀取
  │   │
  │   ├─ prospec/CONSTITUTION.md        ← 原則與硬約束
  │   │   何時讀：每次 session 開始、做架構決策前、code review 時
  │   │   為什麼：確保不違反專案原則（如 Local-First、TDD、Atomic Commit）
  │   │
  │   └─ prospec/ai-knowledge/_index.md ← 模組索引
  │       何時讀：需要了解專案結構、模組依賴關係時
  │       為什麼：快速定位要修改的模組，避免改錯地方
  │
  └─ Layer 2 ─ 按工作範圍載入，只讀需要的部分
      │
      ├─ prospec/ai-knowledge/modules/<name>/README.md  ← 特定模組詳情
      │   何時讀：實際修改該模組的程式碼時
      │   為什麼：了解模組的 API、內部結構、測試方式
      │
      ├─ prospec/ai-knowledge/_conventions.md            ← 程式碼慣例
      │   何時讀：寫新程式碼或 code review 時
      │   為什麼：確保命名、pattern、錯誤處理風格一致
      │
      ├─ docs/requirements.md                            ← 需求規格
      │   何時讀：確認功能範圍、驗證實作是否符合需求時
      │   為什麼：避免實作 Phase 2/3 的功能或遺漏 Phase 1 需求
      │
      └─ docs/plans/*.md                                 ← 設計與實作計劃
          何時讀：開始實作特定 Task 時
          為什麼：取得該 Task 的完整步驟與預期程式碼
```

### 載入規則

1. **每次新 session 開始**：讀 CLAUDE.md（自動）→ 讀 Constitution → 讀 _index.md
2. **開始實作任務前**：讀該任務涉及的模組 README + _conventions.md
3. **做架構或設計決策前**：重讀 Constitution 的相關原則
4. **禁止一次全讀**：不要在 session 開始時把所有 Layer 2 文件都讀進來，浪費 context window
5. **修改多個模組時**：逐一讀取涉及的模組 README，不要一次全部載入

### 為什麼這很重要

- Claude Code 的 context window 有限，全部載入會擠壓實際工作空間
- 漸進式載入確保每次讀取的都是**當下需要的**知識
- Constitution 必須頻繁重讀，因為它定義了不可違反的硬約束

## 注意事項

- 此檔案為 Layer 0（always loaded），保持簡潔，詳細資訊指向其他文件
- 修改架構前必須先讀 Constitution
- 新增功能前必須先讀 requirements.md 確認是否在 Phase 1 MVP 範圍內
- Phase 2/3 功能不在當前實作範圍，不得提前引入

## 主動技
為了確保你有讀到這個檔案，每次執行任務時開頭都說「記せ、規典」（始解）