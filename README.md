# ReportX — Project Reporting & Management System

## 1. Project Overview

**ReportX** is a project-management and project-reporting system for maintaining project information, tracking project delivery, milestones, costs, issues and risks, and generating formal Project Status Reports.

The system combines:

1. A project portfolio/dashboard for seeing all projects.
2. A project data-entry/update system.
3. A detailed page for each individual project.
4. Milestone and delivery tracking.
5. Cost and resource tracking.
6. Issues and risk management.
7. Project-document attachments.
8. Historical saved project states.
9. Formal Project Status Report generation.
10. Word and PDF export.
11. Excel import/synchronization.
12. Administrative controls for cost assumptions and other restricted functions.

The April 2025 FMDQ Project Status Report is the model for the **formal report output**, while the PMO Reporting Dashboard mockup is the model for the **dashboard/data-entry experience**.

---

# 2. Core Concept

ReportX is **stateful and history-aware**.

A project is created once and then continuously maintained as it progresses.

At any point in time, a user should be able to:

- View the current project state.
- Update project information.
- Save the current state.
- Retain historical project/milestone information.
- Generate a Project Status Report for a selected reporting period.
- Export that report to Word or PDF.

The reporting period does **not** have to be monthly. The user can specify an arbitrary start date and end date.

The system should therefore separate:

- The project's underlying structured data.
- The project's saved/history states.
- The reporting period used for a report.
- The generated formal report.

The April 2025 report is an **output/report format reference**, not the database schema.

---

# 3. Main Application Areas

ReportX should have the following major areas:

- Dashboard
- All Projects / Project Portfolio
- Project Detail
- Project creation/update form
- Import Data
- Cost Assumptions
- Report generation
- Project Documents/Attachments
- Historical project states/history

The navigation in the dashboard mockup includes:

- Dashboard
- Milestones
- Project Detail
- Import Data
- Cost Assumptions

It also includes Word/PDF export functionality.

---

# 4. Project Creation and Project ID

## 4.1 Creating a project

When a new project is entered, the user provides the project's required information.

Project identity fields should include:

- Project Name
- Entity/Subsidiary
- Division
- Project Manager
- Status
- Other required project information

## 4.2 Project ID

**Project ID is system-generated.**

The user does NOT manually choose the Project ID when creating a new project.

After a new project is entered and saved, ReportX generates a unique Project ID for it.

The Project ID becomes the system's identifier for that project.

Example:

`PRJ-00001`

The exact ID format can be finalized during implementation, but it must be unique and system-generated.

## 4.3 Existing project updates

When importing/updating project information through Excel, the Project ID is used to determine whether the project already exists.

If the Project ID matches an existing project:

- Update the existing project.
- Keep the project's history.

If the project is new:

- Create a new project.
- Generate its Project ID.

---

# 5. Entity / Subsidiary

Entity and Subsidiary represent the same concept in ReportX and may be used interchangeably.

The project platform should manage projects belonging to entities/subsidiaries such as:

- FMDQX
- FMDQC
- FMDQG
- FMDQP

These values come from the dashboard mockup and can be expanded/changed later.

---

# 6. Division

For the first implementation, use the divisions represented in the Excel/dashboard mockup as placeholders.

Current placeholder values include:

- BDD
- CRD
- MOD
- ISD
- ASD
- GSD
- MAD
- FSD

These are placeholders and can be changed later.

---

# 7. Overall Project Status

The overall project status has three main values:

- Completed
- Ongoing
- Not-Started

This is separate from the status of individual milestones/documents.

---

# 8. Project Completion Percentage

ReportX should **calculate project percentage completion automatically**.

Users should not manually enter the final overall percentage.

The exact completion-weighting mechanism still needs to be finalized before implementation.

The dashboard/mockup contains a `Weight %` field in project/import data, but it has not yet been definitively established whether this is:

- a project-level weight, or
- a milestone-specific weighting system.

Therefore, the implementation must not silently assume a weighting method without confirming this business rule.

---

# 9. Project Schedule

Each project has its own timeline.

Project schedule fields include:

- Start Date
- Original Baseline
- TSC Approved Date / Planned Delivery
- Forecast Delivery
- Actual Delivery
- Schedule Variance

The dashboard mockup describes the planned delivery date as the date shared with TSC.

## 9.1 Schedule Variance

Schedule variance is calculated automatically.

Formula:

`Schedule Variance = Actual/Forecast Delivery Date - TSC Approved Planned Date`

If the project is completed:

`Variance = Actual Delivery - TSC Approved Date`

If the project is not completed:

`Variance = Forecast Delivery - TSC Approved Date`

Therefore, users should not manually calculate schedule variance.

---

# 10. Milestone Lifecycle

Every project follows the following major milestone/delivery lifecycle:

1. BRD
2. SSD
3. Code Drop
4. Quality Assurance Testing
5. VAPT
6. UAT
7. Brand Review
8. Achieve System Readiness (ASR)
9. Go-Live

**ASR is equivalent to Go-Live Preparations.**

BRD and SSD are also part of the project/reporting documentation process.

The milestone journey should be visible on the Project Detail page.

Example:

`BRD → SSD → Code Drop → QA → VAPT → UAT → Brand Review → ASR → Go-Live`

---

# 11. Milestone Statuses

Individual milestones/documents have their own statuses.

Examples from the dashboard lifecycle include:

- Done
- WIP
- Delayed
- Pending
- Not Started
- N/A

Milestone status is independent of the overall project status.

For example:

Project:

`Ongoing`

Milestones:

- BRD — Done
- SSD — Done
- Code Drop — Done
- QA — WIP
- VAPT — Not Started
- UAT — Pending
- Brand Review — N/A
- ASR — Not Started
- Go-Live — Not Started

---

# 12. Milestone Dates

Each milestone should support appropriate dates.

At minimum, the system should support:

- Baseline Date
- Expected Date
- Actual Date, where applicable

Dates may be:

- Available
- TBD
- N/A

The system should not require an actual date where one does not yet exist.

The Project Detail page should allow milestone information to be updated.

A milestone update should support:

- Milestone
- Start Date
- End Date
- Status
- Note

---

# 13. Milestone History

ReportX must retain milestone history.

When milestone information changes, the system should retain historical information rather than simply destroying the previous state.

This supports reporting on project state at different points in time.

---

# 14. RAG Status

The following RAG statuses are entered manually by the user:

- Schedule RAG
- Budget RAG
- Issues RAG

ReportX should **not automatically calculate these RAG values**.

Users explicitly provide the RAG status.

---

# 15. Project Costs and Resources

ReportX must track project resource assumptions and costs.

Resource levels:

- Junior Level 1
- Intermediate Level 2
- Expert Level 3

Project resource inputs:

- Junior Days
- Intermediate Days
- Expert Days
- Other Planned Costs
- Actual Cost to Date

---

# 16. Cost Calculation Rules

The cost business rules in the dashboard mockup are real business rules.

## 16.1 Resource Cost

Formula:

`Resource Cost = (Junior Days × Junior Rate) + (Intermediate Days × Intermediate Rate) + (Expert Days × Expert Rate)`

## 16.2 Contingency

Contingency is calculated from the configured contingency assumption.

## 16.3 Planned Budget

Formula:

`Planned Budget = Resource Cost + Contingency + Other Planned Costs`

Actual cost is entered manually by the user.

---

# 17. Cost Assumptions

Cost rates are administrative assumptions.

The system should support:

- Junior Level 1 Rate
- Intermediate Level 2 Rate
- Expert Level 3 Rate
- Contingency %
- Project Days by level
- Resource cost
- Contingency
- Planned cost

Changing an administrative rate should update calculated project costs accordingly.

## Access

Cost-rate assumptions are restricted to:

- Admin
- PMO

The exact complete role/permission matrix still needs to be finalized.

---

# 18. Issues

Each project should have an Issues section.

Issues should support information based on the formal FMDQ Project Status Report structure.

The April 2025 report includes:

- Priority
- Issue Description
- Impact Summary
- Action Steps

Impact can cover areas such as:

- Milestone
- Schedule
- Scope
- Resources
- Space

Priority levels in the report include:

- Extreme
- High
- Medium
- Low

---

# 19. Risks

Each project should have a Risk section.

Risk should support:

- Probability of Occurrence
- Risk Description
- Impact Summary
- Response Strategy
- Status
- Risk Score

## 19.1 Risk Score

ReportX should calculate risk score automatically.

Formula:

`Risk Score = Probability × Impact`

The April 2025 report provides the probability and impact matrices.

---

# 20. Probability Matrix

Probability levels:

| Level | Description | Probability |
|---|---|---|
| 1 | Rare | 1–20% |
| 2 | Unlikely | 21–40% |
| 3 | Possible | 41–60% |
| 4 | Likely | 61–80% |
| 5 | Almost Certain | 81–100% |

---

# 21. Impact Matrix

Impact levels:

| Level | Description | Example impact |
|---|---|---|
| 5 | Extreme | >18 months delay / >20% time increase / no key objectives |
| 4 | Very High | Severe delay up to 18 months / 10–20% time increase / failure of key objectives or scope reduction |
| 3 | High | Significant delay up to 12 months / 5–10% time increase / some objectives or scope reduction |
| 2 | Medium | Limited delay up to 6 months / <5% time increase / failure of key objectives or scope reduction |
| 1 | Low | <6 months delay / insignificant time increase |

Risk score is therefore derived from the selected probability and impact values.

---

# 22. Executive Assistance Requests

**Not included in the current implementation.**

The April 2025 report contains an Executive Assistance Requests section, including impact on time, cost and quality and requested action, but this feature is intentionally skipped for the current ReportX build.

It can be added later if required.

---

# 23. Planned Activities

ReportX should contain three separate areas for planned activities:

### Planned Accomplishments

What was planned and accomplished during the reporting period.

### Planned but Not Accomplished

Activities that were planned but were not completed.

### Planned Actions for Next Period

Activities planned for the next reporting period.

These should be separate inputs/lists.

---

# 24. Executive Summary

The Executive Summary is manually entered by the user for now.

ReportX should provide an input area where the user can write the summary.

The system does not need to automatically generate the executive summary in the first implementation.

---

# 25. Project Documents / Attachments

Each project should support optional document attachments.

Attachments are **not mandatory**.

Users should be able to attach project documents such as:

- BRD
- SSD
- Code Drop documentation
- QA Report
- VAPT Report
- UAT documentation
- Brand Review documentation
- ASR documentation
- Go-Live documentation

The attachment system should be tied to the relevant project/milestone/document type.

Example:

`BRD → BRD_Budgeting_v2.pdf`

`SSD → SSD_Budgeting_v3.pdf`

---

# 26. Viewing Attached Documents

Users should be able to quickly view an attached document.

For supported PDF documents:

- Show the file name.
- Provide a **View PDF** action.
- Open the PDF in an in-app viewer/modal or appropriate new view.
- Allow the user to quickly inspect the document without having to manually download it.

Users should also be able to replace/update attachments.

Example:

`BRD_Budgeting_v2.pdf   [View PDF] [Replace]`

Attachments remain optional.

---

# 27. Attachments Are Supporting Artifacts

Uploaded documents should **not** become the underlying source of structured project data.

For example, a BRD can have:

- BRD Status
- Baseline Date
- Expected Date
- Actual Date
- Notes
- Attached BRD PDF

The structured fields allow ReportX to calculate, filter, display and report project information.

The attached BRD is the supporting project artifact.

---

# 28. All Projects / Project Portfolio

The All Projects page should provide a portfolio-level view.

The dashboard mockup includes project information such as:

- Project
- Entity
- Division
- Completion
- Status
- TSC Approved
- Planned Go-Live
- Variance
- Budget
- Actual

The portfolio dashboard should also provide KPIs such as:

- Completed
- Average Completion
- Not Started
- Needs Attention
- At Risk / Delayed
- Spend vs Budget

Schedule performance and cost performance should also be represented.

---

# 29. Project Hyperlink / Navigation

Every project listed in the All Projects section should have a clickable hyperlink/action.

Example:

`Budgeting`

Clicking the project should take the user directly to:

**Project Detail → Budgeting**

The Project ID may also be clickable.

The goal is that a user can move from the portfolio list directly into the complete detail page for that project.

---

# 30. Project Detail Page

The Project Detail page is the single-project view containing all necessary project information.

It should include:

### Project Identity

- Project Name
- Project ID
- Entity/Subsidiary
- Division
- Project Manager
- Overall Status
- Percentage Completion

### Schedule

- Start Date
- Original Baseline
- TSC Approved Date
- Planned Delivery
- Forecast Delivery
- Actual Delivery
- Schedule Variance

### Milestones

All nine lifecycle milestones with:

- Status
- Dates
- Notes
- Historical information

### Cost & Resources

- Junior Days
- Intermediate Days
- Expert Days
- Rates
- Resource Cost
- Contingency
- Other Planned Costs
- Planned Budget
- Actual Cost

### RAG

- Schedule RAG
- Budget RAG
- Issues RAG

### Status Update

- Current status update/comments

### Issues

- Project issues

### Risks

- Project risks
- Probability
- Impact
- Automatically calculated Risk Score
- Response Strategy
- Status

### Documents

- Attached project documents
- View PDF
- Replace/upload actions

### History

- Saved project states
- Milestone history
- Historical changes

---

# 31. Project Status Report

ReportX must generate a formal Project Status Report based on the FMDQ April 2025 report structure.

The report should not merely be a screenshot of the dashboard.

It should be a formal document.

The April 2025 report structure is:

1. Executive Summary
2. Project Milestone Status Review
3. Status of Planned Activities
4. Project Issues Summary
5. Project Risk Summary
6. Executive Assistance Requests

However, because Executive Assistance Requests are currently skipped, the ReportX implementation should produce the applicable sections without that feature.

---

# 32. Report Information

The formal report should contain project/report metadata such as:

- Reporting Period Start
- Reporting Period End
- Project Title
- Date of Report
- Delivery Manager / Project Manager
- Report Author
- Executive Sponsor, where applicable

The reporting period is user-defined.

It can be any start/end dates and does not have to be a calendar month.

---

# 33. Milestone Status Review in Report

The report should present the milestone status review.

For each milestone, the report should be able to show:

- Milestone
- Status
- Baseline Completion Date
- Expected Completion Date
- Actual date where applicable
- Whether issues exist

The report should support the milestone lifecycle:

- BRD
- SSD
- Code Drop
- QA
- VAPT
- UAT
- Brand Review
- ASR
- Go-Live

---

# 34. Narrative Status Summary

The formal report should include:

- Schedule RAG
- Budget RAG
- Issues RAG
- Narrative summary/status commentary

The RAG values are manually entered by the user.

---

# 35. Report Planned Activities

The report should contain:

### Planned Accomplishments

### Planned but Not Accomplished

### Planned Actions for Next Period

These correspond to the formal April 2025 reporting structure.

---

# 36. Report Issues Summary

The formal report should contain the project's issue information.

Include:

- Priority
- Issue Description
- Impact Summary
- Action Steps

---

# 37. Report Risk Summary

The formal report should contain:

- Priority
- Probability of Occurrence
- Risk Description
- Impact Summary
- Response Strategy
- Status
- Risk Score where applicable

The risk score is calculated by ReportX.

---

# 38. Report Generation

The report generation flow should be approximately:

`Select Project`
→ `Select Reporting Period`
→ `Load Project State`
→ `Review Report Data`
→ `Generate Report`
→ `Export Word/PDF`

The user should be able to generate a status report at any point in the project's lifecycle.

---

# 39. Historical State / Save State

Users should be able to save the current state of a project.

The system must retain history.

Conceptually:

```text
Project
 ├── Saved State 1
 ├── Saved State 2
 ├── Saved State 3
 └── Current State
```

A saved state represents the project information at a particular point in time.

The exact technical snapshot/version implementation is still an implementation decision, but the business requirement is:

- Users can save state.
- Historical states are retained.
- Milestone history is retained.
- Reports can be produced based on the relevant project state.

---

# 40. Historical Reporting

ReportX must be capable of supporting reporting on project information at different points in time.

Example:

```text
April State
    ↓
May State
    ↓
June State
    ↓
July State
    ↓
Current State
```

The system should not simply overwrite historical information.

This is important because a project may change:

- Status
- Completion
- Forecast date
- Milestone status
- Milestone dates
- Costs
- Issues
- Risks
- Notes

while previous saved states still need to remain available.

---

# 41. Excel Import

The dashboard mockup includes an Excel import workflow:

`Upload`
→ `Map Columns`
→ `Review Changes`
→ `Sync`

The import should support existing project updates and new projects.

Existing projects are identified using Project ID.

The mockup's import data includes fields such as:

- Task
- Entity
- Division
- Project ID
- Brief Description
- Original Baseline
- TSC Approved Date
- BRD
- BRD Status
- SSD
- SSD Status
- Code Drop
- Code Drop Status
- QA
- QA Status
- VAPT
- VAPT Status
- UAT
- UAT Status
- Brand Review
- Brand Review Status
- ASR
- ASR Status
- Go-Live
- Go-Live Status
- Project Manager
- Weight %

The exact handling of `Weight %` for completion still requires final confirmation.

---

# 42. Import Behaviour

When importing:

### Existing project

If Project ID exists:

- Match the project.
- Update applicable information.
- Preserve history.

### New project

If the project does not already exist:

- Create the project.
- Generate a Project ID.
- Store the imported information.

The system should provide a review step before committing changes.

---

# 43. Permissions

The system is intended to be usable by general users, while certain administrative functions are restricted.

Current confirmed rule:

**Admin/PMO can access cost-rate assumptions.**

Other exact permissions still need to be defined.

A likely future role model can include:

- Admin
- PMO
- Project Manager
- General User/Viewer

But these roles and their exact permissions must be confirmed before implementation.

---

# 44. Suggested Permission Principle

At minimum:

### General Users

Should be able to:

- View projects.
- Open Project Detail.
- View milestones.
- View reports.
- View attached documents where permitted.

### Project Managers / Authorized Editors

Should be able to:

- Create/update projects.
- Update milestones.
- Enter status updates.
- Enter issues.
- Enter risks.
- Attach documents.
- Save project states.
- Generate reports.

### Admin / PMO

Should additionally be able to:

- Manage cost assumptions/rates.
- Manage administrative configuration.
- Perform restricted administrative operations.

The exact final matrix must be confirmed.

---

# 45. Dashboard

The Dashboard should provide portfolio-level visibility.

KPIs include:

- Completed projects
- Average completion
- Not Started
- Needs Attention
- At Risk / Delayed
- Spend vs Budget

It should also provide:

- Schedule performance
- Cost performance
- Project portfolio table
- Project status
- Completion
- TSC-approved date
- Planned Go-Live
- Variance
- Budget
- Actual cost

Projects should be clickable into their Project Detail page.

---

# 46. Dashboard Lifecycle View

The dashboard should visually represent the project lifecycle:

`BRD → SSD → Code Drop → QA → VAPT → UAT → Brand Review → ASR → Go-Live`

Statuses can visually communicate:

- Done
- WIP
- Delayed
- Pending
- Not Started
- N/A

---

# 47. Project Data Entry Form

The project form should support:

## Identity

- Project Name
- Project ID — system generated
- Subsidiary/Entity
- Project Manager
- Division
- Status
- Percentage Completion — calculated
- Status Update/Comments

## Schedule

- Start Date
- Planned Delivery
- TSC Approved Planned Date
- Forecast Delivery
- Actual Delivery
- Variance — calculated

## Resources/Budget

- Junior Days
- Intermediate Days
- Expert Days
- Other Planned Costs
- Actual Cost to Date
- Resource Cost — calculated
- Contingency — calculated
- Planned Budget — calculated

## Milestones

All nine milestones, each with:

- Status
- Baseline date
- Expected date
- Actual date where applicable
- Notes
- History

## RAG

- Schedule RAG
- Budget RAG
- Issues RAG

## Issues

Issue records.

## Risks

Risk records with calculated score.

## Planned Activities

- Accomplished
- Not accomplished
- Next-period actions

## Executive Summary

Manual text field.

## Documents

Optional attachments.

---

# 48. Save Behaviour

The project form should support:

- Save Draft
- Save Project

Saving a project should persist the current project state.

Where the user explicitly saves a state/version, that state should be retained for history.

---

# 49. Architecture Concept

The recommended conceptual architecture is:

```text
                  REPORTX
                     │
       ┌─────────────┴─────────────┐
       │                           │
 Project Database             History / States
       │                           │
       ├───────────────┬───────────┤
       │               │
       ▼               ▼
 Portfolio         Project Detail
 Dashboard         / Data Entry
       │               │
       └───────┬───────┘
               │
               ▼
        Report Generation
               │
          ┌────┴────┐
          ▼         ▼
       Word        PDF
```

The project database should contain structured entities for:

- Projects
- Milestones
- Milestone history
- Project states/snapshots
- Resources
- Cost assumptions
- Issues
- Risks
- Planned activities
- Reports/report metadata
- Attachments/documents
- Users/permissions

---

# 50. Important Data Design Principle

Do **not** store the entire project as one giant report document.

Instead, store structured project data.

For example:

```text
Project
 ├── Identity
 ├── Schedule
 ├── Milestones
 │    ├── BRD
 │    ├── SSD
 │    ├── Code Drop
 │    ├── QA
 │    ├── VAPT
 │    ├── UAT
 │    ├── Brand
 │    ├── ASR
 │    └── Go-Live
 ├── Costs
 ├── Resources
 ├── Issues
 ├── Risks
 ├── Planned Activities
 ├── Executive Summary
 ├── Documents
 └── History
```

The report engine then assembles this structured information into the formal FMDQ-style report.

---

# 51. Major User Flow

The complete intended workflow is:

```text
1. User creates a project
        ↓
2. ReportX generates Project ID
        ↓
3. User enters project identity/schedule information
        ↓
4. User tracks the 9 project milestones
        ↓
5. User updates milestone dates/statuses/notes
        ↓
6. User enters resource and cost information
        ↓
7. ReportX calculates resource cost/planned budget
        ↓
8. User enters actual cost
        ↓
9. User enters Schedule/Budget/Issues RAG
        ↓
10. User enters issues
        ↓
11. User enters risks
        ↓
12. ReportX calculates risk scores
        ↓
13. User enters planned activities
        ↓
14. User enters executive summary
        ↓
15. User optionally uploads BRD/SSD/etc.
        ↓
16. User saves project state
        ↓
17. Project appears in All Projects
        ↓
18. User clicks project hyperlink
        ↓
19. Project Detail page opens
        ↓
20. User can view/update the complete project
        ↓
21. User selects reporting period
        ↓
22. ReportX loads appropriate project state
        ↓
23. User reviews report
        ↓
24. ReportX generates formal Project Status Report
        ↓
25. User exports Word/PDF
```

---

# 52. Key Principles

## Project ID

System-generated, not manually entered.

## Project Detail

Every project in All Projects must link directly to its Project Detail page.

## Documents

Attachments are optional.

## PDF Viewing

Attached PDFs should be quickly viewable inside ReportX.

## Milestones

Exactly nine lifecycle milestones for the current implementation.

## RAG

Manually entered.

## Risk

Automatically calculated:

`Probability × Impact`

## Schedule Variance

Automatically calculated from TSC-approved planned date against actual/forecast delivery.

## Cost

Automatically calculated using configured rates and contingency.

## Actual Cost

Manually entered.

## Completion

Automatically calculated; exact weighting method still needs final confirmation.

## History

Project and milestone history must be retained.

## Reporting

Reports can be generated for arbitrary reporting periods.

## Report Format

Formal FMDQ-style Project Status Report, not merely a dashboard screenshot.

## Executive Assistance Requests

Skipped for now.

## Cost Rates

Admin/PMO restricted.

---

# 53. Items Still Requiring Final Confirmation Before Coding

The main unresolved business decisions are:

### 1. Completion Percentage Formula

How exactly should ReportX calculate overall project completion?

Possible basis to confirm:

- Equal weighting of the nine milestones, or
- Weight % supplied for milestones/projects, or
- Another business-defined weighting model.

### 2. Final Permission Matrix

Confirm exactly what:

- Admin
- PMO
- Project Manager
- General User/Viewer

can create, edit, view, delete, import, export and administer.

### 3. Saved State Behaviour

Confirm whether every explicit "Save State" action creates an immutable snapshot/version and whether generated reports should permanently reference that snapshot.

### 4. Attachment File Types

PDF viewing is required for PDFs.

Confirm which other file types should be accepted for uploads, such as:

- PDF
- DOCX
- XLSX
- ZIP
- Images

### 5. Project ID Format

The ID must be system-generated and unique.

The exact format/prefix can be finalized during implementation.

---

# 54. Definition of Done

ReportX's first complete version should allow a user to:

- Create a project.
- Automatically receive a Project ID.
- View the project in All Projects.
- Click the project to open Project Detail.
- View all project information from one page.
- Track the nine milestones.
- Update milestone dates/statuses/notes.
- Preserve milestone history.
- Calculate project completion.
- Enter schedule/budget/issues RAG.
- Automatically calculate schedule variance.
- Enter resources and costs.
- Automatically calculate resource cost.
- Automatically calculate contingency and planned budget.
- Manually enter actual cost.
- Record issues.
- Record risks.
- Automatically calculate risk score.
- Enter planned accomplishments.
- Enter unaccomplished plans.
- Enter next-period actions.
- Enter an executive summary.
- Optionally attach BRD, SSD, QA, VAPT, UAT, Brand, ASR and Go-Live documents.
- Quickly view attached PDFs.
- Replace attachments.
- Save project states.
- Retain historical states.
- Import project information from Excel.
- Update existing projects using Project ID.
- Create new projects from imports and generate IDs.
- Review imports before synchronization.
- View portfolio KPIs.
- Generate a formal Project Status Report.
- Choose an arbitrary reporting period.
- Export the report to Word.
- Export the report to PDF.
- Maintain administrative cost assumptions.
- Restrict administrative cost settings to authorized users.

---

# 55. Source Documents

The functional requirements are based primarily on:

1. **Project Status Report — Budgeting, April 2025**
   - Formal FMDQ Project Status Report structure.
   - Milestone status review.
   - Planned activities.
   - Issues.
   - Risks.
   - Probability/impact matrices.
   - Executive assistance request structure.

2. **PMO Reporting / Project Reporting Dashboard Mockup**
   - Portfolio dashboard.
   - Project detail.
   - Milestone lifecycle.
   - Project data-entry form.
   - Excel import.
   - Cost assumptions.
   - Resource/cost calculations.
   - Project fields and workflow.

ReportX combines these two concepts:

**Dashboard + structured project management + history + documents + formal reporting.**

---

# 56. Running ReportX

## 56.1 Requirements

- Windows, macOS or Linux
- Python 3.11 or newer
- A modern browser (Edge, Chrome or Firefox)

No database server is needed: ReportX stores its data in a single SQLite file.

## 56.2 First-time setup

From the `reportx` folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

## 56.3 Start the app

```powershell
cd backend
..\.venv\Scripts\python.exe run.py
```

Then open **http://localhost:8000** in a browser.

- **First visit:** ReportX asks you to create the first Administrator account (name, work email, a password of at least 10 characters). There is no default password.
- **Everyone else:** the Administrator adds users under **Admin → Users**. Each new user receives a one-time temporary password and must choose their own at first sign-in.

To stop the app, press `Ctrl+C` in the terminal. If code changes don't appear after editing, stop and start the app again.

## 56.4 Where data is kept

| What | Location |
|---|---|
| Database (projects, history, users, reference data) | `backend/data/reportx.db` |
| Uploaded attachments | `backend/uploads/` |

Back up both folders together. Deleting `reportx.db` resets ReportX to a fresh install (the first-run setup screen appears again).

## 56.5 Configuration

Optional settings go in `backend/.env` — copy `backend/.env.example`, which lists every option (database location, session length, sign-in lockout, demo data, and so on).

Business settings are managed inside the app by an Administrator instead:

- **Admin → Settings:** application and organisation name, currency, Project ID format, report classification label, accepted attachment types and size.
- **Admin → Reference data:** entities, divisions, statuses, RAG values, priorities, risk levels, milestone names, report legend text and Excel import column names/spellings.
- **Cost assumptions:** day rates and contingency (PMO and Admin).

## 56.6 Demo data

To load three sample projects into an empty database, add this line to `backend/.env` and start the app:

```
REPORTX_SEED_DEMO_PROJECTS=true
```

Demo projects are only added when the database has no projects.

## 56.7 Roles

| Role | Can do |
|---|---|
| Viewer | View everything; preview and export reports |
| Project Manager | Also create projects, and edit their own projects (milestones, issues, risks, documents, saved states) |
| PMO | Also edit all projects, import from Excel, change cost rates |
| Admin | Also manage users, reference data and settings |

## 56.8 Reports

On a project, choose **Generate report**, pick the reporting period, and select **Generate PDF**. The PDF follows the April 2025 FMDQ Project Status Report format and opens in a new tab. **Word** gives an editable copy in the same layout. By default a report uses the latest state saved on or before the end of the period.
