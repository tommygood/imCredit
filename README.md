# imCredit
- 計算暨大資管系畢業學分門檻

## 簡介
- 用於審核不同組別的同學目前修課數是否已達到標準，讓系辦助理不用人工對。
- build with Django

## Config
- 登入的設定
   - read `account` & `password` from env.

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
https://github.com/tommygood/imCredit/blob/main/109_%E7%8E%8B%E5%86%A0%E6%AC%8A_%E7%95%A2%E6%A5%AD%E5%AD%B8%E5%88%86%E6%AA%A2%E6%A0%B8%E8%A1%A8.pdf
