## 핵심 개요

- 단일 서버 “remote-computer-control”가 스크린샷·마우스·키보드 도구를 모두 제공하고 SSE 엔드포인트로 원격 연결을 받는다.[^2][^1]
- Claude Code에서는 원격 SSE 서버 추가 명령으로 연결하거나, Messages API의 MCP 커넥터에서 URL 타입으로 등록할 수 있다.[^5][^1]


## 왜 단일 서버인가

- FastMCP는 MCP 도구/리소스를 파이썬 데코레이터로 간단히 노출할 수 있어, 스크린샷과 입력 제어를 한 서버로 통합해도 구성 복잡도가 낮다.[^2]
- Claude Code는 원격 SSE 서버 연결을 정식 지원하므로, 통합 서버 하나를 공개 포트로 운영하면 개발/운영이 단순화된다.[^1]


## Docker 자산

아래 파일들을 같은 디렉터리에 배치한다고 가정한다.[^4][^3]

- Dockerfile
- start.sh
- requirements.txt
- mcp_fastmcp_server.py (첨부 파일 사용; DISPLAY=:99, SSE, CORS 설정 포함)


### requirements.txt

아래는 서버 및 GUI 제어·캡처에 필요한 패키지로, pyautogui(X11 제어), python-xlib(Xlib), mss(고속 캡처), Pillow(이미지 인코딩), uvicorn/starlette(SSE 서빙), MCP SDK를 포함한다.[^4][^2]

```
mcp
fastmcp
starlette
uvicorn[standard]
pyautogui
python-xlib
mss
Pillow
```


### Dockerfile

Xvfb로 가상 디스플레이 :99를 띄우고, 컨테이너 시작 시 서버를 자동 기동한다.[^3][^4]

```dockerfile
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# 기본 도구 및 Xvfb 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11-apps ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# 워킹 디렉터리
WORKDIR /app

# 의존성
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 서버 코드
COPY mcp_fastmcp_server.py /app/mcp_fastmcp_server.py
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 네트워크
EXPOSE 8000

# Healthcheck: SSE 엔드포인트 접근 시도
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD \
    wget -qO- http://127.0.0.1:8000/sse || exit 1

# 시작 스크립트 실행
ENTRYPOINT ["/app/start.sh"]
```

이 구성은 pyautogui가 X 서버와 통신 가능한 DISPLAY를 갖도록 Xvfb를 백그라운드로 기동한 뒤 파이썬 서버를 실행하는 일반적인 헤드리스 패턴에 맞춰져 있다.[^3][^4]

### start.sh

컨테이너 기동 시 Xvfb → MCP 서버(SSE) 순으로 구동한다.[^3]

```bash
#!/usr/bin/env bash
set -euo pipefail

# 가상 디스플레이 시작
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!

# 애플리케이션이 내부적으로도 DISPLAY=:99를 설정하지만 환경도 맞춰준다
export DISPLAY=:99

# 로그 출력 대기
sleep 0.5

# 환경변수로 호스트/포트 제어 가능
export MCP_HOST="${MCP_HOST:-0.0.0.0}"
export MCP_PORT="${MCP_PORT:-8000}"

# 서버 실행
python /app/mcp_fastmcp_server.py

# 정리
kill ${XVFB_PID} 2>/dev/null || true
```

pyautogui는 리눅스에서 Xlib를 통해 X 서버와 상호작용하므로, 실제 화면 없이도 Xvfb 가상 프레임버퍼 위에서 마우스/키보드 이벤트와 스크린샷 처리를 진행할 수 있다.[^4][^3]

## 빌드와 실행

- 이미지 빌드:
    - docker build -t remote-mcp:latest . 명령으로 이미지를 빌드한다.[^3]
- 컨테이너 실행:
    - docker run -d --name remote-mcp -p 8000:8000 remote-mcp:latest 로 실행하면 SSE 엔드포인트를 8000 포트로 노출한다.[^1]
- 헬스 확인:
    - 로그에서 “SSE endpoint … /sse”와 같이 기동 메시지를 확인하거나 HEALTHCHECK 상태를 조회하면 된다.[^1]


## Claude 연결 방법

둘 중 한 방법을 사용하면 된다.[^5][^1]

- Claude Code CLI
    - 원격 SSE 서버 추가:
        - claude mcp add --transport sse remote-computer-control http://<HOST_OR_IP>:8000/sse 형태로 등록한다.[^1]
    - 이 방식은 원격 SSE 전송을 통해 도구를 실시간으로 호출할 수 있도록 연결을 구성한다.[^1]
- Messages API의 MCP 커넥터
    - mcp_servers 배열에 URL 타입 서버를 추가한다:
        - { "type": "url", "url": "https://<PUBLIC_HOST>/sse", "name": "remote-computer-control" } 형태로 지정한다.[^5]
    - 커넥터는 현재 URL이 HTTPS여야 하므로 퍼블릭 운영 시 리버스 프록시로 TLS를 종단하는 구성을 권장한다.[^5]


## CLAUDE.md (단일 서버)

아래는 단일 통합 MCP 서버 기준으로 재작성한 문서이다.[^2][^1]

목적

- “remote-computer-control” 단일 서버가 화면 캡처와 입력 제어 도구를 모두 제공하여 Claude가 필요 시 원격으로 시각 정보를 얻고 입력을 수행한다.[^2][^1]

아키텍처

- 서버는 FastMCP 기반으로 도구와 리소스를 노출하고, SSE 전송으로 /sse 엔드포인트에서 원격 접속을 지원한다.[^2][^1]
- 클라이언트 측에서는 Claude Code 또는 Messages API MCP 커넥터가 SSE 서버에 연결해 도구를 호출한다.[^5][^1]

도구 목록

- screenshot(format, quality, monitor): Xvfb 디스플레이의 전체 화면을 캡처해 base64 PNG로 반환한다.[^4][^3]
- move_mouse(x, y, duration), click_mouse(...), type_text(text, interval), press_key(key, modifiers): Xlib를 통해 마우스/키보드 이벤트를 전송한다.[^4]
- get_screen_size(monitor), get_mouse_position(): 현재 디스플레이/포인터 상태를 조회한다.[^4]

배포/실행

- Docker로 배포하며 컨테이너 시작 시 Xvfb(:99)와 MCP SSE 서버가 함께 기동된다.[^3]
- 포트 8000을 노출하고, 필요 시 MCP_HOST/MCP_PORT 환경변수로 바인딩을 조정한다.[^1]

Claude 등록

- Claude Code: claude mcp add --transport sse remote-computer-control http://<HOST>:8000/sse 로 프로젝트 또는 사용자 스코프에 등록한다.[^1]
- Messages API: mcp_servers에 {type:"url", url:"https://<PUBLIC>/sse", name:"remote-computer-control"} 형태로 지정한다.[^5]

보안

- 퍼블릭 운영 시 HTTPS 종단과 인증 헤더 적용을 권장하며, CLI/구성에서 헤더 지정 또는 커넥터의 authorization_token 필드를 사용할 수 있다.[^5][^1]
- 최소 권한 원칙으로 방화벽/리버스 프록시에서 접근 제어를 시행한다.[^5]

운영 팁

- 헤드리스 환경에서는 Xvfb가 필수이며, pyautogui는 리눅스에서 python-xlib 및 Pillow가 필요하다.[^3][^4]
- 다중 서버가 필요하다면 FastMCP 조합/프록시 패턴으로 확장 가능하나, 본 구성은 단일 서버 통합을 전제로 한다.[^2]


## 트러블슈팅

- 화면이 캡처되지 않음: Xvfb(:99)가 기동되었는지, DISPLAY=:99가 설정되었는지 확인하고 해상도/픽셀포맷을 1920x1080x24 등으로 지정한다.[^3]
- 입력 이벤트 무반응: pyautogui가 Xlib에 붙지 못하는 경우 python-xlib 설치, DISPLAY 환경변수, Xauthority 이슈를 점검한다.[^4]
- Claude 연결 실패: Claude Code에서는 --transport sse로 추가했는지, Messages API 커넥터에서는 url이 HTTPS인지 확인한다.[^1][^5]


## 다음 단계 제안

- 프로덕션 노출 시 Nginx 리버스 프록시로 TLS와 인증 헤더를 부여하고, Claude Code 측에서는 --header 또는 커넥터 authorization_token을 사용한다.[^5][^1]
- 도구 입력·출력 스키마에 설명을 더해 Claude가 파라미터를 더 정확히 자동 구성하도록 돕는다.[^2]

원하는 경우, 도커 컴포즈 예시와 Helm 차트 스켈레톤도 제공 가능하다.[^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^6][^7][^8][^9]</span>

<div style="text-align: center">⁂</div>

[^1]: https://docs.anthropic.com/en/docs/claude-code/mcp

[^2]: https://apidog.com/kr/blog/fastmcp-kr/

[^3]: https://stackoverflow.com/questions/39137476/is-it-possible-to-run-pyautogui-in-headless-mode/73036316

[^4]: https://github.com/asweigart/pyautogui

[^5]: https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector

[^6]: mcp_fastmcp_server.py

[^7]: CLAUDE.md

[^8]: https://docs.anthropic.com/ko/docs/claude-code/mcp

[^9]: https://github.com/orgs/modelcontextprotocol/discussions/16

[^10]: https://www.f22labs.com/blogs/mcp-practical-guide-with-sse-transport/

[^11]: https://stackoverflow.com/questions/39730197/how-to-install-the-pyautogui-module-on-redhat

[^12]: https://github.com/ConechoAI/nchan-mcp-transport

[^13]: https://wikidocs.net/286550

[^14]: https://www.reddit.com/r/learnpython/comments/4m6wie/having_issues_installing_pyautogui_on_linux/

[^15]: https://docs.crewai.com/ko/mcp/overview

[^16]: https://github.com/jlowin/fastmcp

[^17]: https://docs.continue.dev/customize/deep-dives/mcp

[^18]: https://wikidocs.net/289908

[^19]: https://wikidocs.net/13959

[^20]: https://support.anthropic.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers

[^21]: https://rudaks.tistory.com/entry/MCP-Server-개발-Python

[^22]: https://www.reddit.com/r/ClaudeAI/comments/1jj80mk/how_can_i_configure_an_mcp_sse_endpoint_in_claude/

