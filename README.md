# Notion to GPT Assistant

이 프로젝트는 Notion 데이터베이스의 내용을 GPT Assistant에 통합하는 도구입니다.

## 설정 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:
- `.env` 파일을 생성하고 다음 정보를 입력하세요:
  - `NOTION_TOKEN`: Notion Integration Token
  - `NOTION_DATABASE_ID`: Notion 데이터베이스 ID
  - `OPENAI_API_KEY`: OpenAI API 키

## Notion 설정

1. Notion에서 새로운 Integration 생성:
   - https://www.notion.so/my-integrations 에서 새로운 integration 생성
   - 생성된 Integration Token을 `.env` 파일에 입력

2. 데이터베이스 공유 설정:
   - Notion 데이터베이스 페이지에서 "Share" 버튼 클릭
   - 생성한 Integration을 추가하여 접근 권한 부여
   - 데이터베이스 ID를 `.env` 파일에 입력 (URL에서 확인 가능)

## 실행 방법

```bash
python main.py
```

## 기능

- Notion 데이터베이스의 내용을 가져옵니다
- 가져온 내용을 GPT Assistant에 통합합니다
- Assistant는 데이터베이스 내용에 대한 질문에 답변할 수 있습니다

## 주의사항

- Notion API는 초당 요청 제한이 있습니다
- 데이터베이스 크기에 따라 처리 시간이 달라질 수 있습니다
- OpenAI API 사용에 따른 비용이 발생할 수 있습니다 