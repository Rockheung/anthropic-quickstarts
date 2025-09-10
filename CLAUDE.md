# Anthropic Quickstarts Development Guide

## Computer-Use Demo

### Setup & Development

- **Setup environment**: `./setup.sh`
- **Build Docker**: `docker build . -t computer-use-demo:local`
- **Run container**: `docker run -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -v $(pwd)/computer_use_demo:/home/computeruse/computer_use_demo/ -v $HOME/.anthropic:/home/computeruse/.anthropic -p 5900:5900 -p 8501:8501 -p 6080:6080 -p 8080:8080 -it computer-use-demo:local`

### Testing & Code Quality

- **Lint**: `ruff check .`
- **Format**: `ruff format .`
- **Typecheck**: `pyright`
- **Run tests**: `pytest`
- **Run single test**: `pytest tests/path_to_test.py::test_name -v`

### Code Style

- **Python**: snake_case for functions/variables, PascalCase for classes
- **Imports**: Use isort with combine-as-imports
- **Error handling**: Use custom ToolError for tool errors
- **Types**: Add type annotations for all parameters and returns
- **Classes**: Use dataclasses and abstract base classes

## Customer Support Agent

### Setup & Development

- **Install dependencies**: `npm install`
- **Run dev server**: `npm run dev` (full UI)
- **UI variants**: `npm run dev:left` (left sidebar), `npm run dev:right` (right sidebar), `npm run dev:chat` (chat only)
- **Lint**: `npm run lint`
- **Build**: `npm run build` (full UI), see package.json for variants

### Code Style

- **TypeScript**: Strict mode with proper interfaces
- **Components**: Function components with React hooks
- **Formatting**: Follow ESLint Next.js configuration
- **UI components**: Use shadcn/ui components library

## Financial Data Analyst

### Setup & Development

- **Install dependencies**: `npm install`
- **Run dev server**: `npm run dev`
- **Lint**: `npm run lint`
- **Build**: `npm run build`

### Code Style

- **TypeScript**: Strict mode with proper type definitions
- **Components**: Function components with type annotations
- **Visualization**: Use Recharts library for data visualization
- **State management**: React hooks for state

## MCP (Model Context Protocol) Servers

### Overview

MCP는 Claude Code와 외부 도구/데이터를 연결하는 표준 프로토콜 (JSON-RPC 2.0 기반)
- **현재 버전**: 2025년 6월 18일 업데이트
- **공식 사양**: https://modelcontextprotocol.io/specification/2025-06-18

### MCP Server Setup

#### 1. Configuration Files

**프로젝트 레벨** (`.claude/mcp_settings.json`):
```json
{
  "mcpServers": {
    "hid-input-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-unified", "python3", "/app/hid_input_mcp.py"],
      "env": {"DISPLAY": ":99", "PYTHONUNBUFFERED": "1"}
    },
    "screenshot-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-unified", "python3", "/app/screenshot_mcp.py"],
      "env": {"DISPLAY": ":99", "PYTHONUNBUFFERED": "1"}
    }
  }
}
```

**사용자 레벨** (`~/.claude/mcp_settings.json`): 전역 MCP 서버 설정

#### 2. Transport Mechanisms

- **stdio** (권장): 표준 입출력 통신, 가장 안정적
- **HTTP + SSE**: 원격 서버 지원, Server-Sent Events
- **Streamable HTTP** (2025 신규): 향상된 성능, 스트리밍 지원

#### 3. Docker Integration

```bash
# 컨테이너 실행
docker-compose up -d

# MCP 설정 적용
./setup_mcp.sh

# Claude Code 재시작 후 확인
# Claude Code에서: /mcp
```

### ctrl-machine-mcp Setup

#### Quick Start
```bash
cd ctrl-machine-mcp

# 1. 환경 설정
cp .env.example .env
# .env 파일에서 VNC_PASSWORD 설정

# 2. Docker 컨테이너 실행
docker-compose up -d

# 3. MCP 설정
./setup_mcp.sh

# 4. VNC 접속 (디버깅용)
open vnc://localhost:5900  # macOS
```

#### Available MCP Servers

**HID Input MCP** - 하드웨어 입력 제어:
- `move_mouse`: 마우스 이동
- `click_mouse`: 클릭
- `type_text`: 텍스트 입력
- `press_key`: 키 조합

**Screenshot MCP** - 화면 캡처:
- `capture_screenshot`: 단일 캡처
- `start_periodic_capture`: 주기적 캡처
- `stop_periodic_capture`: 캡처 중지

### Protocol Structure

#### Request Format
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "screenshot",
    "arguments": {"format": "base64"}
  },
  "id": "request-123"
}
```

#### Core Methods
- `initialize`: 서버 초기화
- `tools/list`: 도구 목록
- `tools/call`: 도구 실행
- `resources/list`: 리소스 목록
- `resources/read`: 리소스 읽기

### Security (2025 Updates)

- **OAuth 2.1**: Resource Server 인증
- **Resource Indicators**: 토큰 스코핑 필수
- **TLS Required**: HTTP 통신 시 필수
- **Input Validation**: 모든 입력 검증

### Troubleshooting

#### MCP 서버가 보이지 않을 때
1. Claude Code 재시작
2. 설정 파일 확인: `~/.claude/mcp_settings.json`
3. Docker 실행 확인: `docker ps`

#### 연결 오류
```bash
# 컨테이너 재시작
docker-compose restart

# 로그 확인
docker logs mcp-unified
```

#### stdio 통신 오류
- MCP 서버는 독립 실행 불가 (Claude Code가 직접 호출)
- supervisor로 실행 시 실패 (stdin/stdout 필요)

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
