import requests
from bs4 import BeautifulSoup

def get_stock_data(symbol):

    url = f"https://finance.yahoo.com/quote/{symbol}"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    price = soup.find("span", class_="Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)").text
    change = soup.find("span", class_="Trsdu(0.3s) Fw(500) Pstart(10px) Fz(24px) C($positiveColor)").text
    change_percentage = soup.find("span", class_="Trsdu(0.3s) Fw(500) Pstart(10px) Fz(24px) C($positiveColor)").find_next("span").text

    print("股票代码:", symbol)
    print("价格:", price)
    print("涨跌幅:", change)
    print("涨跌百分比:", change_percentage)
    
get_stock_data("AAPL")
