import os
import sys
import psutil
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import now, strf_time, timedelta_sec, thread_decorator

DIVIDE_SAVE = True     # 틱데이터 저장방식 선택 - True: 경우 10초에 한번 저장, False: 장마감 후 거래종목만 저장


class Collector:
    def __init__(self, gubun, windowQ, queryQ, tickQ):
        self.gubun = gubun
        self.windowQ = windowQ
        self.queryQ = queryQ
        self.tickQ = tickQ

        self.dict_df = {}
        self.dict_dm = {}
        self.dict_time = {
            '기록시간': now(),
            '저장시간': now(),
            '부가정보': now()
        }
        self.dict_intg = {
            '스레드': 0,
            '시피유': 0.,
            '메모리': 0.
        }
        self.str_tday = strf_time('%Y%m%d')
        self.Start()

    def Start(self):
        while True:
            data = self.tickQ.get()
            if len(data) != 2:
                self.UpdateTickData(data)
            elif data[0] == '콜렉터종료':
                if not DIVIDE_SAVE:
                    self.SaveTickData(data[1])
                break

            if now() > self.dict_time['부가정보']:
                self.UpdateInfo()
                self.dict_time['부가정보'] = timedelta_sec(2)

        if self.gubun == 4:
            self.windowQ.put([1, '시스템 명령 실행 알림 - 콜렉터 종료'])

    def UpdateTickData(self, data):
        code = data[-3]
        dt = data[-2]
        receivetime = data[-1]

        data.remove(code)
        data.remove(dt)
        data.remove(receivetime)

        if code not in self.dict_df.keys():
            columns = [
                '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도',
                '초당매수수량', '초당매도수량', 'VI해제시간', 'VI아래5호가', '매도총잔량', '매수총잔량',
                '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1',
                '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
                '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1',
                '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5'
            ]
            self.dict_df[code] = pd.DataFrame([data], columns=columns, index=[dt])
        else:
            self.dict_df[code].at[dt] = data

        if self.gubun == 4 and now() > self.dict_time['기록시간']:
            gap = (now() - receivetime).total_seconds()
            self.windowQ.put([1, f'콜렉터 수신 기록 알림 - 수신시간과 기록시간의 차이는 [{gap}]초입니다.'])
            self.dict_time['기록시간'] = timedelta_sec(60)

        if DIVIDE_SAVE and now() > self.dict_time['저장시간']:
            self.queryQ.put([2, self.dict_df])
            self.dict_df = {}
            self.dict_time['저장시간'] = timedelta_sec(10)

    def SaveTickData(self, codes):
        for code in list(self.dict_df.keys()):
            if code in codes:
                columns = ['현재가', '시가', '고가', '거래대금', '누적거래대금', '상승VID5가격', '매수수량', '매도수량',
                           '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2']
                self.dict_df[code][columns] = self.dict_df[code][columns].astype(int)
            else:
                del self.dict_df[code]
        self.queryQ.put([2, self.dict_df])

    @thread_decorator
    def UpdateInfo(self):
        info = [8, self.dict_intg['메모리'], self.dict_intg['스레드'], self.dict_intg['시피유']]
        self.windowQ.put(info)
        self.UpdateSysinfo()

    def UpdateSysinfo(self):
        p = psutil.Process(os.getpid())
        self.dict_intg['메모리'] = round(p.memory_info()[0] / 2 ** 20.86, 2)
        self.dict_intg['스레드'] = p.num_threads()
        self.dict_intg['시피유'] = round(p.cpu_percent(interval=2) / 2, 2)
