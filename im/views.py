import os, copy
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
from .form import CreditForm, excelForm, excelLogin, userForm
import datetime
from datetime import date, timedelta
from random import randint
import openpyxl
from collections import OrderedDict
from jinja2 import Environment, FileSystemLoader
from pyecharts.globals import CurrentConfig
CurrentConfig.GLOBAL_ENV = Environment(loader=FileSystemLoader("/var/www/django/credit/templates"))

def Credit(request) : # 選擇學年及領域頁面
    form = CreditForm(request.POST)
    form_lec = userForm(request.POST)
    if "send" in request.POST :
        if form.is_valid() and form_lec.is_valid() :
            form_lec.save()
            request.session['text'] = form_lec.cleaned_data['all_data']
            request.session['year'] = request.POST['year']
            if request.POST['year'] == "107" : # 107 學年
                stand = [12.0, 19.0, 9.0, 39.0, 21.0, 12.0, 20.0] # 各領域最低學分門檻
                request.session['stand'] = stand
                if request.POST['domain']== "1" : # 技術
                    return creMain(request, 1, request.POST['year'], stand)
                if request.POST['domain']== "2" : # 管理
                    return creMain(request, 2, request.POST['year'], stand)
            elif request.POST['year'] == "108" : # 108 學年
                stand = [12.0, 19.0, 15.0, 30.0, 24.0, 12.0, 20.0]
                request.session['stand'] = stand
                if request.POST['domain']== "1" : # 技術
                    return creMain(request, 1, request.POST['year'], stand)
                if request.POST['domain']== "2" : # 管理
                    return creMain(request, 2, request.POST['year'], stand)
    context = {"form" : form, "form_lec" : form_lec}
    return render(request, "credit.html", context)

def creMain(request, domain, year, stand) : # 主頁面
    path = "/var/www/django/credit/media/Excel"
    if not mkLec(path, year) : # 沒資料
        return render(request, "creMain.html", {"no_data" : True})
    mkSameList() # 製作全校共同課程的二維陣列
    #a = request.POST['text']
    a = request.session.get('text')
    b = a.split("\r\n")
    cut = []
    total = []
    for i in range(len(b)) : # 分大組
        if b[i] == '' : # 遇到空一行
            total.append(cut) # 加入 list
            cut = []
            continue # 重新找，不然會把 '' 加到 list
        cut.append(b[i])
        if  i == len(b)-1: # 或是最後一個也要加入 list
            total.append(cut)
            cut = []
    name = ""
    if len(total[0]) < 2 :
        return render(request, "creMain.html", {"ale_wrong_input" : True})
    for i in total[0][1] : # 找名字
        if i != "的" :
            name += i
        else :
            break
    total[0].pop(0) # 不要前兩行
    total[0].pop(0) # 原本的 index1 變 index0
    seme_dic, semi_dic, other_info = mkSemeDic(total) # 只有全部學期的字典，以學年度為 key
    lec_same_cre = 0 # 全校共同課程總共學分
    lec_same = {"lec_same_cre": lec_same_cre} # 全校共同課程，先塞一個頭，因rowspan要len+1i
    tongs_dic = {"liber" : [0], "history" : [0], "law" : [0], "social" : [0], "engi" : [0], "life" : [0] , "green" : [0], "east" : [0], "local" : [0]}
    tongs_cre = {"liber" : [0], "history" : [0], "law" : [0], "social" : [0], "engi" : [0], "life" : [0] , "green" : [0], "east" : [0], "local" : [0]} # 已經修過的通識課的學分
    lec_same_short_name = [] # 已經有上過的課程的簡短課名，ex. 英文上
    tongs_name_only = [] # 只有修過的通識課的課名
    college_name_cre = {"total_cre" : 0} #　key = 院必修課的課名、value = 學分
    depart_name_cre = {"total_cre" : 0} #　key = 系必修課的課名、value = 學分
    tech_name_cre = {"total_cre" : 0} # key = 技術領域的課名, value = 學分
    mana_name_cre = {"total_cre" : 0} # key = 管理領域的課名, value = 學分
    profe_name_cre = {"total_cre" : 0} # key = 系專選的課名, value = 學分
    global other_dic
    other_dic = {"total_cre" : 0} # 沒有在以上課名，都當自由學分
    for i in seme_dic :
        for j in range(len(seme_dic[i])-1) : # 最後一個是共修多少學分，不要算
            if not isFloat(seme_dic[i][j][3]) : # 成績未送達
                continue # 找下個 value，因為有可能相同學期有些先送達
            if float(seme_dic[i][j][3]) < 60.0 : # 有及格
                continue # 沒及格找下一個
            course_name = ckCourseName(seme_dic[i][j]) # 檢查課程名稱，有可能是中間有空白
            same, short_name = lecSame(course_name)  # 是否在全校共同
            if same : # 如果有過的全校共同
                lec_same_cre += float(seme_dic[i][j][1][:3]) # 算總全校共同學分
                lec_same[same] = seme_dic[i][j][1] # 加入課名為 key ，學分為 value 的 dici
                lec_same_short_name.append(short_name) # 通用的課名
                continue # 找下一個課名
            tongs_name = tongsCk(course_name) # 是否在通識，回傳[課名,領域]
            if tongs_name : # 有過的通識
                tongs_name_only.append(tongs_name[0])
                tongs_dic[tongs_name[1]].append({tongs_name[0]:seme_dic[i][j][1]})
                tongs_cre[tongs_name[1]].append(seme_dic[i][j][1][:3])
                continue # 找下一個課名
            college_name = collegeCk(course_name) # 是否在院必修
            if college_name : # 是院必修
                college_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                college_name_cre[college_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                continue
            depart_name = departCk(course_name) # 是否在系必修
            if depart_name : # 是院必修
                depart_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                depart_name_cre[depart_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                continue
            tech_name = techCk(course_name) # 是否在技術領域
            if tech_name : # 是技術領域
                tech_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                tech_name_cre[tech_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                continue
            mana_name = manaCk(course_name) # 是否在管理領域
            if mana_name : # 是管理領域
                mana_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                mana_name_cre[mana_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                continue
            profe_name = profeCk(course_name) # 是否在無領域系專選
            if profe_name :
                profe_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                profe_name_cre[profe_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                continue
            other_dic['total_cre'] += float(seme_dic[i][j][1][:3])
            other_dic[course_name] = seme_dic[i][j][1][:3] # 其他課程，可當自由學分
    #redundSame(lec_same) # 把多餘的特色體育放進自由學分
    #human_cre = redundTongs(tongs_dic) # 把多餘的通識放進自由學分
    total_profe_len = len(profe_name_cre) + len(mana_name_cre) + len(tech_name_cre)
    other_cre = profe_name_cre['total_cre'] + mana_name_cre['total_cre'] # 管理+非次領域的修過學分
    other_cre1 = profe_name_cre['total_cre'] + tech_name_cre['total_cre'] # 管理+非次領域的修過學分
    other_len = len(profe_name_cre) + len(mana_name_cre) - 1
    other_len1 = len(profe_name_cre) + len(tech_name_cre) - 1
    request.session['other_dic'] = other_dic
    request.session['profe_name_cre'] = profe_name_cre
    request.session['mana_name_cre'] = mana_name_cre
    request.session['tech_name_cre'] = tech_name_cre
    request.session['depart_name_cre'] = depart_name_cre
    request.session['college_name_cre'] = college_name_cre
    request.session["tongs_name_only"] = tongs_name_only
    same_nece = ckNecessary(lec_same_short_name, lec_same_cre, stand) # 檢查各領域是否有還沒修完的必修課
    request.session['lec_same_short_name'] = lec_same_short_name
    lec_same['lec_same_cre'] = lec_same_cre
    tongs_len, tongs_cre_sep = ckLength(tongs_dic) # 通識的長度(課數)、通識的學分、領域數
    #free_dic = ckFree(lec_same, tongs_dic, tech_name_cre, mana_name_cre, profe_name_cre) # 可以當做自由學分的課程
    fin_cre = float(lec_same['lec_same_cre'])+float(tongs_cre_sep['human'][0])+float(tongs_cre_sep['society'][0])+float(tongs_cre_sep['science'][0])+float(tongs_cre_sep['spe'][0])+float(college_name_cre['total_cre'])+float(depart_name_cre['total_cre'])+float(tech_name_cre['total_cre'])+float(mana_name_cre['total_cre'])+float(profe_name_cre['total_cre'])+float(other_dic['total_cre'])
    context = {"fin_cre" : fin_cre, "total_pro_cre" : tech_name_cre['total_cre']+mana_name_cre['total_cre']+profe_name_cre['total_cre'], "sum_stand_pro" : stand[4]+stand[5], "total_stand" : sum(stand), "stand" : stand, "date" : datetime.date.today(), "other_cre1" : other_cre1, "other_len1" : other_len1, "depart_107" : east, "college_107" : local, "other_info" : other_info, "semi_dic" : semi_dic, "total" : total, "other_dic" : other_dic, "total_profe_len" : total_profe_len, "other_len" : other_len, "other_cre" : other_cre, "profe_name_cre" : profe_name_cre, "mana_name_cre" : mana_name_cre, "tech_name_cre" : tech_name_cre, "depart_name_cre" : depart_name_cre, "college_name_cre" : college_name_cre, "tongs_pass" : tongsPass(tongs_cre_sep), "tongs_cre_sep" : tongs_cre_sep, "tongs_len" : tongs_len, "name" : name, "domain" : domain, "seme_dic" : seme_dic, "year" : request.POST["year"], "lec_same" : lec_same, "same_nece" : same_nece, "tongs_dic" : tongs_dic, "tongs_cre" : tongs_cre, "test" : [1,1,1,1]}
    return render(request, "creMain.html", context)

def profeCk(course_name) : # 檢查是否在院必修
    if course_name in pro :
        return course_name
    else :
        return False

def manaCk(course_name) : # 檢查是否在院必修
    if course_name in mana :
        return course_name
    else :
        return False

def techCk(course_name) : # 檢查是否在院必修
    if course_name in tech :
        return course_name
    else :
        return False

def departCk(course_name) : # 檢查是否在院必修
    if course_name in depart :
        return course_name
    else :
        return False

def collegeCk(course_name) : # 檢查是否在院必修
    if course_name in college :
        return course_name
    else :
        return False

def tongsPass(tongs_cre_sep) : # 檢查通識學分、領域是否達標
    status = [0,0] # 兩種可能，學分不足、領域不足, 0 為足夠, 1 不足
    for key in tongs_cre_sep :
        if key == "spe" : # 特色通識只要 4 學分
            if tongs_cre_sep[key][0] < 4 : # 學分不足
                status[0] = 1
            if tongs_cre_sep[key][1] < 2 : # 領域不足
                status[1] = 1
        else :
            if tongs_cre_sep[key][0] < 5 : # 學分不足
                status[0] = 1
            if tongs_cre_sep[key][1] < 2 : # 領域不足
                status[1] = 1
    return status

def ckLength(tongs_dic) : # 檢查所有通識長度、通識各領域學分、通識次領域各領域數量
    tongs_length = 0
    human_length = 0
    social_length = 0
    science_length = 0
    spe_length = 0
    tongs_cre = {"human" : [0,0,1,1], "society" : [0,0,1,1], "science" : [0,0,1,1], "spe" : [0,0,1,1,1]} # [各個通識已修過幾學分,幾個領域,是否為算過的領域一開始先設0]
    for key in tongs_dic :
        tongs_length += len(tongs_dic[key])-1
        if key == "liber" or key == "history" : # 人文領域
            if len(tongs_dic[key]) > 1 : # 只有一個課和有零個課是一樣，都只佔一個，所以下一行要-1
                human_length += len(tongs_dic[key]) - 1 # 人文領域的課數數量
                for i in range(1,len(tongs_dic[key])) : # 有可能同個小領域修不只一堂
                    tongs_cre["human"][0] += float(list(tongs_dic[key][i].values())[0][:3])# 找出是幾學分
                # 找出修過幾個領域
                if key == "liber" and tongs_cre["human"][2] : # 領域符合且還沒算過
                    tongs_cre["human"][1] += 1 # 領域數+1
                    tongs_cre["human"][2] = 0 # 標記為算過的領域
                if key == "history" and tongs_cre["human"][3] :
                    tongs_cre["human"][1] += 1
                    tongs_cre["human"][3] = 0
        elif key == "law" or key == "social" :
            if len(tongs_dic[key]) > 1 :
                social_length += len(tongs_dic[key]) - 1
                for i in range(1,len(tongs_dic[key])) :
                    tongs_cre["society"][0] += float(list(tongs_dic[key][i].values())[0][:3])
                if key == "law" and tongs_cre["society"][2] :
                    tongs_cre["society"][1] += 1
                    tongs_cre["society"][2] = 0
                if key == "social" and tongs_cre["society"][3] :
                    tongs_cre["society"][1] += 1
                    tongs_cre["society"][3] = 0
        elif key == "engi" or key == "life" :
            if len(tongs_dic[key]) > 1 :
                science_length += len(tongs_dic[key]) - 1
                for i in range(1,len(tongs_dic[key])) :
                    tongs_cre["science"][0] += float(list(tongs_dic[key][i].values())[0][:3])
                if key == "engi" and tongs_cre["science"][2] :
                    tongs_cre["science"][1] += 1
                    tongs_cre["science"][2] = 0
                if key == "life" and tongs_cre["science"][3] :
                    tongs_cre["science"][1] += 1
                    tongs_cre["science"][3] = 0
        else :
            if len(tongs_dic[key]) > 1 :
                spe_length += len(tongs_dic[key]) - 1
                for i in range(1,len(tongs_dic[key])) :
                    tongs_cre["spe"][0] += float(list(tongs_dic[key][i].values())[0][:3])
                if key == "green" and tongs_cre["spe"][2] :
                    tongs_cre["spe"][1] += 1
                    tongs_cre["spe"][2] = 0
                if key == "east" and tongs_cre["spe"][3] :
                    tongs_cre["spe"][1] += 1
                    tongs_cre["spe"][3] = 0
                if key == "local" and tongs_cre["spe"][4] :
                    tongs_cre["spe"][1] += 1
                    tongs_cre["spe"][4] = 0
    return {"all" : tongs_length+10, "human_length" : human_length+2, "social_length" : social_length+2, "science_length" : science_length+2, "spe_length" : spe_length+3}, tongs_cre

def ckCourseName(course_info) : # 檢查課名是否有空白
    if len(course_info) == 6 : # 長度正常
        return course_info[4]
    course_name = ""
    for i in range(4,len(course_info)-1) :
        if i != len(course_info)-2 : # 不是最後一個課名，要加空格
            course_name += course_info[i] + " "
        else :
            course_name += course_info[i]
    return course_name


def tongsCk(course_name) : # 檢查是否在通識課
    if course_name in liter :
        return [course_name, "liber"]
    elif course_name in his :
        return [course_name, "history"]
    elif course_name in law :
        return [course_name, "law"]
    elif course_name in social :
        return [course_name, "social"]
    elif course_name in engi :
        return [course_name, "engi"]
    elif course_name in life :
        return [course_name, "life"]
    elif course_name in green :
        return [course_name, "green"]
    elif course_name in east :
        return [course_name, "east"]
    elif course_name in local :
        return [course_name, "local"]
    else :
        return False

def ckNecessary(same, lec_same_cre, stand) : # 檢查領域是否有必修還沒修
    if lec_same_cre < stand[0] : # 學分沒到
        return False
    # 檢查必修過了沒
    data_name = ['英文上','英文下','英文二','國文上','國文下','服務學習上','服務學習下','大一體育(上)','大一體育(下)'] # 全部必修課名
    same_nece = True
    same_name_only = [] # 只有上過的課名，把是不是必修拿掉
    for lec_name, necess in same :
        same_name_only.append(lec_name)
    for i in data_name : # 找所有的必修課
        if not i in same_name_only : # 有一個不在裡面
            same_nece = False
            break
    return same_nece

def mkSemeDic(total) : # [全部學期的字典，學年度為 key, 通識dic, 其他資訊]
    count_seme = 0 # 計算學期
    seme_dic = {} # 只有全部學期的字典，以學年度為key
    semi = {"total_cre" : 0} # 所有通識講座
    other_info = {"head" : 0} # 剩下的資訊
    for i in total :
        for j in i :
            if "修課狀況" in j :
                count_seme += 1 # 計算學期
            elif "通識講座" in j and j[-3] != "未": # 是通識講座且有通過
                semi[j[:(len(j)-2)]] = 0 # 不要最後的通過
                semi["total_cre"] += 1 # 總共幾場
            else :
                other_info[j] = 0
    for i in range(count_seme) : # 放入字典
        for j in range(len(total[i])) :
            if j == 0 :
                seme_dic[total[i][0]] = [] # 第一個為 key
            else :
                seme_dic[total[i][0]].append(total[i][j].split(" "))
    return seme_dic, semi, other_info

def isFloat(n) : # 是否為成績(小數點)
    try :
        float(n)
        return n
    except ValueError :
        return False

def mkSameList() : # 製作全校共同課程的二維陣列, [[課名, 是否為必修]]
    global total_same
    total_same = []
    for i in (same+sports) :
        if i[:3] == "體育:" :
            total_same.append([i,0])
        elif i == "英文一上" :
            total_same.append(["英文上", 1])
        elif i == "英文一下" :
            total_same.append(["英文下", 1])
        else :
            total_same.append([i,1])

def lecSame(lec_name) : # 全校共同課程
    if lec_name == "英文寫作一(上)" or lec_name == "英文寫作一(下)" :
        return False, False
    for i in range(len(total_same)) : # 檢查每個課程
        found = True # 是否有找到在 data，先設為 true
        for j in range(len(total_same[i][0])) :
            if not total_same[i][0][j] in lec_name : # 如果有沒有在裡面的字
                found = False
        if found and i <= 8:
            return lec_name, [total_same[i][0], 1]
        if found and i > 8 :
            return lec_name, [total_same[i][0], 0]
    return False, False

def Same(request) : # 全校共同課程
    path = "/var/www/django/credit/media/Excel"
    mkLec(path, str(request.session.get('year')))
    mkSameList() # 製作全校共同 list
    lec_same_name = request.session.get('lec_same_short_name') # 有上過的全校共同課程的全部資訊
    for i in lec_same_name :
        for j in range(len(total_same)) :
            if i[0] in total_same[j] : # 找到已經修過的課
                del total_same[j] # 刪掉
                break # 找到就停
    context = {"passed" : lec_same_name, "not_passed" : total_same}
    return render(request, "same.html", context)

def Tongs(request) : # 通識
    tongs_dic = request.session.get('tongs_name_only')
    liber_dic = {} # key 為課名, value 1 為有修, 0 沒修
    history_dic = {}
    law_dic = {}
    social_dic = {}
    engi_dic = {}
    life_dic = {}
    green_dic = {}
    east_dic = {}
    local_dic = {}
    for i in liter : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            liber_dic[i] = 0
        else :
            liber_dic[i] = 1
    for i in his :
        if not i in tongs_dic : # 沒有修過的課
            history_dic[i] = 0
        else :
            history_dic[i] = 1
    for i in law : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            law_dic[i] = 0
        else :
            law_dic[i] = 1
    for i in social : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            social_dic[i] = 0
        else :
            social_dic[i] = 1
    for i in engi : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            engi_dic[i] = 0
        else :
            engi_dic[i] = 1
    for i in life : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            life_dic[i] = 0
        else :
            life_dic[i] = 1
    for i in green : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            green_dic[i] = 0
        else :
            green_dic[i] = 1
    for i in east : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            east_dic[i] = 0
        else :
            east_dic[i] = 1
    for i in local : # 檢查所有通識課，有修過放1，沒修放0
        if not i in tongs_dic : # 沒有修過的課
            local_dic[i] = 0
        else :
            local_dic[i] = 1
    context = {"liber_dic" : liber_dic, "history_dic" : history_dic, "law_dic" : law_dic, "social_dic" : social_dic, "engi_dic" : engi_dic, "life_dic" : life_dic, "green_dic" : green_dic, "east_dic" : east_dic, "local_dic" : local_dic}
    return render(request, "tongs.html", context)

def College(request) : # 院必修
    stand = request.session.get('stand')
    college_name_cre = request.session.get('college_name_cre')
    college_name_only = [] # 只有院必修課名的 list
    for i in college_name_cre :
        college_name_only.append(i)
    college_dic = {} # 院必修課名 = key, 院必修是否過為 value
    for i in range(len(college)) :
        if college[i] in college_name_only : # 有修過
            college_dic[college[i]] = 1 # value = 1
        else : # 沒修過
            college_dic[college[i]] = 0
    context = {'stand' : stand, "college_dic" : college_dic}
    return render(request, "college.html", context)

def Department(request) : # 系必修
    stand = request.session.get('stand')
    depart_name_cre = request.session.get('depart_name_cre')
    depart_name_only = [] # 只有院必修課名的 list
    for i in depart_name_cre :
        depart_name_only.append(i)
    depart_dic = {} # 院必修課名 = key, 院必修是否過為 value
    for i in range(len(depart)) :
        if depart[i] in depart_name_only : # 有修過
            depart_dic[depart[i]] = 1 # value = 1
        else : # 沒修過
            depart_dic[depart[i]] = 0
    context = {"stand" : stand, "depart_dic" : depart_dic}
    return render(request, "department.html", context)

def Profession(request) : # 系專業選修
    stand = request.session.get('stand')
    tech_name_cre = request.session.get('tech_name_cre')
    mana_name_cre = request.session.get('mana_name_cre')
    profe_name_cre = request.session.get('profe_name_cre')
    tech_name_only = [] # 只有技術組課名的 list
    mana_name_only = [] # 只有管理組課名
    profe_name_only = [] # 只有其他領域課名
    for i in tech_name_cre :
        tech_name_only.append(i)
    for i in mana_name_cre :
        mana_name_only.append(i)
    for i in profe_name_cre :
        profe_name_only.append(i)
    tech_dic = {} # 技術組課名 = key, 院必修是否過為 value
    mana_dic = {}
    profe_dic = {}
    for i in range(len(tech)) :
        if tech[i] in tech_name_only : # 有修過
            tech_dic[tech[i]] = 1 # value = 1
        else : # 沒修過
            tech_dic[tech[i]] = 0
    for i in range(len(mana)) :
        if mana[i] in mana_name_only : # 有修過
            mana_dic[mana[i]] = 1 # value = 1
        else : # 沒修過
            mana_dic[mana[i]] = 0
    for i in range(len(pro)) :
        if pro[i] in profe_name_only : # 有修過
            profe_dic[pro[i]] = 1 # value = 1
        else : # 沒修過
            profe_dic[pro[i]] = 0
    context = {'num' : 14, 'total_pro' : stand[4]+stand[5], 'stand' : stand, "tech_dic" : tech_dic, "mana_dic" : mana_dic, "profe_dic" : profe_dic}
    return render(request, "profession.html", context)

def addData(request) :
    form = excelForm(request.POST, request.FILES)
    form_login = excelLogin(request.POST)
    if request.method == 'POST' :
        if form.is_valid() and form_login.is_valid():
            if request.POST['name'] == "root"  and request.POST['password'] == "012":
                form.save()
                return render(request, "addData.html", {"set" : True})
            else :
                context = {"fail" : True, "form" : form, "form_login" : form_login}
                return render(request, "addData.html", context)
    context = {"form" : form, "form_login" : form_login}
    return render(request, "addData.html", context)

def Free(request) : # 自由學分
    stand = request.session.get('stand')
    other_dic = request.session.get('other_dic')
    context = {"stand" : stand, "other_dic" : other_dic}
    return render(request, "free.html", context)

def mkLec(path, year) : # 製作不同領域課程 list
    excel_path = path + "/" + year + "_data.xlsx" # 抓第幾年
    if os.path.isfile(excel_path) : # 有該年資料
        data = openpyxl.load_workbook((path + "/" + year + "_data.xlsx")) # 抓第幾年
    else :
        return False
    same_num = 18 # 從 a18開始
    num = 1
    global same, sports, college, depart, tech, mana, pro, liter, his, law, social, engi, life, east, green, local
    same, sports, college, depart, tech, mana, pro, liter, his, law, social, engi, life, east, green, local = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []
    start_depart = False # 院必修、系必修在同排，院必修先算
    while True : # 共同必修
        same_index = "A" + str(same_num)
        if data.worksheets[0][same_index].value != "特色運動" : # 遇到特色運動就停
            same.append(data.worksheets[0][same_index].value)
        else :
            break
        same_num += 1
    sports_num = 18
    while True : # 共同必修-特色體育
        index = "F" + str(sports_num)
        if data.worksheets[0][index].value != None :
            sports.append("體育:"+data.worksheets[0][index].value)
        else :
            break
        sports_num += 1
    while True :  # 院必修+系必修
        num += 1 # 同一排，要檢查哪些是系必修所以 index 一開始加較好算
        index = "A" + str(num)
        if data.worksheets[1][index].value == None : # 空就停
            break
        if "系必修" in data.worksheets[1][index].value : # 開始算系必修
            start_depart = True
        if data.worksheets[1][index].value != None and not start_depart: # 院必修
            college.append(data.worksheets[1][index].value)
        if data.worksheets[1][index].value != None and start_depart: # 系必修
            depart.append(data.worksheets[1][index].value)
    num = 2
    while True : # 技術組
        index = "E" + str(num)
        if data.worksheets[1][index].value != None :
            tech.append(data.worksheets[1][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 管理組
        index = "I" + str(num)
        if data.worksheets[1][index].value != None :
            mana.append(data.worksheets[1][index].value)
        else :
            break
        num += 1
    num = 2
    index_letter = ['A','E','I','M','Q','U'] # 系專選在 a+3 排
    for i in index_letter : # 系專選有多排
        num = 2
        while True : # 系專選
            index = i + str(num)
            if data.worksheets[2][index].value != None :
                pro.append(data.worksheets[2][index].value)
            else :
                break
            num += 1
    num = 2
    while True : # 文學
        index = "A" + str(num)
        if data.worksheets[3][index].value != None :
            liter.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 歷史
        index = "E" + str(num)
        if data.worksheets[3][index].value != None :
            his.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 法政
        index = "I" + str(num)
        if data.worksheets[3][index].value != None :
            law.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 社經
        index = "M" + str(num)
        if data.worksheets[3][index].value != None :
            social.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 工程
        index = "A" + str(num)
        if data.worksheets[4][index].value != None :
            engi.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 生活科技
        index = "E" + str(num)
        if data.worksheets[4][index].value != None :
            life.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    green_start = False
    while True : # 東南亞、綠概念 同一排
        index = "I" + str(num)
        if data.worksheets[4][index].value == None:
            break
        elif "特色通識領域" in data.worksheets[4][index].value and "綠概念" in data.worksheets[4][index].value : # 東南亞結束換綠概念
            green_start = True
            num += 1
            continue
        elif not green_start : # 東南亞
            east.append(data.worksheets[4][index].value)
        else : # 綠概念
            green.append(data.worksheets[4][index].value)
        num += 1
    num = 2
    while True : # 在地
        index = "M" + str(num)
        if data.worksheets[4][index].value != None :
            local.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    return True

'''def redundSame(lec_same) : # 多餘的共同必修(超過兩堂的體育)
    count_sport = 0 # 修過的特色體育
    for key in list(lec_same) : # 用 list 包起來可以解決在 del dictionary 在迴圈中會報的錯
        if key[:3] == "體育:" : # 特色體育
            count_sport += 1
        if key[:3] == "體育:" and count_sport > 2 : # 多餘的特色體育
            other_dic[key] = lec_same[key] # 放進自由學分
            del lec_same[key]

def redundTongs(tongs_dic) : # 把多餘通識放進自由學分
    human_cre = [] # 人文總學分
    fifth_total = [[3.0,2.0], [2.0,1.0,2.0], [3.0,1.0,1.0], [1.0,1.0,1.0,1.0,1.0]] # 5 學分的所有可能
    if len(tongs_dic['liber']) > 1 and len(tongs_dic['history']) > 1 : # 領域有到
        for i in range(1,len(tongs_dic['liber'])) :
            human_cre.append(float(str(tongs_dic['liber'][i].values())[14:17]))
        for i in range(1,len(tongs_dic['history'])) :
            human_cre.append(float(str(tongs_dic['history'][i].values())[14:17]))
        if sum(human_cre) >= 5 : # 學分有到
            human_cre1 = copy.deepcopy(human_cre) # 每此要重用一個新的
            for fifth in fifth_total : # 找尋所有可能為 5
                all_in = True # 先設有
                for num in fifth :
                    if not num in human_cre1 : # 不符合 5 分的數字
                        all_in = False
                        break
                    else : # 符合
                        del human_cre1[human_cre1.index(num)]
                if all_in : #　有一組數字都符合
                    human_cre = fifth
                    break
    if human_cre : # 有剛好 5 學分
        human_cre_sep = [[0,0] for i in range(len(human_cre))]
        for j in range(len(human_cre_sep)) : # 把多餘的課刪掉
            for i in range(1,len(tongs_dic['liber'])) :
                if float(str(list(tongs_dic['liber'][i].values()))[2:5]) == human_cre[j] :
                    human_cre_sep[j][0] += 1
            for i in range(1,len(tongs_dic['history'])) :
                if float(str(list(tongs_dic['history'][i].values()))[2:5]) == human_cre[j] :
                    human_cre_sep[j][1] += 1
        human_remove = []
        domain = 0
        human_cre_sep, human_cre = mkSort(human_cre_sep, human_cre)
        for j in range(len(human_cre_sep)) :
            used = False
            if human_cre_sep[j][0] == 1 and human_cre_sep[j][1] == 1: # 該學分在哪個領域
                if domain <= 0 :
                    for i in range(1,len(tongs_dic['liber'])) :
                        if float(str(list(tongs_dic['liber'][i].values()))[2:5]) == human_cre[j] and not used : # 不是多餘的且還沒放過
                            used = True
                        else :
                            human_remove.append(list(tongs_dic['liber'][i].keys())[0])
                            other_dic[list(tongs_dic['liber'][i].keys())[0]] = list(tongs_dic['liber'][i].values())[0][:3]
                else :
                    for i in range(1,len(tongs_dic['history'])) :
                        if float(str(list(tongs_dic['history'][i].values()))[2:5]) == human_cre[j] and not used : # 不是多餘的且還沒放過
                            used = True
                        else :
                            human_remove.append(list(tongs_dic['history'][i].keys())[0])
                            other_dic[list(tongs_dic['history'][i].keys())[0]] = list(tongs_dic['history'][i].values())[0][:3]
            elif human_cre_sep[j][0] == 1 and human_cre_sep[j][1] == 0: # 該學分在哪個領域
                domain += 1
                for i in range(1,len(tongs_dic['liber'])) :
                    if float(str(list(tongs_dic['liber'][i].values()))[2:5]) == human_cre[j] and not used : # 不是多餘的且還沒放過
                        used = True
                    else :
                        human_remove.append(list(tongs_dic['liber'][i].keys())[0])
                        other_dic[list(tongs_dic['liber'][i].keys())[0]] = list(tongs_dic['liber'][i].values())[0][:3]
            else :
                domain -= 1
                for i in range(1,len(tongs_dic['history'])) :
                    if float(str(list(tongs_dic['history'][i].values()))[2:5]) == human_cre[j] and not used : # 不是多餘的且還沒放過
                        used = True
                    else :
                        human_remove.append(list(tongs_dic['history'][i].keys())[0])
                        other_dic[list(tongs_dic['history'][i].keys())[0]] = list(tongs_dic['liber'][i].values())[0][:3]
        for i in human_remove :
            for j in range(1,len(tongs_dic['liber'])) :
                if i in tongs_dic['liber'][j] :
                    del tongs_dic['liber'][j]
                    break
            for j in range(1,len(tongs_dic['history'])) :
                if i in tongs_dic['history'][j] :
                    del tongs_dic['history'][j]
                    break
    return human_remove

def mkSort(human_cre_sep, human_cre) : # 回傳 sorted human_cre_sep, 依照 human_cre_sep 順序的 human_cre
    for i in range(len(human_cre_sep)) :
        for j in range(len(human_cre_sep)) :
            if j != len(human_cre_sep)-1 :
                if sum(human_cre_sep[j]) > sum(human_cre_sep[j+1]) :
                    tem = human_cre_sep[j]
                    human_cre_sep[j] = human_cre_sep[j+1]
                    human_cre_sep[j+1] = tem
                    tem = human_cre[j]
                    human_cre[j] = human_cre[j+1]
                    human_cre[j+1] = tem
    return human_cre_sep, human_cre'''
