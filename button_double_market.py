from binance.client import Client
import configparser
import time
import json

import tkinter as tk


with open('ooo.json', 'r') as read_file:
    ooo = json.load(read_file)


def get_uin():
    with open("Result_RUB_USDT.txt", "r") as file:
        t = float(file.readline().replace(' ', ''))
        return t


def get_conf():
    with open("config.json", "r") as file:
        data = json.load(file)
    return data["ref"], data["delta"], data["take"], data["glow_time"], data["currency_pairs"]


def form_req(req):
    real_rate = []
    for r in req:
        real_rate.append([r["price"], r["qty"]])
    return real_rate


def get_cur_order(currency_pairs):
    order_cur = []
    for i in range(1, len(currency_pairs)):
        order_cur.append(list())
        order_cur[-1].append(currency_pairs[i - 1])
        order_cur[-1].append(currency_pairs[i])
    return order_cur


class App(tk.Tk):
    uin = 0.0
    better_bids = None
    amount_from_sale = None
    currency_pairs = None
    currency_pairs_list = None
    flag = False
    ref = None
    delta = None
    take = None
    glow_time = None
    quantity = None
    cur_order = None
    currency_pairs_order = None

    def __init__(self, clint):
        super().__init__()
        self.title("Buttons")
        self.geometry("300x384")
        self.frame1 = tk.Frame(self,
                               bg="#555",
                               height=80,
                               width=295)
        self.frame2 = tk.Frame(self,
                               bg="#000",
                               height=295,
                               width=295)

        self.frame1.bind("<Button-1>", self.print_event)
        self.frame1.bind("<ButtonRelease-1>", self.print_event)
        self.frame1.pack(padx=2, pady=2)
        self.frame2.pack(padx=2, pady=2)
        self.clint = clint

    def print_event(self, event):
        eve = int(event.type)
        if eve == 4:
            self.ref, self.delta, self.take, self.glow_time, self.currency_pairs = get_conf()
            self.uin = get_uin()
            self.cur_order = get_cur_order(self.currency_pairs.split('/'))
            self.search_for_currency_pairs()
            self.get_amount_from_sale_from_uin()
            if (self.amount_from_sale - self.ref) > self.delta:
                self.flag = True
                self.make_market()
                self.frame2['background'] = '#fff'
        elif eve == 5:
            if self.flag:
                self.flag = False
                balance_first_cur = float(self.clint.get_asset_balance(asset=self.currency_pairs.split('/')[0])["free"])
                balance_last_cur = float(self.clint.get_asset_balance(asset=self.currency_pairs.split('/')[-1])["free"])
                print(self.currency_pairs.split('/')[0], balance_first_cur, self.uin)
                print(self.currency_pairs.split('/')[-1], balance_last_cur, self.delta)
                while balance_first_cur < self.uin or balance_last_cur > self.delta:
                    time.sleep(self.glow_time)
                    balance_first_cur = float(self.clint.get_asset_balance(asset=self.currency_pairs.split('/')[0])["free"])
                    balance_last_cur = float(self.clint.get_asset_balance(asset=self.currency_pairs.split('/')[-1])["free"])
                    print(self.currency_pairs.split('/')[0], balance_first_cur, self.uin)
                    print(self.currency_pairs.split('/')[-1], balance_last_cur, self.delta)
                self.frame2['background'] = '#000'
            else:
                print(':(')

    def search_for_currency_pairs(self):
        currency_pairs_order = list()
        for cur1, cur2 in self.cur_order:
            for symbol in ooo["symbols"]:
                copy_symbol = symbol
                if cur1 in symbol:
                    copy_symbol = copy_symbol.replace(cur1, '')
                else:
                    continue
                if cur2 in symbol:
                    copy_symbol = copy_symbol.replace(cur2, '')
                else:
                    continue
                if copy_symbol == '':
                    if symbol.find(cur1) == 0:
                        currency_pairs_order.append({symbol: 'sell'})
                    else:
                        currency_pairs_order.append({symbol: 'buy'})
        if len(currency_pairs_order) != len(self.cur_order):
            self.currency_pairs_order = None
        else:
            self.currency_pairs_order = currency_pairs_order

    def get_amount_from_sale_from_uin(self):
        last_uin = self.uin
        better_bids = []
        for cur_id in range(len(self.currency_pairs_order)):
            action = list(self.currency_pairs_order[cur_id].values())[0]
            order_book = self.clint.get_order_book(symbol=list(self.currency_pairs_order[cur_id].keys())[0], limit=100)
            if action == 'sell':
                better_bids.append(list())
                for bid in order_book['bids']:
                    last_uin -= float(bid[1])
                    better_bids[-1].append(bid)
                    if last_uin <= 0:
                        break
                better_bids[-1][-1][-1] = str(round(float(better_bids[-1][-1][-1]) + last_uin, 8))
                last_uin = 0
                for bid in better_bids[-1]:
                    last_uin += round(float(bid[0]) * float(bid[1]), 8)
            elif action == 'buy':
                better_bids.append(list())
                for ask in order_book['asks']:
                    last_uin -= float(ask[0]) * float(ask[1])
                    better_bids[-1].append(ask)
                    if last_uin <= 0:
                        break
                better_bids[-1][-1][-1] = str(
                    round(float(better_bids[-1][-1][-1]) + last_uin / float(better_bids[-1][-1][0]), 8))
                last_uin = 0
                for bid in better_bids[-1]:
                    last_uin += float(bid[1])
        self.amount_from_sale = last_uin

    def get_amount_from_sale(self):
        here_uin = self.uin
        amount_from_sale = 0
        for bid in self.better_bids:
            if here_uin - float(bid[1]) > 0:
                if float(bid[1]) > 1:
                    here_uin -= float(bid[1])
                    amount_from_sale += float(bid[1]) * float(bid[0])
            else:
                self.better_bids[-1][1] = str(here_uin)
                amount_from_sale += here_uin * float(bid[0])
        self.amount_from_sale = amount_from_sale

    def make_market(self):
        end_ask = round((self.ref + self.delta) / (self.amount_from_sale / self.uin), 8)
        start_ask_save = end_ask
        for ask in self.currency_pairs_order:
            if list(ask.values())[0] == 'sell':
                ans = self.clint.order_market_sell(symbol=list(ask.keys())[0], quantity=end_ask)
                end_ask = float(ans['cummulativeQuoteQty'])
            else:
                ans = self.clint.order_market_buy(symbol=list(ask.keys())[0], quoteOrderQty=end_ask)
                end_ask = float(ans['executedQty'])
        print('from {} {} to {} {}'.format(start_ask_save, list(self.currency_pairs_order[0].keys())[0], end_ask, list(self.currency_pairs_order[-1].keys())[0]))
        print(self.currency_pairs_order)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read_file(open('secret.cfg'))
    victor_test_api_key = config.get('BINANCE', 'VICTOR_TEST_API_KEY')
    victor_test_secret_key = config.get('BINANCE', 'VICTOR_TEST_SECRET_KEY')
    client = Client(victor_test_api_key, victor_test_secret_key)
    app = App(client)
    app.mainloop()
