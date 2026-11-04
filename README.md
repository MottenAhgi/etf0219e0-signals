# 0219E0 전용 무료 클라우드 분석기

상태: 코드 및 로컬 가상 데이터 테스트 완료. GitHub 배포, 공식 API 인증, 실제 텔레그램 수신, iPhone Safari 실기기 테스트는 아직 완료되지 않았습니다.

주문 실행 코드와 계좌번호 입력란이 없습니다. 학습형 AI가 아닌 설명 가능한 지표 규칙 모델입니다. API 비용이 발생하는 LLM은 사용하지 않습니다. 신호의 수익성은 입증되지 않았습니다.

## 1. GitHub 무료 계정

이미 GitHub 계정을 연결했다면 재가입하지 않습니다. 계정이 없다면 https://github.com/signup 에서 이메일, 비밀번호, 사용자명을 입력하고 이메일·사람 인증을 직접 완료합니다. Free 플랜을 선택합니다. 비밀번호와 인증번호를 채팅에 보내지 않습니다.

새 저장소 이름: `etf0219e0-signals`. 무료 Actions 표준 실행기를 제한 없이 쓰려면 public 저장소를 사용할 수 있습니다. public에는 소스와 파생 분석 결과가 공개될 수 있습니다. 보유수량·매입가·계좌정보는 입력하지 않습니다. private 저장소는 무료 월 사용량 한도가 있으므로 Billing의 예산 및 유료 사용 차단 설정을 확인합니다. 신용카드 등록은 필수 구성에 포함하지 않습니다.

이 폴더 내용을 저장소 최상위에 올립니다. `.github/workflows/`도 반드시 포함해야 합니다. 웹 업로드가 숨김 폴더를 누락하면 GitHub의 Create new file에서 `.github/workflows/analyze.yml`, `.github/workflows/ci.yml`을 각각 생성합니다.

## 2. 공식 시세 API

https://apiportal.koreainvestment.com/ 에서 한국투자증권 계정 및 Open API 서비스 신청 후 실전 앱키를 발급합니다. 계정·서비스 자격 조건과 시세 이용 약관을 확인합니다. 증권계좌가 필요할 수 있으며, 이 프로그램에 계좌번호·주문 권한을 위한 값을 제공할 필요는 없습니다. API 앱키 자체가 주문에도 쓰일 수 있으므로 비밀키로 관리합니다.

저장소 Settings → Secrets and variables → Actions → New repository secret:

| 이름 | 값 |
|---|---|
| KIS_APP_KEY | 실전 App Key |
| KIS_APP_SECRET | 실전 App Secret |
| TELEGRAM_BOT_TOKEN | BotFather 발급 토큰 |
| TELEGRAM_CHAT_ID | 본인의 개인 채팅 ID |

키를 코드, 이슈, 커밋, 채팅 본문에 넣지 않습니다. 키 입력은 사용자가 GitHub Secrets 화면에서 직접 합니다. KIS 주문 API는 호출하지 않고 일봉 조회 API만 허용합니다. 원주가를 사용하며 분배금은 별도 포함하지 않습니다. 최대 약 3년 범위 내 상장 이후 존재하는 데이터만 가져옵니다. 65거래일 미만이면 중단합니다.

## 3. 텔레그램

텔레그램의 공식 @BotFather에서 `/newbot`으로 봇을 만들고 토큰을 Secrets에 저장합니다. 만든 봇과 본인 개인 대화에서 `/start`를 보냅니다. 개인 chat_id는 공식 Bot API `getUpdates` 응답의 message.chat.id로 확인합니다. 토큰이 URL에 포함되므로 URL·응답을 공유하지 않습니다. 그룹·타인 수신자는 사용하지 않습니다.

미설정이면 분석은 성공하고 알림 상태는 `not_configured`가 됩니다. 전송 성공 후에만 중복 방지 상태를 기록합니다. 일자·장중/마감 구분·신호가 같으면 반복 전송하지 않으며, 신호가 바뀌면 새 알림을 보냅니다. Actions cache가 삭제되면 중복 알림이 다시 올 수 있습니다.

## 4. 실행과 시간표 (한국시간)

Actions → 0219E0 analysis → Run workflow:

1. demo=true: 비밀키 없이 가상 데이터 실행. 텔레그램 전송 없음.
2. demo=false, mode=intraday 또는 close: 공식 API 호출 및 설정된 개인 텔레그램 알림.
3. 성공 실행의 Artifacts에서 report.json과 index.html을 받습니다.

예약은 월~금 09:07부터 15:22까지 15분 간격, 마감 분석은 16:07입니다. GitHub cron은 UTC입니다. 공휴일·시세 지연으로 당일 일봉이 없으면 성공한 것처럼 이전 신호를 보내지 않고 실행을 실패 처리합니다. 수능 등 특별 개장일의 첫 시각에도 중단할 수 있습니다. 장애는 Actions 실행 기록에서 확인합니다. 별도 장애 알림 채널은 구현하지 않았습니다.

GitHub 예약은 지연·누락될 수 있습니다. 초 단위 실시간 매매용이 아닙니다. 기본 브랜치에 workflow가 있어야 하며 public 저장소는 60일 무활동으로 예약이 꺼질 수 있습니다. 유효한 API 키가 없으면 실제 분석을 건너뛰며 기존 데모를 유지합니다.

## 5. 분석 규칙

Wilder RSI(14), EMA MACD(12,26,9), 이동평균(5,20,60), 직전 20일 평균 대비 거래량을 계산합니다.

다음 각 항목 1점, 총 5점:
- 종가 > 20일선
- 5일선 > 20일선
- RSI 40~65
- MACD > MACD signal
- 거래량 / 직전 20일 평균 거래량 ≥ 1.2

4~5점: 매수 검토. 2~3점: 관망. 0~1점: 위험 축소 검토. 60일선은 참고 필터로 표시합니다. 점수는 상승 확률이나 신뢰도 퍼센트가 아닙니다. 장중에는 당일 누적 거래량을 사용해 초기 거래량 점수가 낮아질 수 있습니다. 장중 신호는 일봉 완성 전 잠정 신호입니다.

## 6. 백테스트

60일 준비 구간 뒤부터 전일 종가 신호로 다음 거래일 시가에 가상 체결합니다. 4점 이상이면 현금으로 매수, 1점 이하면 매도, 중립이면 현재 비중을 유지합니다. 소수점 수량을 허용하는 연구 모델이며 실제 주문 가능 수량과 다를 수 있습니다. 매수/매도 각 10bp 비용(수수료+슬리피지 가정), 최종 청산 비용을 반영합니다. 비용은 `--cost-bps`로 변경합니다. 매수 보유 비교에도 동일 비용을 적용합니다.

분배금·분배금 재투자·세금은 제외하므로 커버드콜 ETF의 총수익률 비교가 아닙니다. 원주가 분배락이 지표와 수익률에 영향을 줍니다. 상장 이력이 짧으면 검증 기간도 짧습니다. 표본 외 검증·최적화·워크포워드·월분배금 총수익 백테스트는 미구현입니다. 가상 데이터 성과는 이 ETF의 성과가 아닙니다.

## 7. iPhone 대시보드

반응형 단일 HTML을 생성합니다. 분석 시각, 일봉 날짜, 잠정 여부, 지표, 신호와 백테스트가 표시됩니다. 원시 OHLCV·보유정보·API 키를 HTML에 넣지 않습니다.

Settings → Pages → Source: GitHub Actions로 설정하면 docs/index.html이 최초 데모로 게시됩니다. 실제 분석이 성공하면 새 결과가 Pages에 게시됩니다. 키가 없으면 예약 작업은 실제 분석을 건너뜁니다. 공개 웹페이지이므로 파생 분석 결과의 공개가 허용되는지 KIS 시세 이용 조건을 먼저 확인합니다. 원시 시세와 계좌 정보는 게시하지 않습니다. private 저장소의 Pages 사용 가능 여부는 플랜에 따라 다릅니다.

생성된 Pages URL을 iPhone Safari에서 열고 공유 → 홈 화면에 추가합니다. 키를 Safari에 입력하지 않습니다. 화면은 5분마다 갱신하지만 분석 데이터는 Actions가 성공해야 바뀝니다. 24시간 이상 오래된 결과에는 경고가 표시됩니다. iPhone 실기기 검증은 아직 하지 않았습니다.

## 8. 로컬 테스트

Python 3.11 이상:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python analyzer.py --demo
python analyzer.py --csv mydata.csv --mode close
```

CSV 열: date,open,high,low,close,volume. 가상 데이터 실행만 실제로 검증했습니다. 실데이터를 제공하면 동일 엔진으로 분석할 수 있습니다.

## 공식 문서

- https://github.com/koreainvestment/open-trading-api/tree/main/examples_llm/domestic_stock/inquire_daily_itemchartprice
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://core.telegram.org/bots/api#sendmessage
