#VK MINECRAFT BOT#
#  By: Avenger   #
#   28.05.2020   #

import vk_api #API #pip install vk_api
from vk_api.longpoll import VkLongPoll, VkEventType #LongPoll
from random import randrange #Случайные числа
from os.path import exists #Для работы с FileSystem
from json import load, dump #JSON
from requests import post #Запросы к YCAPI #pip install requests
from hashlib import sha256 #Хеширование
from sqlite3 import connect #Для БД AuthMe
from ftplib import FTP #Для скачивания БД AuthMe

#НАСТРОЙКИ
token = "" #Токен сообщества
Server = {
    "RCON": { #RCON данные
        "HOST": "149.202.225.53",
        "PORT": 17565,
        "PASSWORD": ""
    },
    "QUERY": { #QUERY данные (Необязательно)
        "HOST": "149.202.225.53",
        "PORT": 16565
    },
    "MINECRAFT": { #Данные для подключения к серверу
        "HOST": "149.202.225.53",
        "PORT": 25565
    },
    "FTP": { #Данные для подключения по FTP (Порт - 21)
        "HOST": "149.202.225.53", #FTP хост
        "USERNAME": "", #FTP имя (ОБЯЗАТЕЛЬНОЕ ПРАВО - ЧТЕНИЕ)
        "PASSWORD": "", #FTP пароль
        "DataBaseFile": "authme.db" #Название файла БД AuthMe
    }
} 

LoggedUsersPath = "./logged.json" #JSON файл для залогининых юзеров
ConsoleAllowDonate = "console" #Название доната при котором разрешается консоль
keyboards = {
    "auth": "./keyboards/auth.json", #JSON клавиатуры меню
    "Nauth": "./keyboards/nauth.json", #JSON клавиатуры админ меню
    "close": "./keyboards/close.json" #JSON клавиатуры отмены
}
#/////////

#Как установить
#
#1. Скачайте скрипт
#2. Настройте его
#3. Скачайте и установите на сервер плагины: Permissions EX, AuthMe, Plugman
#4. Запустите скрипт
#

for u in keyboards:
    if not exists(keyboards[u]):
        print("FATAL ERROR: НЕ НАЙДЕНА КЛАВИАТУРА " + u)
        exit(1)

if not exists(LoggedUsersPath):
    open(LoggedUsersPath, "w", encoding = "UTF-8").write("{}")

with open(LoggedUsersPath, "r") as rf:
    authed = load(rf)

vk_session = vk_api.VkApi(token = token) #Сессия VK

authUsers = {} #Пользователи которые авториуются
enterUsers = {} #Пользователи которые вводят команду
changeUsers = {}

try:
    vk_session.auth() #Авторизуюсь
except vk_api.AuthError: #Если ошибка авторизации
    pass

longpoll = VkLongPoll(vk_session) #Сессия LongPoll

def checkPassword(linePass, checkPass): #Проверяю корректность пароля
    args = linePass.split("$")
    g = sha256(checkPass.encode("UTF-8")).hexdigest() + args[2]
    return linePass == "$SHA$" + args[2] + "$" + sha256(g.encode("UTF-8")).hexdigest()

def getDBFile(host, user, password): #Получаю по FTP БД AuthMe
    ftp = FTP(host, user, password)
    ftp.login(user, password)
    ftp.cwd("plugins")
    ftp.cwd("AuthMe")
    if post("https://ylousrp.ru/API/monitoring.php", {"ip": Server["MINECRAFT"]["HOST"], "port": Server["MINECRAFT"]["PORT"]}).json()["online"]:
        post("https://ylousrp.ru/API/rcon.php", data = {"ip": Server["RCON"]["HOST"], "port": Server["RCON"]["PORT"], "password": Server["RCON"]["PASSWORD"], "cmd": "plugman disable AuthMe"})
    rtrn = ""
    def write(text):
        global rtrn
        rtrn = text
    ftp.retrbinary("RETR " + Server["FTP"]["DataBaseFile"], write)
    ftp.quit()
    if post("https://ylousrp.ru/API/monitoring.php", {"ip": Server["MINECRAFT"]["HOST"], "port": Server["MINECRAFT"]["PORT"]}).json()["online"]:
        post("https://ylousrp.ru/API/rcon.php", data = {"ip": Server["RCON"]["HOST"], "port": Server["RCON"]["PORT"], "password": Server["RCON"]["PASSWORD"], "cmd": "plugman enable AuthMe"})
    return rtrn

def get_user(user_id): #Получить профиль человека
    return vk_session.method("users.get", {"user_id": user_id, "fields": "city, sex", "name_case": "Nom"})

def send_msg_without_keyboard(peer, message): #Отправить сообщение без клавиатуры
    vk_session.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

def send_msg_with_keyboard(peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
    vk_session.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})

def have(m, i): #Имеет ли массив индекс
    try:
        m[i]
        return True
    except IndexError:
        return False

def maybeInt(inr):
    try:
        int(inr)
        return True
    except TypeError:
        return False

def send_msgs(peers, message): #Отправить рассылку
    if len(peers) > 100:
        return
    peers2 = []
    for f in range(len(peers)):
        peers2[f] = str(peers[f])
    vk_session.method("messages.send", {"user_ids": ",".join(peers2), "message": message, "random_id": randrange(0, 184467440737095516165, 1)})
    

for event in longpoll.listen(): #Для каждого события
    if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
        if event.to_me: #Если сообщение мне
            aid = str(event.user_id)
            cmd = str(event.text).lower()

            if aid in authUsers:
                if cmd == "отменить":
                    send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
                    del authUsers[aid]
                elif authUsers[aid][0] == 1:
                    authUsers[aid] = [2, event.text]
                    send_msg_without_keyboard(aid, "Успешно, введите пароль")
                elif authUsers[aid][0] == 2:
                    getDBFile(Server["FTP"]["HOST"], Server["FTP"]["USERNAME"], Server["FTP"]["PASSWORD"])
                    conn = connect(Server["FTP"]["DataBaseFile"])
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM 'authme'")
                    conn.commit()
                    isHave = -1
                    for u in cursor.fetchall():
                        if u[1] == authUsers[aid][1]:
                            isHave = u[3]
                    if isHave == -1:
                        send_msg_with_keyboard(aid, "Ошибка, вас нету в базе данных AuthMe", keyboards["Nauth"])
                        del authUsers[aid]
                        continue
                    valid = True
                    free = False
                    if not checkPassword(isHave, event.text):
                        valid = False
                    if valid: #Если логин и пароль верны
                        for i in authed: #Если нету такого ника в базе
                            if authed[i][0] == authUsers[aid][1]:
                                send_msg_with_keyboard(aid, "Ошибка, к этому аккаунту уже привязан ВК профиль", keyboards["Nauth"])
                                del authUsers[aid]
                                free = True
                        if free:
                            continue
                        rs = post("https://ylousrp.ru/API/getPlayerDonate.php", data = {"ip": Server["RCON"]["HOST"], "port": Server["RCON"]["PORT"], "password": Server["RCON"]["PASSWORD"], "player": authUsers[aid][1]})
                        if not rs.status_code == 200:
                            send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["Nauth"])
                            del authUsers[aid]
                            continue
                        else:
                            if rs.text == "Connecting error":
                                send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["Nauth"])
                                del authUsers[aid]
                                continue
                            else:
                                if not rs.text == ConsoleAllowDonate:
                                    send_msg_with_keyboard(aid, "Ошибка, пользователь с этим ником не имеет привелегии " + ConsoleAllowDonate, keyboards["Nauth"])
                                    del authUsers[aid]
                                    continue
                        authed[aid] = [authUsers[aid][1], event.text]
                        with open(LoggedUsersPath, "w") as wf:
                            dump(authed, wf)
                        send_msg_with_keyboard(aid, "Успешно, вы авторизованы", keyboards["auth"])
                        del authUsers[aid]
                    else:
                        send_msg_with_keyboard(aid, "Ошибка, логин или пароль некорректны", keyboards["Nauth"])
                        del authUsers[aid]
                        continue

            if aid in enterUsers:
                if cmd == "отменить":
                    send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                    del enterUsers[aid]
                elif enterUsers[aid][0] == 1:
                    rs = post("https://ylousrp.ru/API/rcon.php", data = {"ip": Server["RCON"]["HOST"], "port": Server["RCON"]["PORT"], "password": Server["RCON"]["PASSWORD"], "cmd": event.text})
                    if not rs.status_code == 200:
                        print(rs.status_code)
                        send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["Nauth"])
                        del enterUsers[aid]
                    else:
                        if rs.text == "Connecting error":
                            send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["Nauth"])
                            del enterUsers[aid]
                        elif rs.text == "REQUEST INVALID":
                            print("ERROR:", rs.text)
                            send_msg_with_keyboard(aid, "Ошибка, внутриняя ошибка скрипта бота", keyboards["Nauth"])
                            del enterUsers[aid]
                        else: 
                            try:
                                send_msg_with_keyboard(aid, rs.text, keyboards["auth"])
                            except:
                                pass
                            del enterUsers[aid]

            if aid in changeUsers:
                if cmd == "отменить":
                    send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                    del changeUsers[aid]
                elif changeUsers[aid][0] == 1:
                    changeUsers[aid] = [2, event.text]
                    send_msg_without_keyboard(aid, "Успешно, введите новый пароль")
                elif changeUsers[aid][0] == 2:
                    if authed[aid][1] == changeUsers[aid][1]:
                        rs = post("https://ylousrp.ru/API/rcon.php", data = {"ip": Server["RCON"]["HOST"], "port": Server["RCON"]["PORT"], "password": Server["RCON"]["PASSWORD"], "cmd": "authme password " + authed[aid][0] + " " + event.text})
                        if not rs.status_code == 200:
                            print(rs.status_code)
                            send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["auth"])
                            del changeUsers[aid]
                        else:
                            if rs.text == "Connecting error":
                                send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                                del changeUsers[aid]
                            elif rs.text == "REQUEST INVALID":
                                print("ERROR:", rs.text)
                                send_msg_with_keyboard(aid, "Ошибка, внутриняя ошибка скрипта бота", keyboards["auth"])
                                del changeUsers[aid]
                            else: 
                                send_msg_with_keyboard(aid, "Успешно, пароль изменён", keyboards["auth"])
                                del changeUsers[aid]
                    else:
                        send_msg_with_keyboard(aid, "Ошибка, ваш старый пароль некорректен", keyboards["auth"])
                        del changeUsers[aid]

            if cmd in ["начать", "меню", "старт"]:
                if aid in authed:
                    send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                else:
                    send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
            elif cmd == "зарегистрироваться" and not aid in authed:
                authUsers[aid] = [1, "login"]
                send_msg_with_keyboard(aid, "Введите свой никнейм", keyboards["close"])
            elif cmd == "ввести команду" and aid in authed and not aid in changeUsers:
                enterUsers[aid] = [1, "cmd"]
                send_msg_with_keyboard(aid, "Успешно, введите команду", keyboards["close"])
            elif cmd == "поменять пароль" and aid in authed and not aid in enterUsers:
                changeUsers[aid] = [1, "oldPass"]
                send_msg_with_keyboard(aid, "Успешно, введите старый пароль", keyboards["close"])
            vk_session.method("messages.markAsRead", {"peer_id": aid, "message_id": vk_session.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение