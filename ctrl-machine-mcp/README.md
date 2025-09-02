# Control Machine MCP Servers

Claude Code와 연동하여 컴퓨터 자동화를 위한 두 가지 독립적인 MCP(Model Control Protocol) 서버를 제공합니다.

## 🎯 개요

이 프로젝트는 Claude Code의 자동화 기능을 확장하기 위해 두 가지 핵심 MCP 서버를 구현합니다:

1. **HID Input MCP Server** - 하드웨어 수준의 키보드/마우스 입력 제어
2. **Screenshot MCP Server** - 주기적/이벤트 기반 화면 캡처 및 분석

## 📋 시스템 요구사항

- Python 3.8 이상
- macOS, Windows, 또는 Linux
- Claude Code 또는 MCP 호환 클라이언트

### 플랫폼별 추가 요구사항

**macOS:**
- 접근성 권한 필요 (시스템 환경설정 > 보안 및 개인정보 보호 > 접근성)

**Windows:**
- 관리자 권한으로 실행 권장

**Linux:**
- X11 또는 Wayland
- xdotool 설치 필요 (브라우저 창 캡처용)

## 🚀 설치

### 1. 의존성 설치

```bash
cd ctrl-machine-mcp
pip install -r requirements.txt
```

### 2. MCP 서버 등록

Claude Code 설정 파일(~/.claude/claude_code_config.json)에 다음 내용을 추가:

```json
{
  "mcpServers": {
    "hid-input-mcp": {
      "command": "python",
      "args": ["/path/to/ctrl-machine-mcp/hid_input_mcp.py"]
    },
    "screenshot-mcp": {
      "command": "python",
      "args": ["/path/to/ctrl-machine-mcp/screenshot_mcp.py"]
    }
  }
}
```

또는 제공된 `mcp_config.json` 파일을 참조하여 설정할 수 있습니다.

## 💻 HID Input MCP Server

하드웨어 입력 장치를 직접 제어하여 물리적인 키보드/마우스 입력을 생성합니다.

### 주요 기능

- **마우스 제어**
  - 절대 위치 이동
  - 클릭 (좌/우/중간 버튼, 다중 클릭)
  - 드래그 앤 드롭
  - 스크롤

- **키보드 제어**
  - 텍스트 입력
  - 단일 키 입력
  - 조합 키 (Ctrl+C, Alt+Tab 등)
  - 인간과 유사한 타이핑 시뮬레이션

### 사용 가능한 도구

| 도구 이름 | 설명 | 주요 매개변수 |
|----------|------|--------------|
| `move_mouse` | 마우스를 절대 위치로 이동 | x, y, duration |
| `click_mouse` | 마우스 버튼 클릭 | x, y, button, clicks |
| `drag_mouse` | 마우스 드래그 | start_x, start_y, end_x, end_y |
| `scroll_mouse` | 마우스 휠 스크롤 | x, y, direction, clicks |
| `type_text` | 텍스트 입력 | text, interval, simulate_human |
| `press_key` | 키 입력 | key, modifiers |
| `get_mouse_position` | 현재 마우스 위치 조회 | - |
| `get_event_history` | 입력 이벤트 기록 조회 | limit |

### 사용 예시

```python
# Claude Code에서 사용 예시
# 1. 마우스를 (500, 300) 위치로 이동
await mcp.call_tool("hid-input-mcp", "move_mouse", {"x": 500, "y": 300})

# 2. 더블 클릭
await mcp.call_tool("hid-input-mcp", "click_mouse", {"x": 500, "y": 300, "clicks": 2})

# 3. 텍스트 입력 (인간처럼)
await mcp.call_tool("hid-input-mcp", "type_text", {
    "text": "Hello, World!",
    "simulate_human": true
})

# 4. 단축키 실행 (Ctrl+S)
await mcp.call_tool("hid-input-mcp", "press_key", {
    "key": "s",
    "modifiers": ["ctrl"]
})
```

## 📸 Screenshot MCP Server

화면 캡처 기능을 제공하며, 주기적 캡처와 특정 영역/창 캡처를 지원합니다.

### 주요 기능

- **캡처 모드**
  - 전체 화면
  - 특정 모니터
  - 활성 창
  - 브라우저 창
  - 사용자 정의 영역

- **주기적 캡처**
  - 설정 가능한 간격 (초 단위)
  - 백그라운드 실행
  - 자동 히스토리 관리

### 사용 가능한 도구

| 도구 이름 | 설명 | 주요 매개변수 |
|----------|------|--------------|
| `capture_screenshot` | 단일 스크린샷 캡처 | mode, monitor_index, region |
| `start_periodic_capture` | 주기적 캡처 시작 | interval, mode |
| `stop_periodic_capture` | 주기적 캡처 중지 | - |
| `get_capture_status` | 캡처 상태 조회 | - |
| `get_latest_screenshot` | 최신 스크린샷 조회 | - |
| `find_browser_windows` | 브라우저 창 검색 | - |
| `clear_history` | 캡처 기록 삭제 | - |

### 사용 예시

```python
# Claude Code에서 사용 예시
# 1. 전체 화면 캡처
screenshot = await mcp.call_tool("screenshot-mcp", "capture_screenshot", {
    "mode": "full_screen"
})

# 2. 브라우저 창 캡처
browsers = await mcp.call_tool("screenshot-mcp", "find_browser_windows", {})
screenshot = await mcp.call_tool("screenshot-mcp", "capture_screenshot", {
    "mode": "browser",
    "browser_index": 0
})

# 3. 주기적 캡처 시작 (2초 간격)
await mcp.call_tool("screenshot-mcp", "start_periodic_capture", {
    "interval": 2.0,
    "mode": "active_window"
})

# 4. 특정 영역 캡처
screenshot = await mcp.call_tool("screenshot-mcp", "capture_screenshot", {
    "mode": "region",
    "region": {
        "x": 100,
        "y": 100,
        "width": 800,
        "height": 600
    }
})
```

## 🔧 설정

### 환경 변수

```bash
# 로깅 레벨 설정
export MCP_LOG_LEVEL=INFO

# Python 버퍼링 비활성화 (실시간 출력)
export PYTHONUNBUFFERED=1
```

### 설정 파일 (mcp_config.json)

```json
{
  "settings": {
    "screenshot": {
      "default_interval": 1.0,
      "max_history": 50,
      "default_mode": "full_screen"
    },
    "hid_input": {
      "safety_enabled": true,
      "default_typing_interval": 0.0,
      "human_simulation": false
    }
  }
}
```

## 🧪 테스트

```bash
# 단위 테스트 실행
pytest test_mcp_servers.py -v

# 특정 테스트만 실행
pytest test_mcp_servers.py::TestHIDInputController -v

# 커버리지 리포트 생성
pytest test_mcp_servers.py --cov=. --cov-report=html
```

## 📝 실제 사용 시나리오

### 시나리오 1: 웹 자동화

```python
# 1. 브라우저 창 찾기
browsers = await find_browser_windows()

# 2. 첫 번째 브라우저 스크린샷
await capture_screenshot(mode="browser", browser_index=0)

# 3. 검색창 클릭
await click_mouse(x=500, y=100)

# 4. 검색어 입력
await type_text("Claude Code MCP automation")

# 5. Enter 키 입력
await press_key("enter")

# 6. 결과 화면 캡처
await capture_screenshot(mode="browser")
```

### 시나리오 2: 모니터링

```python
# 1. 주기적 캡처 시작 (5초 간격)
await start_periodic_capture(interval=5.0, mode="full_screen")

# 2. 10분 동안 모니터링
await asyncio.sleep(600)

# 3. 캡처 중지
await stop_periodic_capture()

# 4. 캡처 기록 확인
status = await get_capture_status()
print(f"Captured {status['history_count']} screenshots")
```

## 🔐 보안 고려사항

1. **권한 관리**
   - macOS: 접근성 권한 필요
   - Windows: 관리자 권한 권장
   - Linux: X11 접근 권한 필요

2. **안전 기능**
   - PyAutoGUI FAILSAFE 활성화 (마우스를 화면 모서리로 이동시 중지)
   - 이벤트 로깅 및 추적
   - 최대 히스토리 제한

3. **민감 정보 보호**
   - 스크린샷에 민감 정보 포함 가능
   - 캡처 데이터는 메모리에만 저장
   - 필요시 히스토리 삭제 기능 제공

## 🤝 기여

기여를 환영합니다! 다음 절차를 따라주세요:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🆘 문제 해결

### macOS에서 권한 오류

시스템 환경설정 > 보안 및 개인정보 보호 > 접근성에서 터미널 또는 Python에 권한을 부여하세요.

### Windows에서 클릭이 작동하지 않음

관리자 권한으로 실행하거나 UAC 설정을 확인하세요.

### Linux에서 창 캡처 실패

```bash
sudo apt-get install xdotool  # Ubuntu/Debian
sudo yum install xdotool      # CentOS/RHEL
```

### ImportError 발생

```bash
pip install --upgrade -r requirements.txt
```

## 📚 참고 자료

- [MCP Protocol Documentation](https://github.com/anthropics/mcp)
- [PyAutoGUI Documentation](https://pyautogui.readthedocs.io/)
- [MSS Documentation](https://python-mss.readthedocs.io/)
- [Pynput Documentation](https://pynput.readthedocs.io/)