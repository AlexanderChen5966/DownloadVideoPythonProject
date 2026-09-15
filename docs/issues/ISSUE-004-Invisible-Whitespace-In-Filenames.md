# ISSUE-004: 檔名夾帶不可見空白導致後續處理找不到檔案

> **狀態：** ✅ 已解決
> **建立日期：** 2026-09-15
> **分類：** 檔名處理 / 跨工具相容性

---

## 問題描述

對兩支已下載完成的 MP4 執行轉檔時，明明檔案就在目錄裡，卻一律回報找不到：

```
Error opening input file 小壽星專屬故事 EP141 《小象的愛心電池》 手足相處｜同理他人｜家庭生活.mp4.
Error opening input files: No such file or directory
```

```
ls: 睡前故事 EP143 《我從哪裡來？》 生命教育｜兒童性教育｜家庭生活.mp4: No such file or directory
```

### 關鍵症狀：`ls` 列得出來，但打檔名找不到

`ls` 可以正常列出檔案，複製 `ls` 輸出的檔名也能操作，**唯獨照著螢幕重新打一次就失敗**。這個特徵是判斷本問題的決定性線索——它排除了「檔案不存在」「權限不足」「路徑打錯」等可能，指向**檔名裡有肉眼看不出來的字元**。

用 `repr()` 一看即現形：

```python
'小壽星專屬故事 EP141 《小象的愛心電池》\xa0手足相處｜同理他人｜家庭生活.mp4'
```

`\xa0` 是 **NBSP（U+00A0，不斷行空格）**，在任何介面上都和半形空格長得一模一樣。

---

## 根本原因

問題**源自本專案的下載流程**，不是使用者操作失誤。`download_history.json` 的原始紀錄就已帶著 `\xa0`：

```
/tmp/downloads/睡前故事 EP143 《我從哪裡來？》\xa0生命教育｜兒童性教育｜家庭生活.mp4
```

成因是兩層疏漏疊加：

1. **yt-dlp 輸出樣板未經清洗** — `server.py` / `download_cli.py` 都用 `-o "{output_dir}/%(title)s.%(ext)s"` 讓 yt-dlp 直接落地。YouTube 標題含 NBSP 時會原封不動寫進檔名，這條路徑**完全沒有呼叫 `sanitize_filename()`**。

2. **`sanitize_filename()` 本身也擋不住** — 原實作只處理 `\/:*?"<>|` 與 ASCII 控制字元（`\x00-\x1f`）。NBSP 是合法的可列印字元，不在清單內；零寬字元（U+200B、U+FEFF 等）同理。

> ⚠️ 與 [ISSUE-003](ISSUE-003-YouTube-403-Player-Client.md) 的關係：兩者都出在 yt-dlp 指令組裝，但 ISSUE-003 影響的是**能否下載成功**，本問題下載完全成功、**壞在下載之後的每一道工序**。潛伏期長，且因為症狀是「檔案不存在」，極易被誤判為使用者打錯路徑。

### 影響範圍

檔名一旦落地，所有下游工序都會中招，且錯誤訊息都長得像使用者的錯：

| 呼叫端 | 失敗形式 |
|--------|---------|
| MCP `convert_to_mp3` | `os.path.exists()` 為 False → `FILE_NOT_FOUND` |
| `.claude/skills/media-processor/scripts/*.py` | `Path.exists()` 為 False → `❌ 找不到輸入檔案` |
| 手動 shell 指令 | Tab 補完失效、複製貼上的路徑對不上 |

---

## 解決方案

分「治本」與「治標」兩層，缺一不可：治本讓新檔案不再產生壞檔名，治標讓既有的壞檔名仍能處理。

### 治本：yt-dlp 命名前就清洗

在 `utils/path_resolver.py` 新增共用 helper，讓 yt-dlp 在套用 `-o` 樣板**之前**先改寫 title：

```python
def filename_cleanup_args() -> list[str]:
    return [
        "--replace-in-metadata", "title", f"[{LOOKALIKE_SPACES}]", " ",
        "--replace-in-metadata", "title", f"[{INVISIBLE_CHARS}]", "",
    ]
```

選擇 `--replace-in-metadata` 而非「下載後改名」，是因為影片與字幕檔共用同一個 title，**在來源就改掉才能保證兩者檔名一致**；事後改名只會動到 `--print after_move:filepath` 印出的那一個檔案，導致 `.srt` 與影片對不上。

**刻意不使用 `--restrict-filenames`**：該參數會把檔名限制成純 ASCII，中文標題會整個被轉寫或刪除，代價遠大於收益。

### 治標：容忍編碼不同的路徑

在 `utils/sanitizer.py` 新增兩個函式：

| 函式 | 用途 |
|------|------|
| `normalize_unicode_filename()` | 不可見空白轉半形空格、零寬字元移除、統一 NFC、合併連續空格 |
| `resolve_existing_path()` | 找不到檔案時依序退回 NFC/NFD 變體，再掃同目錄比對正規化後的檔名 |

`sanitize_filename()` 也改為先過一次 `normalize_unicode_filename()`，podcast 與音檔下載路徑一併受惠。

處理的字元集中管理於 `utils/sanitizer.py`：

```python
LOOKALIKE_SPACES = "  ...    "  # 與半形空格難以區分
INVISIBLE_CHARS  = "​‌‍‎‏⁠﻿"  # 完全不可見
```

> **全形空格（U+3000）刻意不納入**。本問題的危害來自「與半形空格**無法區分**」，U+3000 寬度明顯不同、且常是 CJK 排版的刻意選擇，轉換它會造成非預期的檔名變動。

### 修改檔案

| 檔案 | 位置 | 說明 |
|------|------|------|
| `utils/sanitizer.py` | 新增 helper | `normalize_unicode_filename()` / `resolve_existing_path()`；`sanitize_filename()` 加掛正規化 |
| `utils/path_resolver.py` | 新增 helper | `filename_cleanup_args()` |
| `utils/__init__.py` | 匯出 | 對外公開兩個新函式 |
| `server.py` | `download_media` 下載指令 | 帶入清洗參數 |
| `server.py` | `convert_to_mp3` | 改用 `resolve_existing_path()`；自動產生的輸出檔名改為乾淨版本 |
| `download_cli.py` | CLI 下載指令 | 帶入清洗參數 |
| `.claude/skills/media-processor/scripts/path_utils.py` | 新增 | 技能腳本用的獨立版本（不依賴專案 `utils/`） |
| `.claude/skills/media-processor/scripts/*.py` | 4 支腳本的檔案驗證 | 改用 `resolve_existing_path()` |

技能腳本是以 `python scripts/xxx.py` 直接執行，腳本所在目錄會自動進 `sys.path`，因此 `from path_utils import ...` 可行，毋須改動 `sys.path`。該檔刻意與 `utils/sanitizer.py` 重複一份，以維持技能包可獨立搬移的特性。

---

## 驗證

**治本** — 以原始問題影片（`NRrAAa7CHQM`）`--simulate` 實測輸出檔名：

```
BEFORE -> '睡前故事 EP143 《我從哪裡來？》\xa0生命教育｜兒童性教育｜家庭生活.webm'
AFTER  -> '睡前故事 EP143 《我從哪裡來？》 生命教育｜兒童性教育｜家庭生活.webm'
```

**治標** — 建立真實含 NBSP 的測試檔 `測試 影片\xa0標題.mp4`，以「使用者打出來的半形空格版本」呼叫：

| 呼叫端 | 結果 |
|--------|------|
| `os.path.exists()`（對照組） | `False` ✅ 確認情境成立 |
| `resolve_existing_path()` | 正確回傳含 `\xa0` 的真實路徑 ✅ |
| MCP `convert_to_mp3` | 轉檔成功，且輸出檔名為乾淨的 `測試 影片 標題.mp3` ✅ |
| `convert_audio.py` / `extract_audio.py` | 轉檔成功 ✅ |

**未被放寬** — 真正不存在的檔案仍正確報錯，沒有因為放寬比對而誤判：

| 情境 | 結果 |
|------|------|
| 同目錄下不存在的檔名 | `FILE_NOT_FOUND` ✅ |
| 不存在的目錄 | `None` ✅ |

全部異動檔案通過 `py_compile` 與 import 檢查。

---

## 注意事項

- **MCP server 需重啟才會生效**，Claude Desktop 會沿用啟動時載入的 `server.py`
- 本次修正**不會自動改名既有檔案**。`download_history.json` 中既有的 2 筆紀錄與磁碟上對應檔案仍帶 `\xa0`，靠 `resolve_existing_path()` 兜底處理；如需徹底清理必須手動改名
- `resolve_existing_path()` 的最後一段會**逐一列出父目錄**做比對，僅在前面的快速路徑全部失敗時才觸發；極大型目錄下有效能成本，但屬於例外路徑，正常情況第一行 `exists()` 就返回
- 比對**刻意不做大小寫折疊**（casefold）。放寬到那個程度可能選到另一個實際存在的不同檔案，寧可回報找不到也不要處理錯檔案
- 同類風險尚存於**未經 `sanitize_filename()` 的其他落地路徑**。日後新增任何「由外部 metadata 決定檔名」的功能時，應一律走 `sanitize_filename()` 或 `filename_cleanup_args()`

---

## 相關檔案

```
utils/sanitizer.py                  # 正規化與路徑解析 helper
utils/path_resolver.py              # yt-dlp 檔名清洗參數
server.py                           # MCP download_media / convert_to_mp3
download_cli.py                     # CLI 下載
.claude/skills/media-processor/scripts/path_utils.py   # 技能腳本獨立版本
docs/issues/ISSUE-003-YouTube-403-Player-Client.md     # 同樣出在 yt-dlp 指令組裝
docs/issues/ISSUE-005-Case-Insensitive-Path-Comparison-Data-Loss.md   # 本次新增的 in_place 防護沿用字串比較，未能攔下同檔覆寫
```

## 參考資料

- [yt-dlp — `--replace-in-metadata`](https://github.com/yt-dlp/yt-dlp#modifying-metadata)
- [Unicode UAX #15 — Normalization Forms](https://unicode.org/reports/tr15/)
