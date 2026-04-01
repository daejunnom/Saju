# AI 사주 분석기 (AI Saju Analyzer)

구글의 **Gemini 1.5 Flash AI**를 활용하여 사용자의 생년월일시를 바탕으로 정밀한 사주 명식을 산출하고 운세를 분석해주는 데스크톱 애플리케이션입니다.

## 주요 기능
- **정밀 명식 산출**: 생년월일시를 바탕으로 사주 팔자 및 대운, 세운 자동 계산.
- **AI 운세 분석**: Gemini AI가 사주 원국을 분석하여 성격, 직업운, 재물운 등을 상세히 설명.
- **글로벌 타임존 지원**: `geopy`와 `timezonefinder`를 통해 전 세계 어디서든 출생지 기반 정확한 시간 보정.
- **사용자 친화적 GUI**: 깔끔한 인터페이스로 누구나 쉽게 사용 가능.

## 시작하기 (사용 방법)
1. **다운로드**: 우측 [Releases](https://github.com/daejunnom/Saju/releases) 탭에서 최신 버전의 `saju_gui.exe`를 다운로드합니다.
2. **API 키 준비**: [Google AI Studio](https://aistudio.google.com/)에서 무료 Gemini API Key를 발급받으세요.
3. **실행**: 다운로드한 `.exe` 파일을 실행하고 API 키와 출생 정보를 입력합니다.
4. **분석**: '사주 분석 시작' 버튼을 누르면 AI가 분석 결과를 출력합니다.

## 기술 스택
- **Language**: Python 3.10+
- **AI 모델**: Google Gemini 1.5 Flash
- **GUI**: Tkinter

## 주의사항
- 본 프로그램은 인터넷 연결이 필요합니다.
- 입력하신 API Key는 개인 컴퓨터에만 임시로 사용되며 외부로 전송되지 않습니다.


# AI Saju Analyzer

An advanced desktop application that calculates traditional Korean Saju (Four Pillars of Destiny) and provides personalized fortune-telling using **Google Gemini 1.5 Flash AI**.

## Key Features
- **Precise Saju Calculation**: Automatically computes Saju pillars, Dae-un (Major Cycles), and Se-un (Annual Cycles).
- **AI Fortune Interpretation**: Detailed analysis of personality, career, and wealth luck powered by Gemini AI.
- **Global Timezone Support**: Accurate birth time correction based on location coordinates using `geopy` and `timezonefinder`.
- **User-Friendly GUI**: Simple and intuitive interface for seamless user experience.

## Getting Started
1. **Download**: Navigate to the [Releases](https://github.com/daejunnom/Saju/releases) section and download the latest `saju_gui.exe`.
2. **API Key**: Obtain a free Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
3. **Run**: Launch the `.exe` file, enter your API Key and birth information.
4. **Analyze**: Click 'Start Analysis' and wait for the AI to generate your results.

## Tech Stack
- **Language**: Python 3.10+
- **AI Model**: Google Gemini 1.5 Flash
- **GUI**: Tkinter

## Important Notes
- An active internet connection is required.
- Your API Key is processed locally and is never stored or transmitted externally by this application.
