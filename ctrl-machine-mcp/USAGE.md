# MCP Servers 사용 가이드

## 🚀 빠른 시작

### 1. 설치 및 설정
```bash
# 1. Docker 컨테이너 실행
docker-compose up -d

# 2. MCP 설정 스크립트 실행
./setup_mcp.sh
```

### 2. Claude Code 설정 확인
```bash
# 설정 파일 위치
cat ~/.claude/claude_code_config.json
```

## 📝 Claude Code에서 사용하기

### MCP 서버 확인
Claude Code에서 다음 명령어로 연결된 MCP 서버를 확인:
```
/mcp
```

출력 예시:
```
Available MCP servers:
• hid-input-mcp - Hardware input control
• screenshot-mcp - Screen capture
```

### 사용 예시

#### 1. 스크린샷 캡처
```
화면을 캡처해줘
```
Claude가 자동으로 `screenshot-mcp` 서버의 `capture_screenshot` 도구를 호출합니다.

#### 2. 마우스 이동
```
마우스를 화면 중앙으로 이동시켜줘
```
Claude가 `hid-input-mcp` 서버의 `move_mouse` 도구를 호출합니다.

#### 3. 텍스트 입력
```
"Hello World"를 타이핑해줘
```
Claude가 `hid-input-mcp` 서버의 `type_text` 도구를 호출합니다.

## 🛠 직접 도구 호출하기

### HID Input MCP 도구들

```python
# 마우스 이동
mcp://hid-input-mcp/move_mouse?x=500&y=300

# 클릭
mcp://hid-input-mcp/click_mouse?x=500&y=300&button=left

# 텍스트 입력
mcp://hid-input-mcp/type_text?text=Hello&simulate_human=true

# 키 조합
mcp://hid-input-mcp/press_key?key=s&modifiers=["ctrl"]
```

### Screenshot MCP 도구들

```python
# 전체 화면 캡처
mcp://screenshot-mcp/capture_screenshot?mode=full_screen

# 특정 영역 캡처
mcp://screenshot-mcp/capture_screenshot?mode=region&region={"x":100,"y":100,"width":800,"height":600}

# 주기적 캡처 시작
mcp://screenshot-mcp/start_periodic_capture?interval=2.0

# 주기적 캡처 중지
mcp://screenshot-mcp/stop_periodic_capture
```

## 🔍 디버깅

### 컨테이너 상태 확인
```bash
docker ps
docker logs mcp-unified
```

### VNC로 화면 보기
```bash
# macOS
open vnc://localhost:5900

# 비밀번호는 .env 파일 확인
cat .env | grep VNC_PASSWORD
```

### MCP 서버 테스트
```bash
# HID 기능 테스트
docker exec mcp-unified python3 -c "import pyautogui; print(pyautogui.size())"

# 스크린샷 기능 테스트
docker exec mcp-unified python3 -c "import mss; with mss.mss() as s: print(len(s.monitors))"
```

## ⚠️ 주의사항

1. **Docker 컨테이너가 실행 중이어야 함**
   ```bash
   docker-compose up -d
   ```

2. **Claude Code 재시작 필요**
   - 설정 파일 수정 후 Claude Code를 재시작해야 적용됨

3. **권한 문제**
   - macOS: Docker Desktop이 접근성 권한을 가지고 있어야 함
   - Linux: 사용자가 docker 그룹에 속해 있어야 함

## 🐛 문제 해결

### MCP 서버가 보이지 않을 때
1. Claude Code 재시작
2. 설정 파일 확인: `~/.claude/claude_code_config.json`
3. Docker 컨테이너 실행 확인: `docker ps`

### 연결 오류 발생 시
```bash
# 컨테이너 재시작
docker-compose restart

# 로그 확인
docker logs mcp-unified
```

### VNC 연결 실패 시
1. 포트 5900이 사용 중인지 확인
2. 비밀번호 확인: `cat .env`
3. 방화벽 설정 확인