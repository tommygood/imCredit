# imCredit
- 計算暨大資管系畢業學分門檻

## 簡介
- 用於審核不同組別的同學目前修課數是否已達到標準，讓系辦助理不用人工對。
- build with Django

## Config
- 寫登入的設定檔到 `config.json` :  `{"account" : "{your_account}", "password", "{your_password}"}`

## Usage
- `python3 manage.py runserver`
- open browser on localhost:8000/credit/IMCreditCount

## 功能
- 各個領域可以列出詳細的資訊（已修過、未修過的課）
- 輸出 pdf 檔：確保所有內容集中在一頁 pdf
- 新增學年資料
  - 可登入 /credit/addData，新增新學年度的 excel 資料。
  - excel 的資料放置位置規則寫在 views.py 的 mkLec
- 浮水印
  - 以系辦身分登入，檔案會有浮水印

## Demo
![image](https://github.com/tommygood/imCredit/assets/96759292/ed4d2d48-0395-4e52-b78c-4def4024f3eb)
