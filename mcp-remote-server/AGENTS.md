### 목적

- 이 저장소는 단일 MCP 서버 “remote-computer-control”을 통해 스크린샷과 입력 제어 도구를 원격 제공하며, SSE 전송으로 노출된 /sse 엔드포인트에 접속해 도구 호출을 수행한다.[^4][^1]
- 본 문서는 모든 에이전트가 동일한 접속 구성과 도구 사용 원칙을 따르도록 표준화된 지침을 제공한다.[^2][^5]


### 연결 구성

- 이 프로젝트의 에이전트는 Anthropic API의 **MCP 커넥터**를 사용해 원격 MCP 서버에 직접 연결하며, 요청 본문에 mcp_servers 항목을 추가해 URL 기반 서버를 선언한다.[^6][^1]
- 커넥터 사용 시 베타 헤더 anthropic-beta: mcp-client-2025-04-04 가 필요하며, 서버가 인증을 요구하면 authorization_token 필드에 Bearer 토큰을 설정한다.[^1][^6]

예시: Messages API 요청 조각

```json
{
  "model": "claude-sonnet-4",
  "max_tokens": 1000,
  "messages": [
    {"role": "user", "content": "원격 화면 상태를 확인하고 필요하면 로그인해줘"}
  ],
  "mcp_servers": [
    {
      "type": "url",
      "url": "https://<PUBLIC_HOST>/sse",
      "name": "remote-computer-control",
      "authorization_token": "<OPTIONAL_BEARER_TOKEN>"
    }
  ]
}
```

- 위 URL은 본 저장소의 단일 서버가 노출하는 SSE 경로(/sse)이며, 퍼블릭 운영 시 HTTPS 종단 및 인증 토큰 사용을 권장한다.[^4][^1]


### 노출 도구

- screenshot(format="base64", quality=85, monitor=0): 현재 디스플레이에서 전체 화면을 캡처해 base64 PNG로 반환한다.[^4][^1]
- move_mouse(x, y, duration), click_mouse(button, x, y, clicks, interval): 마우스 이동과 클릭을 처리하며 좌표 지정 또는 현재 위치에서 동작한다.[^1][^4]
- type_text(text, interval), press_key(key, modifiers): 타이핑과 단일/조합 키 입력을 전송해 폼 입력이나 단축키 수행에 사용한다.[^4][^1]
- get_screen_size(monitor), get_mouse_position(): 현재 화면 크기와 포인터 좌표를 조회해 후속 입력의 기준으로 삼는다.[^1][^4]


### 작동 원리

- MCP 커넥터가 설정된 요청을 받으면 Claude는 원격 MCP 서버에 연결해 사용 가능한 도구를 자동으로 조회한 뒤, 목표 달성을 위해 어떤 도구를 어떤 인자로 호출할지 스스로 판단한다.[^3][^1]
- 에이전트는 필요 시 여러 번의 도구 호출을 연쇄적으로 수행하고 오류를 관리하면서 충분한 결과가 확보될 때까지 반복한 후 응답을 생성한다.[^3]


### 사용 원칙

- 시각 정보가 필요한 단계에서는 먼저 screenshot을 호출해 최신 상태를 확보하고, 좌표가 필요한 입력은 get_screen_size/get_mouse_position 결과를 기준으로 결정한다.[^3][^4]
- 민감 동작(로그인/결제 등)은 화면 검증 스텝(캡처→확인→입력)을 분리해 수행하고, 실패시 재시도 전 최신 캡처로 상태를 재평가한다.[^5][^3]
- 툴 호출은 목적 지향적으로 최소화하며, 중복 캡처/불필요 입력을 피하고 단계별 로그로 추적 가능성을 유지한다.[^5][^3]


### 보안

- 원격 서버는 공개 HTTP(S)로 노출되어야 하며, 커넥터는 URL 기반 서버만 직접 연결한다(로컬 STDIO 미지원).[^6][^1]
- 인증이 필요한 환경에서는 authorization_token을 사용하고, 네트워크 상에서는 TLS 종단 및 방화벽/리버스 프록시에서 최소 권한 접근을 권장한다.[^6][^1]


### 운영

- 본 서버는 SSE 엔드포인트를 /sse 경로에 마운트하며, 컨테이너가 시작될 때 함께 기동되도록 구성되어 있다.[^4]
- 다중 서버 연결이 필요한 시나리오에서도 mcp_servers에 여러 URL 항목을 추가해 병렬 도구 집합을 구성할 수 있다.[^1][^3]


### 프롬프트 가이드

- 시스템 지침에 “원격 화면 확인 → 필요 입력 수행 → 결과 검증” 루프를 명시해 에이전트가 단계적 계획과 검증을 기본 전략으로 사용하도록 유도한다.[^5][^3]
- CLAUDE.md와 AGENTS.md는 상호 보완적으로 사용되며, CLAUDE.md는 코드베이스·워크플로 지침, AGENTS.md는 에이전트 연결/도구 사용 원칙을 담는 것을 권장한다.[^2][^5]


### 테스트 체크리스트

- mcp_servers에 단일 서버가 노출되고 이름이 remote-computer-control로 인식되는지 확인한다.[^4][^1]
- “사용 가능한 도구가 뭐야?” 같은 프롬프트로 도구 인벤토리를 질의하고 screenshot 호출 결과가 base64 PNG로 반환되는지 점검한다.[^1][^4]
- 인증이 켜진 경우 authorization_token 누락 시 연결 거부/도구 비노출 에러가 재현되는지 확인한다.[^1]


### 문제 해결

- 연결 실패: URL 형식(type=url), /sse 경로, 베타 헤더 설정(anthropic-beta) 유무를 확인한다.[^6][^1]
- 도구 비노출: 서버 기동 여부, CORS/SSE 접근 가능성, 인증 토큰 설정을 점검한다.[^4][^1]
- 실행 실패: 좌표/화면 크기 전제 충돌 가능성이 있으므로 get_screen_size/get_mouse_position으로 재동기화 후 입력을 재시도한다.[^3][^4]


### 변경 관리

- 도구 시그니처 변경 시 본 문서의 “노출 도구” 섹션을 함께 업데이트하고, 에이전트 시스템 지침/테스트 체크리스트를 동기화한다.[^2][^5]
- 원격 서버를 추가/교체하는 경우 mcp_servers 항목을 갱신하고 보안/인증 섹션을 재검토한다.[^6][^1]

이 AGENTS.md는 단일 서버 통합 구성을 전제로 작성되었으며, 에이전트가 **도구 자동 발견→계획→호출→검증**의 표준 루프를 따르도록 최적화되어 있다.[^2][^3]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^7][^8][^9]</span>

<div style="text-align: center">⁂</div>

[^1]: https://docs.anthropic.com/en/docs/agents-and-tools/mcp-connector

[^2]: https://agents.md

[^3]: https://www.anthropic.com/news/agent-capabilities-api

[^4]: mcp_fastmcp_server.py

[^5]: https://www.anthropic.com/engineering/claude-code-best-practices

[^6]: https://docs.anthropic.com/ko/docs/agents-and-tools/mcp-connector

[^7]: CLAUDE.md

[^8]: https://www.anthropic.com/news/model-context-protocol

[^9]: https://docs.neuron-ai.dev/getting-started/mcp-connector

[^10]: https://www.builder.io/blog/agents-md

[^11]: https://composio.dev/blog/the-complete-guide-to-building-mcp-agents

[^12]: https://www.confluent.io/blog/ai-agents-using-anthropic-mcp/

[^13]: https://github.com/lastmile-ai/mcp-agent

[^14]: https://gpt-trainer.com/blog/anthropic+model+context+protocol+mcp

[^15]: https://openai.github.io/openai-agents-python/mcp/

[^16]: https://docs.anthropic.com/ko/docs/agents-and-tools/remote-mcp-servers

[^17]: https://github.com/ruvnet/claude-flow/wiki/CLAUDE-MD-Templates

[^18]: https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent

[^19]: https://newsletter.victordibia.com/p/how-to-use-mcp-anthropic-mcp-tools

[^20]: https://github.com/wshobson/agents

[^21]: https://github.com/mcp-use/mcp-use

[^22]: https://habr.com/en/articles/939420/

