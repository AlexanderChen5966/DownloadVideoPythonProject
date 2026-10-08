---
name: sign-off-generator
description: Generate internal sign-off documents (簽呈產生器). Use when user requests internal sign-off document, corporate form, or access request documents.
tags:
  - document
  - sign-off
  - access request
metadata:
  version: 1.0.0
  last-updated: 2026-01-06
---

# Sign-off Document Generator

When user requests internal sign-off document or corporate form,
always follow the structured format below.

Output rules:
1. 主旨 / Subject
2. 說明 / Description
3. 申請人 / Applicant
4. 員編 / Employee ID
5. 擬辦 / Submit for approval

Language rules:
Output in Traditional Chinese if user text is zh-TW;
Include English translation if user asks for bilingual.

Templates for request types:

AWS Software Developer:
主旨:
申請開啟 AWS Software Developer 權限
Apply for AWS Software Developer Access

說明:
申請開啟 AWS Software Developer 權限，以利進行軟體開發及系統測試相關工作。
Applicant applies for AWS Software Developer access permissions for the purpose of software development and system testing operations.

PMS Access:
主旨:
申請啟用 PMS 專案、AWS 服務權限
Apply for PMS Project and AWS Services Access

說明:
申請啟用 PMS 專案相關 AWS 服務權限，以利進行軟體開發及系統測試相關工作。
Applicant requesting to enable AWS services for PMS project to facilitate software development and system testing.

Projects:
{{ projects }}

AWS Services:
{{ aws_services }}

擬辦:
擬請核准
Submit for approval