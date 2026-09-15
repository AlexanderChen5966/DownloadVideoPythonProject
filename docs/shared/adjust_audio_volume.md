# P4：音量調整工具（adjust_audio）

> **狀態：🔸 部分完成**（任務 2 已實作；任務 1 `adjust_audio` 仍待實作）
> **優先級：P4（功能擴充）**
> **建立日期：2026-05-19**
> **完成日期：任務 2 於 2026-09-15 完成**
> **實際影響檔案：2 個**（`server.py`、`utils/loudnorm.py`）
> **前置依賴：P0–P3 皆已完成**

---

## 需求描述

部分音檔原始音量過小，播放時需要手動調大。需要一個 MCP 工具，讓 Agent 可以直接對現有音檔調整音量或進行響度正規化，輸出覆蓋原檔或存為新檔。

## 目標

- 新增 `adjust_audio` MCP tool（第 9 個工具）
- 支援三種模式：固定增益、響度正規化、動態正規化
- 同時在 `convert_to_mp3` 新增 `normalize` 可選參數，轉換時一步到位

---

## 影響範圍分析

| 檔案 | 修改原因 |
|------|---------|
| `server.py` | 新增 `adjust_audio` tool、在 `convert_to_mp3` 加 `normalize` 參數 |
| `utils/loudnorm.py` | 兩趟式 loudnorm 的量測與濾鏡組裝（任務 2 實作時新增） |

> 原規劃為「不需新增 utils 檔案，FFmpeg 指令直接在 server.py 組裝」。實作任務 2 時改為抽出 `utils/loudnorm.py`：兩趟式流程包含 JSON 量測結果解析與靜音判斷，約 60 行，放在 server.py 會淹沒工具函式本身；且任務 1 的 `loudnorm` 模式可直接共用同一份量測邏輯。

---

## 實作任務

### 任務 1：新增 `adjust_audio` MCP tool ⏳ 待實作

> ⚠️ **實作前必讀**：下方程式碼撰寫於 2026-05-19，早於兩次同類缺陷的修正。實作時必須一併套用，否則會重蹈覆轍：
>
> | 項目 | 下方原始設計 | 必須改為 | 出處 |
> |------|------------|---------|------|
> | 檔案存在檢查 | `os.path.exists(input_file)` | `resolve_existing_path(input_file)` | [ISSUE-004](../issues/ISSUE-004-Invisible-Whitespace-In-Filenames.md)：檔名含不可見空白時會誤判為不存在 |
> | 是否覆蓋原檔 | `output_file == input_file` 之類的字串比較 | `os.path.samefile()` | [ISSUE-005](../issues/ISSUE-005-Case-Insensitive-Path-Comparison-Data-Loss.md)：不分大小寫的檔案系統上會讓 FFmpeg 同時讀寫同一檔案，銷毀原檔 |
> | `loudnorm` 模式 | 單趟 `loudnorm` | 共用 `utils/loudnorm.py` 的兩趟式流程 | 見下方任務 2：單趟會把動態範圍壓掉一半 |
>
> 本工具預設「覆蓋原檔」，是全專案**唯一**會就地改寫使用者原始檔案的功能，上述第二項尤其關鍵。

在 `server.py` 的 `convert_to_mp3` 工具之後插入，套用現有的 `@mcp.tool()` 裝飾器和 `success_response` / `error_response` 回傳結構。

#### 工具簽名

```python
@mcp.tool()
async def adjust_audio(
    input_file: str,
    output_file: str = None,
    mode: Literal["volume", "loudnorm", "dynaudnorm"] = "loudnorm",
    volume_multiplier: float = 2.0,
) -> dict:
    """
    調整音檔音量或進行響度正規化

    Args:
        input_file: 輸入音檔路徑（支援 mp3, m4a, wav, opus, flac 等）
        output_file: 輸出路徑（選填，預設覆蓋原檔）
        mode: 調整模式
            - 'volume'    : 固定倍增，volume_multiplier 倍（如 2.0 = 音量加倍）
            - 'loudnorm'  : EBU R128 響度正規化，目標 -23 LUFS（廣播標準，最常用）
            - 'dynaudnorm': 動態正規化，保留動態範圍但整體提升
        volume_multiplier: 僅 mode='volume' 時有效，預設 2.0

    Returns:
        調整結果字典，包含 input_file、output_file、mode、file_size
    """
```

#### FFmpeg 指令對應

| mode | FFmpeg filter |
|------|--------------|
| `volume` | `-filter:a "volume={volume_multiplier}"` |
| `loudnorm` | `-filter:a loudnorm` |
| `dynaudnorm` | `-filter:a dynaudnorm` |

#### 完整實作

```python
@mcp.tool()
async def adjust_audio(
    input_file: str,
    output_file: str = None,
    mode: Literal["volume", "loudnorm", "dynaudnorm"] = "loudnorm",
    volume_multiplier: float = 2.0,
) -> dict:
    if not os.path.exists(input_file):
        return error_response("FILE_NOT_FOUND", f"輸入檔案不存在: {input_file}", input_file=input_file)

    if output_file is None:
        output_file = input_file  # 預設覆蓋原檔

    if mode == "volume":
        audio_filter = f"volume={volume_multiplier}"
    elif mode == "loudnorm":
        audio_filter = "loudnorm"
    elif mode == "dynaudnorm":
        audio_filter = "dynaudnorm"
    else:
        return error_response("INVALID_MODE", f"不支援的模式: {mode}")

    # 若覆蓋原檔，先輸出到暫存檔再替換
    import tempfile
    overwrite = (os.path.abspath(input_file) == os.path.abspath(output_file))
    if overwrite:
        suffix = Path(input_file).suffix
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp_path = tmp.name
        tmp.close()
        target = tmp_path
    else:
        target = output_file

    try:
        cmd = [
            "ffmpeg", "-i", input_file,
            "-filter:a", audio_filter,
            "-y", target
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        if overwrite:
            os.replace(tmp_path, output_file)

        return success_response(
            input_file=input_file,
            output_file=output_file,
            mode=mode,
            file_size=os.path.getsize(output_file)
        )
    except subprocess.CalledProcessError as e:
        if overwrite and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return error_response("ADJUST_FAILED", str(e), stderr=e.stderr)
    except Exception as e:
        if overwrite and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return error_response("UNKNOWN_ERROR", str(e))
```

---

### 任務 2：在 `convert_to_mp3` 加入 `normalize` 參數 ✅ 已完成（2026-09-15）

讓轉換和正規化可以一步完成。真正的效益不只是少一個步驟——若先轉 MP3 再正規化，等於解碼後重新編碼一次，會多掉一代音質；合併在同一個 FFmpeg 流程則是直接從原始來源一次編碼到位。

> ⚠️ **實作時修正了下方的原始設計：改用兩趟式 loudnorm。**
>
> 原規劃的 `-filter:a loudnorm` 是**單趟**模式，為串流設計、無法預看全檔，會以動態增益逐段調整，等同輕度壓縮。實測（響度起伏 -40dB → -6dB 的素材）：
>
> | 作法 | 成品響度 | 動態範圍 LRA |
> |------|---------|-------------|
> | 來源 | -28.11 LUFS | 4.80 LU |
> | 單趟（原規劃） | -23.14 LUFS | **2.40 LU ← 動態被壓掉一半** |
> | 兩趟 `linear=true`（實作版） | -23.00 LUFS | **4.80 LU ← 完整保留** |
>
> 目標響度的準確度兩者差距不大（0.14 vs 0.00 dB），**真正的差異在動態保留**。單趟會不請自來地壓縮動態，改變旁白的聲音表情；兩趟以線性增益達成目標，只搬移音量、不改變動態。
>
> 實際實作見 `utils/loudnorm.py` 與 `server.py` 的 `convert_to_mp3`，下方原始程式碼僅保留作為設計沿革。

#### 修改前（server.py:318–360）

```python
async def convert_to_mp3(
    input_file: str,
    output_file: str = None,
    quality: int = 2
) -> dict:
    ...
    cmd = [
        "ffmpeg", "-i", input_file,
        "-vn", "-codec:a", "libmp3lame",
        "-qscale:a", str(quality), "-y",
        output_file
    ]
```

#### 修改後

```python
async def convert_to_mp3(
    input_file: str,
    output_file: str = None,
    quality: int = 2,
    normalize: bool = False,
) -> dict:
    ...
    cmd = [
        "ffmpeg", "-i", input_file,
        "-vn", "-codec:a", "libmp3lame",
        "-qscale:a", str(quality),
    ]
    if normalize:
        cmd.extend(["-filter:a", "loudnorm"])
    cmd.extend(["-y", output_file])
```

---

## 錯誤碼

| error_code | 觸發條件 |
|-----------|---------|
| `FILE_NOT_FOUND` | input_file 路徑不存在 |
| `INVALID_MODE` | mode 不在 volume/loudnorm/dynaudnorm 三個值內 |
| `ADJUST_FAILED` | FFmpeg CalledProcessError（格式不支援、編解碼錯誤等） |
| `UNKNOWN_ERROR` | 其他未預期例外 |

---

## 邊界條件

| 情況 | 處理方式 |
|------|---------|
| `output_file` 未指定 | 覆蓋原檔（先寫暫存檔再 os.replace 確保原子性） |
| `mode='volume'` 但 `volume_multiplier` 未給 | 預設 2.0（約 +6 dB）|
| `volume_multiplier=1.0` | FFmpeg 正常執行但音量不變，允許（使用者自行決定） |
| 輸入檔非音訊格式（如 .jpg）| FFmpeg 會拋錯，由 `ADJUST_FAILED` 捕捉 |
| `loudnorm` 對已正規化的檔案執行 | 安全，FFmpeg 會重新分析並輸出 |

---

## 白名單

`adjust_audio` 處理本機檔案，**不涉及網路請求**，不需要白名單檢查。

---

## 驗證清單

- [ ] `mode='loudnorm'`：loudnorm 模式正常執行，輸出檔可播放
- [ ] `mode='volume', volume_multiplier=2.0`：音量明顯變大，與原檔比較
- [ ] `mode='dynaudnorm'`：dynaudnorm 模式正常執行
- [ ] `output_file=None`：原檔被覆蓋，不殘留暫存檔
- [ ] 指定 `output_file` 路徑：新檔建立，原檔不變
- [ ] 輸入檔不存在：回傳 `error_code=FILE_NOT_FOUND`
- [ ] `convert_to_mp3` + `normalize=True`：輸出 MP3 音量明顯正規化
- [ ] `convert_to_mp3` + `normalize=False`（預設）：行為與原本相同

---

## README 更新提示

實作完成後，`README.md` 的 MCP 工具一覽表需新增一行：

```markdown
| `adjust_audio` | 調整音檔音量（固定增益 / EBU R128 響度正規化 / 動態正規化） |
```

並在功能特色加入「**音量調整**：支援固定增益、響度正規化（EBU R128）、動態正規化」。
