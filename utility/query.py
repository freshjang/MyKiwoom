import sqlite3
from utility.static import now
from utility.setting import DB_STG, DB_TICK


class Query:
    def __init__(self, windowQ, queryQ):
        self.windowQ = windowQ
        self.queryQ = queryQ
        self.con1 = sqlite3.connect(DB_STG)
        self.cur1 = self.con1.cursor()
        self.con2 = sqlite3.connect(DB_TICK)
        self.Start()

    def __del__(self):
        self.con1.close()
        self.con2.close()

    def Start(self):
        k = 0
        while True:
            query = self.queryQ.get()
            if query[0] == 1:
                if len(query) == 2:
                    try:
                        self.cur1.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([1, f'시스템 명령 오류 알림 - execute {e}'])
                    else:
                        self.con1.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con1, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([1, f'시스템 명령 오류 알림 - to_sql {e}'])
            elif query[0] == 2:
                try:
                    if len(query) == 2:
                        start = now()
                        for code in list(query[1].keys()):
                            query[1][code].to_sql(code, self.con2, if_exists='append', chunksize=1000)
                        k += 1
                        if k % 4 == 0:
                            save_time = (now() - start).total_seconds()
                            self.windowQ.put([1, f'시스템 명령 실행 알림 - 틱데이터 저장 쓰기소요시간은 [{save_time}]초입니다.'])
                    elif len(query) == 4:
                        query[1].to_sql(query[2], self.con2, if_exists=query[3], chunksize=1000)
                except Exception as e:
                    self.windowQ.put([1, f'시스템 명령 오류 알림 - to_sql {e}'])
