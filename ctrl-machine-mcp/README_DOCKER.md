# Docker MCP Servers for Claude Code

HTTP 기반 MCP 서버를 Docker 컨테이너에서 실행하여 Claude Code와 연동합니다.

## 기능

- **Screenshot MCP**: 화면 캡처 및 시각 정보 처리
- **HID Input MCP**: 마우스/키보드 입력 제어
- **VNC Access**: 원격 데스크톱 접속 (포트 5900)

## 빠른 시작

### 1. 현재 실행 중인 컨테이너 사용

```bash
# HTTP 서버가 이미 실행 중인지 확인
curl http://localhost:8080/health
curl http://localhost:8081/health
```

### 2. Claude Code에 MCP 서버 등록

```bash
# Claude Code에서 사용
claude --mcp-config ctrl-machine-mcp/mcp_docker_config.json
```

또는 `~/.claude.json`에 직접 추가:

```json
{
  "mcpServers": {
    "docker-screenshot-mcp": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    },
    "docker-hid-mcp": {
      "type": "http",
      "url": "http://localhost:8081/mcp"
    }
  }
}
```

## Docker 컨테이너 관리

### 컨테이너 시작

```bash
# 기존 컨테이너 확인
docker ps -a | grep mcp

# 컨테이너가 중지된 경우 재시작
docker start mcp-unified

# HTTP 서버 시작 (컨테이너 내부)
docker exec -d mcp-unified python3 /app/screenshot_mcp_http.py
docker exec -d mcp-unified python3 /app/hid_input_mcp_http.py
```

### 새 컨테이너 빌드 및 실행

```bash
# Docker Compose 사용 (권장)
docker-compose -f docker-compose-http.yml up -d

# 또는 수동 빌드
docker build -f Dockerfile.http -t mcp-http:latest .
docker run -d \
  --name mcp-http \
  -e VNC_PASSWORD=your_password \
  -p 5900:5900 \
  -p 8080:8080 \
  -p 8081:8081 \
  mcp-http:latest
```

## VNC 접속

```bash
# macOS
open vnc://localhost:5900

# 암호: 환경변수 VNC_PASSWORD 또는 기본값 'mcp123'
```

## API 엔드포인트

### Screenshot MCP (포트 8080)

- `GET /health` - 헬스 체크
- `GET /tools` - 사용 가능한 도구 목록
- `POST /capture` - 스크린샷 캡처
- `POST /mcp` - MCP 프로토콜 요청

### HID Input MCP (포트 8081)

- `GET /health` - 헬스 체크
- `GET /tools` - 사용 가능한 도구 목록
- `POST /click` - 마우스 클릭
- `POST /move` - 마우스 이동
- `POST /type` - 텍스트 입력
- `POST /press` - 키 입력
- `POST /hotkey` - 단축키
- `POST /mcp` - MCP 프로토콜 요청

## 테스트

```bash
# 스크린샷 캡처 테스트
curl -X POST http://localhost:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"region": {"top": 0, "left": 0, "width": 1920, "height": 1080}}'

# 마우스 클릭 테스트
curl -X POST http://localhost:8081/click \
  -H "Content-Type: application/json" \
  -d '{"x": 100, "y": 100, "button": "left"}'

# 텍스트 입력 테스트
curl -X POST http://localhost:8081/type \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from MCP!", "interval": 0.05}'
```

## 환경 변수

- `VNC_PASSWORD`: VNC 접속 암호 (기본값: 없음)
- `LANG`: ko_KR.UTF-8 (한국어 설정)
- `DISPLAY`: :99 (가상 디스플레이)
- `SCREENSHOT_MCP_PORT`: 8080
- `HID_MCP_PORT`: 8081

## 문제 해결

### 컨테이너 로그 확인

```bash
docker logs mcp-unified
docker exec mcp-unified ps aux | grep python
```

### HTTP 서버 재시작

```bash
# 프로세스 확인
docker exec mcp-unified ps aux | grep mcp_http

# 프로세스 종료 후 재시작
docker exec mcp-unified pkill -f mcp_http
docker exec -d mcp-unified python3 /app/screenshot_mcp_http.py
docker exec -d mcp-unified python3 /app/hid_input_mcp_http.py
```

### 권한 설정

Claude Code의 설정에서 다음 도구들을 허용해야 합니다:

- `mcp__docker-screenshot-mcp__capture_screenshot`
- `mcp__docker-hid-mcp__click_mouse`
- `mcp__docker-hid-mcp__type_text`
- `mcp__docker-hid-mcp__press_key`

## 보안 주의사항

- VNC 암호를 설정하여 무단 접근을 방지하세요
- 프로덕션 환경에서는 방화벽 규칙을 적용하세요
- 민감한 정보를 입력할 때 주의하세요