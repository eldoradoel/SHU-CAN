import time
from requests import session
import socket
import threading


class ShuNetwork:
    def __init__(self):
        # 学号
        self.userId = ""
        # 密码
        self.password = ""
        # 电信宽带账号
        self.telecomUserId = ""
        # 电信宽带密码
        self.telecomPassword = ""
        self.useTelecom = False
        self.needSendChangeMessage = False
        self.userIndex = ""
        self.successCount = 0
        self.failCount = 0
        self.session = session()
        self.session.headers[
            'User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"

    @staticmethod
    def printLog(message):
        print("{} {}".format(time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime()), message))

    @staticmethod
    def checkInternetConnect():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(5)
            result = sock.connect_ex(("223.5.5.5", 53))
            sock.shutdown(socket.SHUT_RDWR)
            return result == 0
        except socket.error:
            return False
        finally:
            sock.close()

    def sendNetworkChangeMessage(self, message):
        try:
            self.session.get("".format(message))
        except Exception as e:
            self.printLog("发送网络变更消息时程序异常 {}".format(e))

    def getLocalLoginStatus(self):
        return "中国电信" if self.useTelecom else "校园网"

    def getLoginStatus(self):
        try:
            r = self.session.post("http://10.10.9.9:8080/eportal/InterFace.do?method=getOnlineUserInfo", timeout=(30, 30))
            r.encoding = "utf-8"
            resp = r.json()
            if r.status_code == 200:
                if resp["result"] == "success":
                    self.userIndex = resp["userIndex"]
                    if resp["service"] == "校园网":
                        self.useTelecom = False
                    elif resp["service"] == "中国电信":
                        self.useTelecom = True
                    return 1
                elif resp["result"] == "fail":
                    return 2
                else:
                    self.printLog("登陆状态获取异常 {}".format(r.text))
                    return 3
            else:
                self.printLog("校园网认证服务异常 {}  {}".format(r.status_code, r.text))
                return 4
        except Exception as e:
            self.printLog("获取登陆状态时程序异常 {}".format(e))
            return 4

    def getLoginQueryString(self):
        r = self.session.get("http://123.123.123.123/", allow_redirects=False)
        r.encoding = 'utf-8'
        st = r.text.find("index.jsp?") + 10
        end = r.text.find("'</script>")
        return r.text[st:end]

    def connect(self):
        data = {"userId": self.userId if not self.useTelecom else self.telecomUserId,
                "password": self.password if not self.useTelecom else self.telecomPassword,
                "passwordEncrypt": "false",
                "queryString": self.getLoginQueryString(),
                "service": "shu" if not self.useTelecom else "%E4%B8%AD%E5%9B%BD%E7%94%B5%E4%BF%A1",
                "operatorPwd": "",
                "operatorUserId": "",
                "validcode": ""}
        r = self.session.post(
            "http://10.10.9.9:8080/eportal/InterFace.do?method=login", data=data, timeout=(30, 30))
        r.encoding = "utf-8"
        resp = r.json()
        self.userIndex = resp["userIndex"]
        self.printLog("登陆至 {} 登陆状态 {} {}".format(
            self.getLocalLoginStatus(), resp["result"], resp["message"]))
        self.printLog("调试信息 [{}]--[{}]".format(data, r.text))

    def disconnect(self):
        data = {"userIndex": self.userIndex}
        r = self.session.post(
            "http://10.10.9.9:8080/eportal/InterFace.do?method=logout", data=data, timeout=(30, 30))
        r.encoding = "utf-8"
        resp = r.json()
        self.printLog("离线状态 {} {}".format(resp["result"], resp["message"]))

    def startConnectLoop(self):
        if not self.checkInternetConnect():
            self.failCount += 1
        else:
            self.successCount += 1
            self.failCount = 0
        if self.failCount == 2:
            shuNetworkStatus = self.getLoginStatus()
            if shuNetworkStatus == 1:
                self.useTelecom = not self.useTelecom
                self.printLog("已登陆 无法连接到公网 切换连接至 {}".format(
                    self.getLocalLoginStatus()))
                try:
                    self.disconnect()
                    time.sleep(1)
                    self.connect()
                except Exception as e:
                    self.printLog("切换连接时程序异常 {}".format(e))
                self.needSendChangeMessage = True
            elif shuNetworkStatus == 2:
                self.printLog("未登陆 无法连接到公网")
                try:
                    self.connect()
                except Exception as e:
                    self.printLog("连接时程序异常 {}".format(e))
            elif shuNetworkStatus == 4:
                self.printLog("校园网认证服务异常 无法连接到公网")
            self.failCount = 0
        if self.successCount == 12:
            self.getLoginStatus()
            self.printLog("网络连接正常 登陆至 {}".format(self.getLocalLoginStatus()))
            if self.needSendChangeMessage:
                # self.sendNetworkChangeMessage(
                #     "网络连接切换 登陆至 {}".format(self.getLocalLoginStatus()))
                self.needSendChangeMessage = False
            self.successCount = 0
        threading.Timer(10, self.startConnectLoop).start()


shu = ShuNetwork()

if __name__ == "__main__":
    shu.startConnectLoop()
