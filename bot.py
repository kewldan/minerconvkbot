#VK MINECRAFT BOT#
#   By: Avenger  #
#   02.06.2020   #
#  Version: 2.2  #

import vk_api #API #pip install vk_api
from vk_api.longpoll import VkLongPoll, VkEventType #LongPoll
from random import randrange #Случайные числа
import os #Для работы с FileSystem
from json import load, dump #JSON
from hashlib import sha256 #Хеширование
from sqlite3 import connect #Для БД AuthMe
from ftplib import FTP #Для скачивания БД AuthMe
from threading import Thread #Для потоков
from fuzzywuzzy.fuzz import ratio #Для сравнения строк #pip install fuzzywuzzy
from mcrcon import MCRcon #Для RCON #pip install mcrcon

#НАСТРОЙКИ
token = "" #Главный токен

LoggedUsersPath = "./logged.json" #JSON файл для БД
keyboards = {
    "auth": "./keyboards/auth.json", #JSON клавиатуры меню
    "Nauth": "./keyboards/nauth.json", #JSON клавиатуры админ меню
    "close": "./keyboards/close.json" #JSON клавиатуры отмены
}
Keyboards = {
    "guest": "./keyboards2/guest.json", #Клавиатура гостя
    "owner": "./keyboards2/owner.json" #Клавиатура владельца сервера
}
#/////////

if not os.path.exists(LoggedUsersPath):
    open(LoggedUsersPath, "w", encoding = "UTF-8").write("{}")
    DataBase = {}
else:
    with open(LoggedUsersPath, "r") as rf:
        DataBase = load(rf)

def have(m, i): #Имеет ли массив индекс
    try:
        m[i]
        return True
    except IndexError:
        return False

def checkToken(token):
    temp = vk_api.VkApi(token = token)
    try:
        temp.auth()
    except vk_api.AuthError:
        pass
    try:
        VkLongPoll(temp)
    except vk_api.ApiError as err:
        if err.error["error_code"] == 5:
            return False
        else:
            return err.error["error_code"]
    return True

def getPlayerDonate(host, port, password, player, FTPs):#TODO: Проверка PEX
    try:
        ftp = FTP(host, FTPs["USERNAME"], FTPs["PASSWORD"])
    except:
        return -1
    ftp.login(FTPs["USERNAME"], FTPs["PASSWORD"])

    if "plugins" in ftp.nlst():
        ftp.cwd("plugins")
    else:
        return -2
    
    if not "PermissionsEx" in ftp.nlst():
        return -3
    
    ftp.quit()
    mc = MCRcon(host, password, port)
    mc.connect()
    return mc.command("pex user " + player).split()[5]

def rcon(host, port, password, cmd):
    mc = MCRcon(host, password, port)
    mc.connect()
    return mc.command(cmd)

def maybeInt(inr):
    try:
        int(inr)
        return True
    except TypeError:
        return False

def checkPassword(linePass, checkPass): #Проверяю корректность пароля
    args = linePass.split("$")
    g = sha256(checkPass.encode("UTF-8")).hexdigest() + args[2]
    return linePass == "$SHA$" + args[2] + "$" + sha256(g.encode("UTF-8")).hexdigest()

for u in keyboards:
    if not os.path.exists(keyboards[u]):
        print("FATAL ERROR: НЕ НАЙДЕНА КЛАВИАТУРА " + u)
        exit(1)


class Main(Thread):
    def __init__(self, token):
        Thread.__init__(self)
        self.requestAuth = {}
        self.deleteUsers = {}
        self.controllUsers = {}
        self.vk = vk_api.VkApi(token = token) #Сессия VK

        try:
            self.vk.auth() #Авторизуюсь
        except vk_api.AuthError: #Если ошибка авторизации
            pass

    def checkOwner(self, owner_id):
        for h in DataBase:
            if DataBase[h]["OWNER"] == str(owner_id):
                return True
        return False

    def toMenu(self, user_id):
        if self.checkOwner(user_id):
            self.send_msg_with_keyboard(user_id, "Главное меню (Владелец)", Keyboards["owner"])
        else:
            self.send_msg_with_keyboard(user_id, "Главное меню (Гость)", Keyboards["guest"])
    
    def run(self):
        print("Main bot active")
        longpoll = VkLongPoll(self.vk) #Сессия LongPoll

        for event in longpoll.listen(): #Для каждого события
            if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
                if event.to_me: #Если сообщение мне
                    aid = str(event.user_id)
                    cmd = str(event.text).lower()
                    txt = event.text

                    if aid in self.requestAuth:
                        if cmd == "отменить":
                            self.send_msg_without_keyboard(aid, "Успешно, операция отменена")
                            self.toMenu(aid)
                            del self.requestAuth[aid]
                            continue
                        if self.requestAuth[aid][0] == 1:
                            if not txt in DataBase:
                                self.requestAuth[aid][1] = txt
                                self.requestAuth[aid][0] = 2
                                self.send_msg_without_keyboard(aid, "Успешно, введите Токен сообщества сервера (https://vk.com/dev/access_token?f=2.%20Ключ%20доступа%20сообщества)")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, сервер с таким названием уже существует")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 2:
                            if checkToken(txt):
                                self.requestAuth[aid][2]["TOKEN"] = txt
                                self.requestAuth[aid][0] = 3
                                self.send_msg_without_keyboard(aid, "Успешно, введите IP сервера")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, токен не корректен")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 3:
                            self.requestAuth[aid][2]["HOST"] = txt
                            self.requestAuth[aid][0] = 4
                            self.send_msg_without_keyboard(aid, "Успешно, введите привелегию, при которой можно возпользоватся консолью")
                        elif self.requestAuth[aid][0] == 4:
                            self.requestAuth[aid][2]["ConsoleAllowDonate"] = txt
                            self.requestAuth[aid][0] = 5
                            self.send_msg_without_keyboard(aid, "Успешно, введите RCON порт")
                        elif self.requestAuth[aid][0] == 5:
                            if maybeInt(txt):
                                self.requestAuth[aid][2]["RCON"]["PORT"] = int(txt)
                                self.requestAuth[aid][0] = 6
                                self.send_msg_without_keyboard(aid, "Успешно, введите RCON пароль")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, это не число")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 6:
                            self.requestAuth[aid][2]["RCON"]["PASSWORD"] = txt
                            self.requestAuth[aid][0] = 7
                            self.send_msg_without_keyboard(aid, "Успешно, введите MINECRAFT порт")
                        elif self.requestAuth[aid][0] == 7:
                            if maybeInt(txt):
                                self.requestAuth[aid][2]["MINECRAFT"]["PORT"] = int(txt)
                                self.requestAuth[aid][0] = 8
                                self.send_msg_without_keyboard(aid, "Успешно, введите FTP (Корневая папка - папка с server.jar) пользователя (Нужно право на чтение файлов)")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, это не число")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 8:
                            self.requestAuth[aid][2]["FTP"]["USERNAME"] = txt
                            self.requestAuth[aid][0] = 9
                            self.send_msg_without_keyboard(aid, "Успешно, введите FTP (Корневая папка - папка с server.jar) пароль от пользователя")
                        elif self.requestAuth[aid][0] == 9:
                            self.requestAuth[aid][2]["FTP"]["PASSWORD"] = txt
                            self.send_msg_without_keyboard(aid, "Успешно, ваш сервер зарегистрирован! Бот начнёт работать в ближайшее время")
                            DataBase[self.requestAuth[aid][1]] = self.requestAuth[aid][2]
                            with open(LoggedUsersPath, "w", encoding = "UTF-8") as f:
                                dump(DataBase, f)
                            bots.bots.append(MineBot(self.requestAuth[aid][2]["TOKEN"], self.requestAuth[aid][2], self.requestAuth[aid][1]))
                            bots.bots[len(bots.bots) - 1].start()
                            del self.requestAuth[aid]
                            self.toMenu(aid)
                            continue
                    
                    if aid in self.deleteUsers:
                        if cmd == "отменить":
                            self.send_msg_without_keyboard(aid, "Успешно, операция отменена")
                            self.toMenu(aid)
                            del self.deleteUsers[aid]
                            continue
                        else:
                            if txt == self.deleteUsers[aid]:
                                del DataBase[txt]
                                with open(LoggedUsersPath, "w", encoding = "UTF-8") as f:
                                    dump(DataBase, f)
                                self.send_msg_without_keyboard(aid, "Успешно, сервер удалён")
                                self.toMenu(aid)
                                del self.deleteUsers[aid]
                                continue
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, название сервера не корректно")
                                self.toMenu(aid)
                                del self.deleteUsers[aid]
                                continue
                    
                    if aid in self.controllUsers:
                        if cmd == "отменить":
                            self.send_msg_without_keyboard(aid, "Успешно, операция отменена")
                            self.toMenu(aid)
                            del self.controllUsers[aid]
                            continue
                        else:
                            if self.controllUsers[aid][0] == 1:
                                r = {"percent": 0, "index": 0}
                                allowValue = ["ip", "привелегия", "портrcon", "парольrcon", "портminecraft", "пользовательftp", "парольftp"]
                                for f in range(len(allowValue)):
                                    if ratio(cmd, allowValue[f]) > r["percent"]:
                                        r = {"percent": ratio(cmd, allowValue[f]), "index": f}
                                self.send_msg_without_keyboard(aid, "Успешно, выбран параметр " + allowValue[r["index"]].upper() + ", введите значение")
                                self.controllUsers[aid] = [2, r["index"]]
                            elif self.controllUsers[aid][0] == 2:
                                al = {5: "USERNAME", 6: "PASSWORD"}
                                for f in DataBase:
                                    if DataBase[f]["OWNER"] == aid:
                                        nam = f
                                if self.controllUsers[aid][1] == 0:
                                    DataBase[nam]["HOST"] = txt
                                    self.send_msg_without_keyboard(aid, "Успешно, IP пароль изменён на " + txt)
                                    self.toMenu(aid)
                                    del self.controllUsers[aid]
                                    continue
                                elif self.controllUsers[aid][1] == 1:
                                    DataBase[nam]["ConsoleAllowDonate"] = txt
                                    self.send_msg_without_keyboard(aid, "Успешно, привелегия для консоли изменена на " + txt)
                                    self.toMenu(aid)
                                    del self.controllUsers[aid]
                                    continue
                                elif self.controllUsers[aid][1] == 2:
                                    if maybeInt(txt):
                                        DataBase[nam]["RCON"]["PORT"] = int(txt)
                                        self.send_msg_without_keyboard(aid, "Успешно, RCON порт изменён на " + txt)
                                        self.toMenu(aid)
                                        del self.controllUsers[aid]
                                        continue
                                    else:
                                        self.send_msg_without_keyboard(aid, "Ошибка, это не число")
                                        self.toMenu(aid)
                                        del self.controllUsers[aid]
                                        continue
                                elif self.controllUsers[aid][1] == 3:
                                    DataBase[nam]["RCON"]["PASSWORD"] = txt
                                    self.send_msg_without_keyboard(aid, "Успешно, RCON пароль изменён на " + txt)
                                    self.toMenu(aid)
                                    del self.controllUsers[aid]
                                    continue
                                elif self.controllUsers[aid][1] == 4:
                                    if maybeInt(txt):
                                        DataBase[nam]["MINECRAFT"]["PORT"] = int(txt)
                                        self.send_msg_without_keyboard(aid, "Успешно, MINECRAFT порт изменён на " + txt)
                                        self.toMenu(aid)
                                        del self.controllUsers[aid]
                                        continue
                                    else:
                                        self.send_msg_without_keyboard(aid, "Ошибка, это не число")
                                        self.toMenu(aid)
                                        del self.controllUsers[aid]
                                        continue
                                elif self.controllUsers[aid][1] in [5, 6]:
                                    DataBase[nam]["FTP"][al[self.controllUsers[aid][1]]] = txt
                                    self.send_msg_without_keyboard(aid, "Успешно, FTP параметр изменён на " + txt)
                                    self.toMenu(aid)
                                    del self.controllUsers[aid]
                                    continue

                    if cmd in ["начать", "меню", "старт", "привет", "start"]:
                        self.toMenu(aid)
                    elif cmd == "зарегистрировать сервер" and not self.checkOwner(aid):
                        self.requestAuth[aid] = [1, "name", {
                            "TOKEN": "",
                            "OWNER": aid,
                            "HOST": "ip",
                            "ConsoleAllowDonate": "console",
                            "authed": {},
                            "RCON": {
                                "PORT": -1,
                                "PASSWORD": "rpass"
                            },
                            "MINECRAFT": {
                                "PORT": -1
                            },
                            "FTP": {
                                "USERNAME": "user",
                                "PASSWORD": "fpass"
                            }
                        }]
                        self.send_msg_with_keyboard(aid, "Успешно, запрос обрабатывается, введите Название сервера", keyboards["close"])
                    elif cmd == "удалить сервер" and self.checkOwner(aid):
                        nam = ""
                        for f in DataBase:
                            if DataBase[f]["OWNER"] == aid:
                                nam = f
                        self.deleteUsers[aid] = nam
                        self.send_msg_with_keyboard(aid, "Успешно, введите название сервера для подтверждения операции (" + nam + ")", keyboards["close"])
                    elif cmd == "управлять сервером" and self.checkOwner(aid):
                        self.controllUsers[aid] = [1, "valueToChange"]
                        for f in DataBase:
                            if DataBase[f]["OWNER"] == aid:
                                nam = f
                        Serv = DataBase[nam]
                        self.send_msg_without_keyboard(aid, """
Данные для чтения:
    Название сервера: {}
    Количество авторизованых людей: {}

Данные которые можно изменить:
    IP: {}
    Привелегия: {}
    ПортRcon: {}
    ПарольRcon: {}
    ПортMinecraft: {}
    ПользовательFTP: {}
    ПарольFTP: {}
                        """.format(nam, len(Serv["authed"]), Serv["HOST"], Serv["ConsoleAllowDonate"], Serv["RCON"]["PORT"], Serv["RCON"]["PASSWORD"], Serv["MINECRAFT"]["PORT"], Serv["FTP"]["USERNAME"], Serv["FTP"]["PASSWORD"]))
                        self.send_msg_with_keyboard(aid, "Успешно, выберите параметр который хотите изменить", keyboards["close"])
                    elif not aid in self.controllUsers and not aid in self.requestAuth and not aid in self.deleteUsers:
                        self.send_msg_without_keyboard(aid, "Ошибка, команда не распознана, напишите \"меню\"")
                    self.vk.method("messages.markAsRead", {"peer_id": aid, "message_id": self.vk.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение

    def send_msg_without_keyboard(self, peer, message): #Отправить сообщение без клавиатуры
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

    def send_msg_with_keyboard(self, peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})

class MineBot(Thread):
    def __init__(self, token, settings, name):
        Thread.__init__(self) #Отдельный поток
        self.Server = settings #Настройки
        self.name = name #Название сервера
        self.authed = self.Server["authed"] #Авторизированые пользователи
        self.vk = vk_api.VkApi(token = token) #Сессия VK

        self.authUsers = {} #Пользователи которые авториуются
        self.enterUsers = {} #Пользователи которые вводят команду
        self.changeUsers = {} #Пользователи которые меняют пароль

        try:
            self.vk.auth() #Авторизуюсь
        except vk_api.AuthError: #Если ошибка авторизации
            pass
    
    def run(self):
        print("Mine bot " + self.name + " is active\n")
        longpoll = VkLongPoll(self.vk) #Сессия LongPoll

        for event in longpoll.listen(): #Для каждого события
            if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
                if event.to_me: #Если сообщение мне
                    aid = str(event.user_id) #ID
                    cmd = str(event.text).lower()

                    if aid in self.authUsers:
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
                            del self.authUsers[aid]
                        elif self.authUsers[aid][0] == 1:
                            self.authUsers[aid] = [2, event.text]
                            self.send_msg_without_keyboard(aid, "Успешно, введите пароль (Обработка занимает много времени)")
                        elif self.authUsers[aid][0] == 2:
                            if self.getDBFile(self.Server["HOST"], self.Server["FTP"]["USERNAME"], self.Server["FTP"]["PASSWORD"], aid) == -1:
                                self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен не правильно", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue
                            conn = connect("DB" + self.name + ".db")
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM 'authme'")
                            conn.commit()
                            isHave = -1
                            for u in cursor.fetchall():
                                if u[1] == self.authUsers[aid][1]:
                                    isHave = u[3]
                            if isHave == -1:
                                self.send_msg_with_keyboard(aid, "Ошибка, вас нету в базе данных AuthMe", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue
                            valid = True
                            free = False
                            if not checkPassword(isHave, event.text):
                                valid = False
                            if valid: #Если логин и пароль верны
                                for i in self.authed: #Если нету такого ника в базе
                                    if self.authed[i][0] == self.authUsers[aid][1]:
                                        self.send_msg_with_keyboard(aid, "Ошибка, к этому аккаунту уже привязан ВК профиль", keyboards["Nauth"])
                                        del self.authUsers[aid]
                                        free = True
                                if free:
                                    continue
                                self.authed[aid] = [self.authUsers[aid][1], event.text]
                                self.Server["authed"][aid] = [self.authUsers[aid][1], event.text]
                                DataBase[self.name] = self.Server
                                with open(LoggedUsersPath, "w") as wf:
                                    dump(DataBase, wf)
                                self.send_msg_with_keyboard(aid, "Успешно, вы авторизованы", keyboards["auth"])
                                del self.authUsers[aid]
                                continue
                            else:
                                self.send_msg_with_keyboard(aid, "Ошибка, логин или пароль некорректны", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue

                    if aid in self.enterUsers:
                        rs = getPlayerDonate(self.Server["HOST"], self.Server["RCON"]["PORT"], self.Server["RCON"]["PASSWORD"], self.authed[aid][0], self.Server["FTP"])
                        if rs == -1:
                            self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен неправильно", keyboards["auth"])
                            self.sendError("[https://vk.com/id{}] Ошибка подключения к FTP")
                            del self.enterUsers[aid]
                            continue
                        elif rs == -2:
                            self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен неправильно", keyboards["auth"])
                            self.sendError("[https://vk.com/id{}] FTP папка plugins не доступна")
                            del self.enterUsers[aid]
                            continue
                        elif rs == -3:
                            self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен неправильно", keyboards["auth"])
                            self.sendError("[https://vk.com/id{}] FTP папка plugins/PermissionsEx не доступна")
                            del self.enterUsers[aid]
                            continue
                        elif rs == "CONNECT ERR":
                            self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                            del self.enterUsers[aid]
                            continue
                        elif rs == "FAIL":
                            self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен не правильно", keyboards["auth"])
                            self.sendError("[https://vk.com/id{}] Ошибка подключения к RCON")
                            del self.enterUsers[aid]
                        else:
                            if not rs == self.Server["ConsoleAllowDonate"]:
                                self.send_msg_with_keyboard(aid, "Ошибка, пользователь с этим ником не имеет привелегии " + self.Server["ConsoleAllowDonate"], keyboards["auth"])
                                del self.enterUsers[aid]
                                continue
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                            del self.enterUsers[aid]
                        elif self.enterUsers[aid][0] == 1:
                            rs = rcon(self.Server["HOST"], self.Server["RCON"]["PORT"], self.Server["RCON"]["PASSWORD"], event.text)
                            if rs == "CONNECT ERR":
                                self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                                del self.enterUsers[aid]
                            elif rs == "FAIL":
                                self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен не правильно", keyboards["auth"])
                                self.sendError("[https://vk.com/id{}] Ошибка подключения к RCON")
                                del self.enterUsers[aid]
                            else: 
                                try:
                                    self.send_msg_with_keyboard(aid, rs, keyboards["auth"])
                                    continue
                                except:
                                    pass
                                del self.enterUsers[aid]

                    if aid in self.changeUsers:
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                            del self.changeUsers[aid]
                        elif self.changeUsers[aid][0] == 1:
                            self.changeUsers[aid] = [2, event.text]
                            self.send_msg_without_keyboard(aid, "Успешно, введите новый пароль")
                        elif self.changeUsers[aid][0] == 2:
                            if self.authed[aid][1] == self.changeUsers[aid][1]:
                                rs = rcon(self.Server["HOST"], self.Server["RCON"]["PORT"], self.Server["RCON"]["PASSWORD"], "authme password " + self.authed[aid][0] + " " + event.text)
                                if rs == "CONNECT ERR":
                                    self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                                    del self.changeUsers[aid]
                                    continue
                                elif rs == "FAIL":
                                    self.send_msg_with_keyboard(aid, "Ошибка, сервер настроен не правильно", keyboards["auth"])
                                    self.sendError("[https://vk.com/id{}] Ошибка подключения к RCON")
                                    del self.changeUsers[aid]
                                    continue
                                else: 
                                    self.send_msg_with_keyboard(aid, "Успешно, пароль изменён", keyboards["auth"])
                                    del self.changeUsers[aid]
                                    continue
                            else:
                                self.send_msg_with_keyboard(aid, "Ошибка, ваш старый пароль некорректен", keyboards["auth"])
                                del self.changeUsers[aid]
                                continue

                    if cmd in ["начать", "меню", "старт", "привет", "start"]:
                        if aid in self.authed:
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                        else:
                            self.send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
                    elif cmd == "зарегистрироваться" and not aid in self.authed:
                        self.authUsers[aid] = [1, "login"]
                        self.send_msg_with_keyboard(aid, "Введите свой никнейм", keyboards["close"])
                    elif cmd == "ввести команду" and aid in self.authed and not aid in self.changeUsers:
                        self.enterUsers[aid] = [1, "cmd"]
                        self.send_msg_with_keyboard(aid, "Успешно, введите команду", keyboards["close"])
                    elif cmd == "сменить пароль" and aid in self.authed and not aid in self.enterUsers:
                        self.changeUsers[aid] = [1, "oldPass"]
                        self.send_msg_with_keyboard(aid, "Успешно, введите старый пароль", keyboards["close"])
                    elif not aid in self.changeUsers and not aid in self.authUsers and not aid in self.enterUsers and not cmd == "отменить":
                        self.send_msg_without_keyboard(aid, "Ошибка, команда не распознана, напишите \"меню\"")
                    self.vk.method("messages.markAsRead", {"peer_id": aid, "message_id": self.vk.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение

    def getDBFile(self, host, user, password, aid): #Получаю по FTP БД AuthMe
        try:
            ftp = FTP(host, user, password)
        except:
            self.sendError("[https://vk.com/id{}] Сервер FTP недоступен".format(aid))
            return -1
        ftp.login(user, password)
        if "plugins" in ftp.nlst():
            ftp.cwd("plugins")
        else:
            self.sendError("[https://vk.com/id{}] FTP папка plugins не доступна".format(aid))
            return -1
        if "PlugMan" in ftp.nlst():
            rcon(self.Server["HOST"], self.Server["RCON"]["PORT"], self.Server["RCON"]["PASSWORD"], "plugman disable AuthMe")
        else:
            self.sendError("[https://vk.com/id{}] FTP папка plugins/PlugMan не доступна".format(aid))
            return -1
        if "AuthMe" in ftp.nlst():
            ftp.cwd("AuthMe")
        else:
            self.sendError("[https://vk.com/id{}] FTP папка plugins/AuthMe не доступна".format(aid))
            return -1
        if not "authme.db" in ftp.nlst():
            self.sendError("[https://vk.com/id{}] FTP файл plugins/AuthMe/authme.db не доступен".format(aid))
            return -1
        with open("DB" + self.name + ".db", "wb") as f:
            ftp.retrbinary("RETR authme.db", f.write)
        ftp.quit()
        rcon(self.Server["HOST"], self.Server["RCON"]["PORT"], self.Server["RCON"]["PASSWORD"], "plugman enable AuthMe")

    def send_msg_without_keyboard(self, peer, message): #Отправить сообщение без клавиатуры
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

    def send_msg_with_keyboard(self, peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})

    def sendError(self, msg):
        bots.mainBot.send_msg_without_keyboard(self.Server["OWNER"], "[ОШИБКА БОТА] " + msg)



class Bots:
    def __init__(self, mainToken):
        self.bots = []
        self.mainBot = Main(mainToken)
        for b in DataBase:
            self.bots.append(MineBot(DataBase[b]["TOKEN"], DataBase[b], b))
            self.bots[-1].start()
        self.mainBot.start()
bots = Bots(token)