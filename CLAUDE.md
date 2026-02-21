# midjourney-api

> AI-augmented project with Prospec Skills and structured AI Knowledge

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


## Working with This Project

1. **開始前**: 閱讀 Constitution 了解專案原則
2. **理解結構**: 查閱 AI Knowledge Index 掌握模組架構
3. **程式碼規範**: 遵循 Conventions 文件中的風格指南
4. **使用 Skills**: 透過 `/skill-name` 指令觸發專用工作流程
5. **模組依賴**: 修改前檢查 `prospec/ai-knowledge/module-map.yaml`

## Notes

- 此檔案為 Layer 0 (always loaded) - 保持簡潔，指向其他資源
- Skills 為 Layer 1-2 - 按需載入詳細指令
- Knowledge Base 為 on-demand - 根據工作範圍載入
