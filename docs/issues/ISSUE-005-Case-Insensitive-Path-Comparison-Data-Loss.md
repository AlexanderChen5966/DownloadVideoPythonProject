# ISSUE-005: 路徑字串比較在不分大小寫檔案系統上失效，導致音檔內容被銷毀

> **狀態：** ✅ 已解決
> **建立日期：** 2026-09-15
> **分類：** 資料完整性 / 檔案系統相容性
> **嚴重性：** 🔴 高——會無聲銷毀使用者原始檔案，且工具回報成功

---

## 問題描述

對副檔名為大寫的 `.MP3` 檔案呼叫 `convert_to_mp3`，原始檔案內容會被大量銷毀：

```
轉檔前: 2760832 bytes, 600.0 秒
轉檔後:   32262 bytes,   6.9 秒
```

**98.8% 的音訊資料消失，而工具回傳 `success=True`。**

### 關鍵症狀：沒有任何錯誤訊息

FFmpeg 正常結束、回傳碼為 0，工具回報成功，錯誤只能靠事後播放或檢查檔案大小才會發現。這個特徵是本問題最危險之處——它排除了「轉檔失敗」的直覺判斷，使用者不會知道原始檔已經回不來了。

檔案越大破壞越嚴重：

| 來源長度 | 轉檔前 | 轉檔後 | 結果 |
|---------|--------|--------|------|
| 3 秒 | 24467 bytes | 14503 bytes | 僥倖存活，但被無聲重新編碼（多掉一代音質） |
| 600 秒 | 2760832 bytes | 32262 bytes | **僅剩 6.9 秒，內容實質全毀** |

---

## 根本原因

macOS 預設的 APFS 是**不分大小寫（case-insensitive）但保留大小寫**的檔案系統。`song.MP3` 與 `song.mp3` 指向**同一個實體檔案**，但作為 Python 字串並不相等。

`convert_to_mp3` 用字串比較判斷輸入與輸出是否為同一檔案，兩道防線因此同時失效：

```python
# 防線 1：已是 MP3 就免轉檔
if input_file.lower().endswith('.mp3') and input_file == output_file:
    return success_response(message="檔案已經是 MP3 格式", ...)
#                            ^^^^^^^^^^^^^^^^^^^^^^^^^^
#   "song.MP3" != "song.mp3" → 判定為不同檔案 → 未攔截

# 防線 2：同路徑時改走暫存檔
in_place = os.path.abspath(output_file) == os.path.abspath(input_file)
#          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   abspath 只做路徑正規化，不解析大小寫 → 同樣判定為不同檔案 → 未攔截
```

兩道防線都放行後，實際執行的指令變成：

```
ffmpeg -i song.MP3 ... -y song.mp3     # 讀與寫指向同一個 inode
```

FFmpeg 一邊讀取來源、一邊以 `-y` 覆寫同一個檔案。小檔案可能整份落在 I/O 緩衝內而僥倖存活，大檔案則在讀到一半時來源已被自己的輸出覆蓋，於是提早結束並留下截斷的成品。

> ⚠️ **這是既有缺陷，不是 [ISSUE-004](ISSUE-004-Invisible-Whitespace-In-Filenames.md) 修正時引入的。** 原始碼一直使用 `input_file == output_file`。但 ISSUE-004 為了支援就地正規化而新增的 `in_place` 判斷，本應攔下這個情境卻沿用了字串比較，等於錯過一次攔截機會。**新增防護時若沿用既有的錯誤前提，防護本身也會失效。**

### 為何 `abspath` 不夠

| 方法 | 解析符號連結 | 解析大小寫 | 偵測硬連結 |
|------|------------|-----------|-----------|
| `a == b` | ❌ | ❌ | ❌ |
| `os.path.abspath(a) == os.path.abspath(b)` | ❌ | ❌ | ❌ |
| `os.path.realpath(a) == os.path.realpath(b)` | ✅ | ❌ | ❌ |
| **`os.path.samefile(a, b)`** | ✅ | ✅ | ✅ |

`abspath` 只做語法層級的路徑正規化（處理 `..`、相對路徑），完全不接觸檔案系統。`samefile` 比對的是 `st_dev` 與 `st_ino`，也就是**實體檔案身分**，因此能一併涵蓋大小寫、符號連結與硬連結三種情況。

---

## 解決方案

改用 `os.path.samefile()`，並將判斷**提前到兩道防線之前**共用，避免兩處各自實作而再次分歧。

```python
# 必須用 samefile 而非字串比較：macOS 預設的檔案系統不分大小寫，
# song.MP3 與 song.mp3 是同一個檔案，字串比較會讓 FFmpeg 同時讀寫同一檔案而毀損內容
in_place = os.path.exists(output_file) and os.path.samefile(input_file, output_file)

if not normalize and in_place and input_file.lower().endswith('.mp3'):
    return success_response(message="檔案已經是 MP3 格式", ...)
```

`samefile` 要求兩個路徑都存在，故以 `os.path.exists(output_file)` 前置守衛；`input_file` 在此之前已由 `resolve_existing_path()` 確認存在。

### 修改檔案

| 檔案 | 位置 | 說明 |
|------|------|------|
| `server.py` | `convert_to_mp3` | `in_place` 改用 `samefile`，並提前至「免轉檔」判斷之前共用 |

---

## 驗證

三種副檔名寫法皆以 60 秒 MP3（480461 bytes）測試，確認原檔完好且走到正確分支：

| 輸入 | 轉檔前 | 轉檔後 | 結果 |
|------|--------|--------|------|
| `case.MP3` | 480461 | 480461 | ✅ 「檔案已經是 MP3 格式」 |
| `case.Mp3` | 480461 | 480461 | ✅ 「檔案已經是 MP3 格式」 |
| `case.mp3` | 480461 | 480461 | ✅ 「檔案已經是 MP3 格式」 |

搭配 `normalize=True`（此時不會提早返回，必須實際走暫存檔流程）：

- `BIG.MP3` 600.0 秒 → 成品 600.0 秒，長度完整保留 ✅
- 無殘留 `.tmp.mp3` 暫存檔 ✅

回歸測試確認既有行為未受影響：一般轉檔、`normalize=True`、預設輸出路徑、`FILE_NOT_FOUND`、`NORMALIZE_FAILED` 全數正常；正規化準確度維持 -23.00 LUFS。

**全專案排查**：`grep` 確認沒有其他地方以字串比較判斷輸入輸出是否同檔，`os.replace` 也僅此一處使用。

---

## 注意事項

- **MCP server 需重啟才會生效**，Claude Desktop 會沿用啟動時載入的 `server.py`
- **已受損的檔案無法復原**。本修正只能防止再次發生；若曾對大寫副檔名的 MP3 執行過轉檔，該檔案的內容已永久遺失，需從原始來源重新取得
- 本問題**只在不分大小寫的檔案系統上出現**。Linux（ext4/xfs）預設區分大小寫，同樣的程式碼在該環境下不會觸發，因此**無法靠 Linux CI 發現**——這類缺陷必須在 macOS 或 Windows 上實測
- 日後任何「判斷兩個路徑是否指向同一檔案」的需求，一律使用 `os.path.samefile()`，不要用 `==`、`abspath` 或 `realpath`
- 若未來新增其他會就地覆寫檔案的工具（例如 P4 規劃中的 `adjust_audio`，其設計為「覆蓋原檔」），必須套用同一套 `samefile` + 暫存檔 + `os.replace` 流程

---

## 相關檔案

```
server.py                    # convert_to_mp3 的 in_place 判斷
docs/issues/ISSUE-004-Invisible-Whitespace-In-Filenames.md   # 同一函式的前一次修正，新增的防護沿用了錯誤前提
docs/shared/adjust_audio_volume.md                           # P4：adjust_audio 同樣會就地覆寫，需套用相同流程
```

## 參考資料

- [Python 文件 — `os.path.samefile`](https://docs.python.org/3/library/os.path.html#os.path.samefile)
- [Apple — APFS 的大小寫敏感性](https://support.apple.com/guide/disk-utility/file-system-formats-dsku19ed921c/mac)
