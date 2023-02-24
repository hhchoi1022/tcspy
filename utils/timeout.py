#%%
from functools import wraps
import errno
import os
import signal
import functools
from threading import Thread
#%%
'''
# For Unix system 
class TimeoutError(Exception):
    pass

def Timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        d  signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL,seconds) #used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decoratoref wrapper(*args, **kwargs):
          '''


# For window system
def Timeout(timeout, error : str):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            res = [Exception('function [%s] timeout [%s seconds] exceeded!' % (func.__name__, timeout))]
            # 모든 timeout 데코레이터 사용한 메서드에 res 초기값을 error로 초기화
            def newFunc():
                try:
                    res[0] = func(*args, **kwargs)
                    #res[0] : api 데이터, 메서드를 실행시켜서 값을 저장
                except Exception as e:
                    print("오류발생")
                    res[0] = e
                    #print("res[0] except", res[0]) #함수 자체가 실행이 안 되는 오류 처리
            t = Thread(target=newFunc)
            t.daemon = True
            try:
                t.start()
                t.join(timeout)
            except Exception as je:
                print ('error starting thread')
                raise je
            ret = res[0]
            # print("ret", ret)
            #print("ret 타입", type(ret))
            if isinstance(ret, BaseException):
                print("오류 발생")
                raise ret
            return ret
        return wrapper
    return deco