## 목적

Claude Code에서 자동화를 위해 두 가지 MCP 서버를 연동한다:

1. **입력 신호 관리용 MCP (HID MCP)**: 하드웨어 입력 신호(키보드, 마우스 등)를 실제 HID 드라이버를 통해 물리적으로 발생시킴.[^5][^6]
2. **화면 캡처 및 인식용 MCP (Screenshot MCP)**: 주기적/이벤트 기반으로 화면 전체 또는 특정 윈도우/브라우저 영역을 캡처해 Claude가 시각 정보를 처리함.[^2][^1]

## 아키텍처

- Claude Code가 각 MCP(입력·화면) 서버에 필요할 때마다 명령을 직접 발행함
- 입력 MCP는 실제 하드웨어 입력 프로토콜, Screenshot MCP는 화면 캡처 및 이미지 분석 API를 제공
- 각 MCP 서버는 독립적이며 Claude에서 병렬·순차적 호출이 가능


## MCP 서버 등록 방법

```json
{
  "mcpServers": {
    "hid-input-mcp": {
      "command": "python",
      "args": ["/path/to/hid_input_mcp.py"]
    },
    "screenshot-mcp": {
      "command": "node",
      "args": ["/path/to/screenshot_full_page_mcp/index.js"]
    }
  }
}
```


## 주요 실행 플로우

1. Claude Code가 **screenshot-mcp**에 주기적으로(설정 프레임 간격) 캡처 명령을 요청함
2. 캡처 결과(이미지, 분석 정보)를 받아 화면 요소 탐색 및 상태 판단
3. 필요 시 **hid-input-mcp**에 입력 신호(클릭, 타이핑 등) 명령 발송
4. 반복하여 로그인, 상품 구매 등 복합 자동화 절차 진행

## 확장성

- MCP 서버 추가(예: 파일 분석, 네트워크 제어 등) 가능
- Claude Code는 각 기능별 MCP를 필요시마다 호출하여 동작하므로, 병렬 처리/장애 분리/유지보수에 강함.[^3]


## 권장 사항

- 스크린샷 MCP의 프레임 간격, 캡처 대상(브라우저/전체 화면 등)은 Claude Code에서 제어
- 입력 MCP는 OS/HID 드라이버 호환성을 우선 고려
- 별도 로깅/검증 기능 추가 가능

***

**요약:** 입력 신호와 화면 캡처를 별도 MCP로 관리하고 Claude Code가 필요할 때 각 서버를 주도적으로 동작시키는 방식이 기능별 안정성과 확장성을 확보한다.[^2][^3][^1]
<span style="display:none">[^10][^11][^12][^13][^7][^8][^9]</span>

<div style="text-align: center">⁂</div>

[^1]: https://github.com/upnorthmedia/ScreenshotMCP/

[^2]: https://playbooks.com/mcp/syedazharmbnr1-screen-capture

[^3]: https://apidog.com/kr/blog/how-to-quickly-build-a-mcp-server-for-claude-code-kr/

[^4]: https://www.reddit.com/r/ClaudeAI/comments/1h55zxd/can_someone_explain_mcp_to_me_how_are_you_using/

[^5]: https://acroname.com/blog/how-usb-hid-makes-plug-and-play-devices-work

[^6]: https://developer.chrome.com/docs/capabilities/hid

[^7]: https://lobehub.com/mcp/upnorthmedia-screenshot-mcp

[^8]: https://dev.to/composiodev/i-built-my-complete-side-project-in-a-day-using-claude-code-and-mcp-now-you-know-why-they-dont-22gk

[^9]: https://www.anthropic.com/engineering/claude-code-best-practices

[^10]: https://www.youtube.com/watch?v=nu3VDVzAVaE

[^11]: https://lobehub.com/mcp/peterparker57-screenshot-mcp

[^12]: https://github.com/grahama1970/claude-code-mcp-enhanced

[^13]: https://github.com/greggh/claude-code.nvim/pull/30

