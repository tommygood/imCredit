import os, copy, subprocess, time
from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
from .form import CreditForm, excelForm, excelLogin, userForm, waterForm
import datetime
from datetime import date, timedelta
from random import randint
import openpyxl
from collections import OrderedDict
from jinja2 import Environment, FileSystemLoader
from .models import userLec
from pathlib import Path
#from pyecharts.globals import CurrentConfig
#CurrentConfig.GLOBAL_ENV = Environment(loader=FileSystemLoader("/var/www/django/credit/templates"))
BASE_DIR = Path(__file__).resolve().parent.parent

# login info
import json
login_info = json.loads(open(str(BASE_DIR) + "/config.json", "r").read())
account = login_info["account"]
password = login_info["password"]

def Credit(request) : # 選擇學年及領域頁面
    form = CreditForm(request.POST)
    form_lec = userForm(request.POST)
    if "send" in request.POST :
        if form.is_valid() and form_lec.is_valid() :
            #form_lec.save()
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
            elif request.POST['year'] == "109" : # 109 學年
                stand = [12.0, 19.0, 0, 73.0, 28.0, 0, 0.0]
                request.session['stand'] = stand
                if request.POST['domain']== "1" : # 技術
                    return creMain(request, 1, request.POST['year'], stand)
                if request.POST['domain']== "2" : # 管理
                    return creMain(request, 2, request.POST['year'], stand)
    context = {"form" : form, "form_lec" : form_lec}
    return render(request, "credit.html", context)

def mkConflictCourses() :
    # 針對 技術次領域, 管理次領域, 系專業選修 檢查課名相同的課

    #tech, mana, pro
    global conflict_courses
    conflict_courses = {} # 所有有重複課名的課
    index = 0
    for course in tech :
        conflict_courses[course] = [["tech", tech_snum[index]]]
        index += 1
    index = 0
    for course in mana :
        if course in conflict_courses :
            conflict_courses[course].append(["mana", mana_snum[index]])
        else :
            conflict_courses[course] = [["mana", mana_snum[index]]]
        index += 1
    index = 0
    for course in pro :
        if course in conflict_courses : 
            conflict_courses[course].append(["pro", pro_snum[index]])
        else :
            conflict_courses[course] = [["pro", pro_snum[index]]]
        index += 1
    
    all_keys = []
    for key in conflict_courses :
        all_keys.append(key) # tech_snum, mana_snum, pro_snum
    for key in all_keys :
        if len(conflict_courses[key]) <= 1 : # 只有一堂相同課
            del conflict_courses[key] # 刪除該課
    return conflict_courses

def ckConflictCourse(course_name, course_snum, domain) :
    # 檢查課程是否有相同課名, 且是否真正修的課號的領域和 domain 相同

    for courses in conflict_courses :
        if courses != course_name : # 不同課名, 不相同 
            continue
        # 相同課名, 檢查課號和領域是否相同
        for course in conflict_courses[courses] :
            c_domain = course[0]
            c_snum = str(course[1])
            if c_snum == course_snum : # 相同課號且同課名, 代表是對應的課
                if c_domain == domain : # 同個領域
                    return course_name
        return False
    return "keep" # 此課程沒有相同課名的課

def creMain(request, domain, year, stand) : # 主頁面
    path = str(BASE_DIR) + "/media/Excel"
    if not mkLec(path, year) : # 沒資料
        return render(request, "creMain.html", {"no_data" : True})
    mkSameList() # 製作全校共同課程的二維陣列
    mkConflictCourses() # 針對課名相同的課處理
    #print(conflict_courses)
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
    userLec.objects.create(student_name=name, all_data=a)
    total[0].pop(0) # 不要前兩行
    total[0].pop(0) # 原本的 index1 變 index0
    seme_dic, semi_dic, other_info = mkSemeDic(request, total) # 只有全部學期的字典，以學年度為 key
    total_credit = findTotalCredit(total[len(total)-1]) # 從校務系統的資料找總學分
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
        if "已抵免之學分" in i : 
            for j in range(len(seme_dic[i])) :
                if "內抵" in seme_dic[i][j] : # 因為內抵本來就有在學期中的紀錄裡了
                    continue
                course_snum = seme_dic[i][j][0]
                course_name = seme_dic[i][j][3]
                same, short_name = lecSame(course_name)  # 是否在全校共同
                if (same or ckOverseas(course_name)) and (short_name not in lec_same_short_name) : # 如果有過的全校共同
                    lec_same['lec_same_cre'] += float(seme_dic[i][j][2][:3]) # 算總全校共同學分
                    lec_same[same+'-抵免'] = seme_dic[i][j][2][:3] # 加入課名為 key ，學分為 value 的 dici
                    lec_same_short_name.append(short_name) # 通用的課名
                    continue # 找下一個課名
                tongs_name = tongsCk(course_name) # 是否在通識，回傳[課名,領域]
                if tongs_name : # 有過的通識
                    tongs_name_only.append(tongs_name[0])
                    tongs_dic[tongs_name[1]].append({tongs_name[0]: seme_dic[i][j][2]+'-抵免'})
                    tongs_cre[tongs_name[1]].append(seme_dic[i][j][2][:3])
                    continue # 找下一個課名
                college_name = collegeCk(course_name) # 是否在院必修
                if college_name : # 是院必修
                    college_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                    college_name_cre[college_name+'-抵免'] = seme_dic[i][j][2][:3] # key = 課名, value = 學分          
                    continue
                depart_name = departCk(course_name) # 是否在系必修
                if depart_name : # 是院必修
                    depart_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                    depart_name_cre[depart_name+'-抵免'] = seme_dic[i][j][2][:3] # key = 課名, value = 學分
                    continue
                tech_name = techCk(course_name, course_snum, i) # 是否在技術領域
                mana_name = manaCk(course_name, course_snum, i) # 是否在管理領域
                if tech_name and mana_name : # 是技術和管理領域的課
                    if domain == 1 :
                        tech_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                        tech_name_cre[tech_name+'-抵免'] = seme_dic[i][j][2][:3] # key = 課名, value = 學分
                    else :
                        mana_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                        mana_name_cre[mana_name+'-抵免'] = seme_dic[i][j][2][:3]  # key = 課名, value = 學分
                    continue
                if tech_name : # 是技術領域
                    tech_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                    tech_name_cre[tech_name+'-抵免'] = seme_dic[i][j][2][:3] # key = 課名, value = 學分
                    continue
                if mana_name : # 是管理領域
                    mana_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                    mana_name_cre[mana_name+'-抵免'] = seme_dic[i][j][2][:3] # key = 課名, value = 學分
                    continue
                profe_name = profeCk(course_name, course_snum) # 是否在無領域系專選
                if profe_name :
                    profe_name_cre["total_cre"] += float(seme_dic[i][j][2][:3])
                    profe_name_cre[profe_name+'-抵免'] = seme_dic[i][j][2][:3]  # key = 課名, value = 學分
                    continue
                other_dic['total_cre'] += float(seme_dic[i][j][2][:3])
                other_dic[course_name+'-抵免'] = seme_dic[i][j][2][:3] # 其他課程，可當自由學分
        else :
            for j in range(len(seme_dic[i])-1) : # 最後一個是共修多少學分，不要算
                if not isFloat(seme_dic[i][j][3]) : # 成績未送達
                    continue # 找下個 value，因為有可能相同學期有些先送達
                if float(seme_dic[i][j][3]) < 60.0 : # 有及格
                    continue # 沒及格找下一個
                course_snum = seme_dic[i][j][0]
                course_name = ckCourseName(seme_dic[i][j]) # 檢查課程名稱，有可能是中間有空白
                same, short_name = lecSame(course_name)  # 是否在全校共同
                if (same or ckOverseas(course_name)) and (short_name not in lec_same_short_name) : # 如果有過的全校共同
                    lec_same['lec_same_cre'] += float(seme_dic[i][j][1][:3]) # 算總全校共同學分
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
                tech_name = techCk(course_name, course_snum, i) # 是否在技術領域
                mana_name = manaCk(course_name, course_snum, i) # 是否在管理領域
                if tech_name and mana_name : # 是技術領域
                    if domain == 1 :
                        tech_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                        tech_name_cre[tech_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                    else :
                        mana_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                        mana_name_cre[mana_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                    continue
                if tech_name : # 是技術領域
                    tech_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                    tech_name_cre[tech_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                    continue
                if mana_name : # 是管理領域
                    mana_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                    mana_name_cre[mana_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                    continue
                profe_name = profeCk(course_name, course_snum) # 是否在無領域系專選
                if profe_name : 
                    profe_name_cre["total_cre"] += float(seme_dic[i][j][1][:3])
                    profe_name_cre[profe_name] = seme_dic[i][j][1][:3] # key = 課名, value = 學分
                    continue
                other_dic['total_cre'] += float(seme_dic[i][j][1][:3])
                other_dic[course_name] = seme_dic[i][j][1][:3] # 其他課程，可當自由學分
    #redundSame(lec_same) # 把多餘的特色體育放進自由學分
    #human_cre = redundTongs(tongs_dic) # 把多餘的通識放進自由學分
    lec_same_cre = lec_same['lec_same_cre']
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
    tongs_len, tongs_cre_sep = ckLength(tongs_dic) # 通識的長度(課數)、通識的學分、領域數
    #free_dic = ckFree(lec_same, tongs_dic, tech_name_cre, mana_name_cre, profe_name_cre) # 可以當做自由學分的課程
    fin_cre = float(lec_same['lec_same_cre'])+float(tongs_cre_sep['human'][0])+float(tongs_cre_sep['society'][0])+float(tongs_cre_sep['science'][0])+float(tongs_cre_sep['spe'][0])+float(college_name_cre['total_cre'])+float(depart_name_cre['total_cre'])+float(tech_name_cre['total_cre'])+float(mana_name_cre['total_cre'])+float(profe_name_cre['total_cre'])+float(other_dic['total_cre'])
    # 是否是資管系辦登入
    if request.session.get('root') == 'im' :
        pic_path = '/media/image/im_water.png'
    else :
        pic_path = ''
    context = {"pic_path" : pic_path, "fin_cre" : total_credit, "total_pro_cre" : tech_name_cre['total_cre']+mana_name_cre['total_cre']+profe_name_cre['total_cre'], "sum_stand_pro" : stand[4]+stand[5], "total_stand" : sum(stand), "stand" : stand, "date" : datetime.date.today(), "other_cre1" : other_cre1, "other_len1" : other_len1, "depart_107" : east, "college_107" : local, "other_info" : other_info, "semi_dic" : semi_dic, "total" : total, "other_dic" : other_dic, "total_profe_len" : total_profe_len, "other_len" : other_len, "other_cre" : other_cre, "profe_name_cre" : profe_name_cre, "mana_name_cre" : mana_name_cre, "tech_name_cre" : tech_name_cre, "depart_name_cre" : depart_name_cre, "college_name_cre" : college_name_cre, "tongs_pass" : tongsPass(tongs_cre_sep), "tongs_cre_sep" : tongs_cre_sep, "tongs_len" : tongs_len, "name" : name, "domain" : domain, "seme_dic" : seme_dic, "year" : request.POST["year"], "lec_same" : lec_same, "same_nece" : same_nece, "tongs_dic" : tongs_dic, "tongs_cre" : tongs_cre}
    return render(request, "creMain.html", context)

def profeCk(course_name, course_snum) : # 檢查是否在院必修
    conflict_result = ckConflictCourse(course_name, course_snum, "pro")
    if conflict_result == True : # 是此領域的重複課名的課程
        return course_name
    elif conflict_result == False : # 不是此領域, 但是重複課名的課程
        return False
    if course_name in pro :
        return course_name
    else :
        return False

def manaCk(course_name, course_snum, stu_year) : # 檢查是否在院必修

    conflict_result = ckConflictCourse(course_name, course_snum, "mana")
    if conflict_result == True : # 是此領域的重複課名的課程
        return course_name
    elif conflict_result == False : # 不是此領域, 但是重複課名的課程
        return False
    if course_name in mana :
        return course_name
    else :
        return False

def techCk(course_name, course_snum, stu_year) : # 檢查是否在院必修
    # 特例
    if course_name == "人因與人機介面" and "112學年" in stu_year and "第2學期" in stu_year :
        return False

    conflict_result = ckConflictCourse(course_name, course_snum, "tech")
    if conflict_result == True : # 是此領域的重複課名的課程
        return course_name
    elif conflict_result == False : # 不是此領域, 但是重複課名的課程
        return False
    for each_tech in tech :
        if '$~$' in each_tech : # 相同課有多個課名
            each_tech = each_tech.split('$~$')
            for different_course_name in each_tech :
                if different_course_name == course_name :
                    return course_name
        else :
            if each_tech == course_name :
                return course_name
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
    data_name = ['英文上','英文下','英文二','國文上','國文下','土木系服務學習(上)','土木系服務學習(下)','大一體育(上)','大一體育(下)'] # 全部必修課名
    same_nece = True
    same_name_only = [] # 只有上過的課名，把是不是必修拿掉
    for lec_name, necess in same :
        same_name_only.append(lec_name)

    # 檢查特色體育有沒有修超過兩堂
    special_num = 0
    for course in same_name_only :
        if "體育:" in course :
            special_num += 1
    if special_num < 2 :
        print("特色體育未達標, 只修 ", special_num, " 堂")
        return False

    for i in data_name : # 找所有的必修課
        if not i in same_name_only : # 有一
            same_nece = False
            print("必修 ", i, " 還沒修")
            #return [i, same_name_only]
            break
    return same_nece

def mkSemeDic(request, total) : # [全部學期的字典，學年度為 key, 通識dic, 其他資訊]
    count_seme = 0 # 計算學期
    seme_dic = {} # 只有全部學期的字典，以學年度為key
    semi = {"total_cre" : 0} # 所有通識講座
    other_info = {"head" : 0} # 剩下的資訊
    for i in total :
        for j in i :
            if '休學' in j : # 有休學，多加一學期。因為休學紀錄會多被 split 一個 list
                count_seme += 1
                break
            if "修課狀況" in j or "已抵免之學分" in j :
                count_seme += 1 # 計算學期
            elif "通識講座" in j and j[-3] != "未": # 是通識講座且有通過
                semi[j[:(len(j)-2)]] = 0 # 不要最後的通過
                semi["total_cre"] += 1 # 總共幾場
            else :
                other_info[j] = 0
    for i in range(count_seme) : # 放入字典
        out = False
        in_cre = False
        for j in range(len(total[i])) :
            if total[i][j] == "外抵" or "外抵" in total[i][j] :
                out = True
            if "內抵" in total[i][j] or '免修' in total[i][j] :
                out = True
                in_cre = True
            if j == 0 :
                seme_dic[total[i][0]] = [] # 第一個為 key
            else :
                # 處理特例課名
                if "Python 程式設計" in total[i][j] :
                    total[i][j] = total[i][j].replace("Python 程式設計", "Python程式設計") 
                if out : # 外抵或內抵
                    #seme_dic[total[i][0]].append(total[i][j].split("  "))
                    seme_dic[total[i][0]].append(mkSplit(total[i][j]))
                else :
                    seme_dic[total[i][0]].append(total[i][j].split(" "))
    if in_cre : # 幫全部的內抵學分換成抵用後的名字
        for k in range(len(seme_dic['已抵免之學分如下:'])) :
            for i in seme_dic :
                for j in range(len(seme_dic[i])) :
                    if (seme_dic['已抵免之學分如下:'][k][-1][:-5] in seme_dic[i][j] or seme_dic['已抵免之學分如下:'][k][-1][:-3] in seme_dic[i][j]) and '內抵' not in seme_dic[i][j] : # 是內抵的學分，且只要抓學期中的紀錄就好
                        print(seme_dic[i][j][4], "換成", seme_dic['已抵免之學分如下:'][k][2])
                        seme_dic[i][j][4] = seme_dic['已抵免之學分如下:'][k][2] # 換名字
    return seme_dic, semi, other_info

def mkSplit(obj) : # 遇到字才加到 list
    n_obj = []
    each = ''
    space = False
    for i in range(len(obj)) :
        if obj[i] != ' ' : # 自己不是空白
            if i == len(obj)-1 : # 全部的最後一個
                if obj[i] == '）' : # 轉換格式
                    each += ')'
                elif obj[i] == '（' :
                    each += '('
                else :
                    each += obj[i]
                n_obj.append(each)
                break
            if space == True : # 前一個是空白, 加進 list
                n_obj.append(each)
                each = ''
                if obj[i] == '）' :
                    each += ')'
                elif obj[i] == '（' :
                    each += '('
                else :
                    each += obj[i]
                space = False
            else : #　前一個不是空白, 還不用加進 list, 繼續找下一個
                if obj[i] == '）' :
                    each += ')'
                elif obj[i] == '（' :
                    each += '('
                else :
                    each += obj[i]
        else : # 空白就不要
            space = True
    return n_obj


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
    if lec_name == "英文寫作一(上)" or lec_name == "英文寫作一(下)" or '進修英文' in lec_name :
        return False, False
    is_over = False
    if "僑外生華語文(上)" in lec_name or ("中文思辨與表達一" in lec_name and "科技學院" in lec_name) :
        is_over = True
        over_lec_name = lec_name
        lec_name = "國文上"
    if "僑外生華語文(下)" in lec_name or ("中文思辨與表達二" in lec_name and "科技學院" in lec_name) :
        is_over = True
        is_over = True
        over_lec_name = lec_name
        lec_name = "國文下"
    for i in range(len(total_same)) : # 檢查每個課程
        found = True # 是否有找到在 data，先設為 true
        for j in range(len(total_same[i][0])) :
            if not total_same[i][0][j] in lec_name : # 如果有沒有在裡面的字
                found = False
        if found and i <= 8:
            if is_over :
                return over_lec_name, [total_same[i][0], 1]
            else :
                return lec_name, [total_same[i][0], 1]
        if found and i > 8 :
            if is_over :
                return over_lec_name, [total_same[i][0], 0]
            else :
                return lec_name, [total_same[i][0], 0]
    return False, False

def Same(request) : # 全校共同課程
    path = str(BASE_DIR) + "/media/Excel"
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
        if '$~$' in tech[i] : # 同堂課有多個課名
            tech_name = tech[i].split('$~$')
        else : # 普通的，只有一種課名
            tech_name = [tech[i]]
        is_pass_one = False # 是否有通過其中一個課名
        for each_tech in tech_name :
            if each_tech in tech_name_only : # 有修過其中一堂課名
                tech_dic[each_tech] = [1,tech_snum[i]]
                is_pass_one = True
                break
        if not is_pass_one : # 一種課名都沒通過，代表沒過此堂課
            tech_dic[each_tech] = [0, tech_snum[i]]
    for i in range(len(mana)) :
        if mana[i] in mana_name_only : # 有修過
            mana_dic[mana[i]] = [1, mana_snum[i]] # value = 1
        else : # 沒修過
            mana_dic[mana[i]] = [0, mana_snum[i]]
    for i in range(len(pro)) :
        if pro[i] in profe_name_only : # 有修過
            profe_dic[pro[i]] = [1, pro_snum[i]] # value = 1
        else : # 沒修過
            profe_dic[pro[i]] = [0, pro_snum[i]]
    context = {'num' : 14, 'total_pro' : stand[4]+stand[5], 'stand' : stand, "tech_dic" : tech_dic, "mana_dic" : mana_dic, "profe_dic" : profe_dic}
    return render(request, "profession.html", context)

def addData(request) :
    try : # 是否是系辦登入
        if request.session['root'] == 'im' :
            is_root = True # 有登入過
    except :
        is_root = False # 沒有登入過
    if not is_root :
        context = {'not_root' : True}
        return render(request, "addData.html", context)
    form = excelForm(request.POST, request.FILES)
    #form_login = excelLogin(request.POST)
    if request.method == 'POST' :
        #if form.is_valid() and form_login.is_valid():
            #if request.POST['name'] == "imadmin"  and request.POST['password'] == "im_grade439":
        if form.is_valid() :
            try : # 先去刪看看是否已有此學年的檔案
                stu_year = request.POST['stu_year']
                subprocess.Popen(f'rm {str(BASE_DIR)}/media/Excel/{stu_year}_data.xlsx', stdout=subprocess.PIPE, shell=True)
            except :
                print('remove excel data error')
            # 先等一下再加入新的 excel 檔，否則會被判定還有原本的 excel 檔
            time.sleep(1)
            form.save()
            return render(request, "addData.html", {"set" : True})
            #else :
            #    context = {"fail" : True, "form" : form, "form_login" : form_login}
            #    return render(request, "addData.html", context)
    context = {"form" : form}
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
    global tech_snum, mana_snum, pro_snum
    tech_snum, mana_snum, pro_snum = [], [], []
    start_depart = False # 院必修、系必修在同排，院必修先算
    while True : # 共同必修
        same_index = "B" + str(same_num)
        if data.worksheets[0][same_index].value != "特色運動" : # 遇到特色運動就停
            same.append(data.worksheets[0][same_index].value)
        else :
            break
        same_num += 1
    sports_num = 18
    while True : # 共同必修-特色體育
        index = "H" + str(sports_num)
        if data.worksheets[0][index].value != None :
            sports.append("體育:"+data.worksheets[0][index].value)
        else :
            break
        sports_num += 1
    while True :  # 院必修+系必修
        num += 1 # 同一排，要檢查哪些是系必修所以 index 一開始加較好算
        index = "B" + str(num)
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
        index = "G" + str(num)
        if data.worksheets[1][index].value != None :
            tech.append(data.worksheets[1][index].value)
            tech_snum.append(data.worksheets[1]["F" + str(num)].value)
        else :
            break
        num += 1
    num = 2
    while True : # 管理組
        index = "L" + str(num)
        if data.worksheets[1][index].value != None :
            mana.append(data.worksheets[1][index].value)
            mana_snum.append(data.worksheets[1]["K" + str(num)].value)
        else :
            break
        num += 1
    num = 2
    index_letter = ['B','G','L','Q','U','V'] # 系專選在 a+3 排
    for i in index_letter : # 系專選有多排
        num = 2
        while True : # 系專選
            index = i + str(num)
            if data.worksheets[2][index].value != None :
                pro.append(data.worksheets[2][index].value)
                pro_snum.append(data.worksheets[2][chr(ord(i)-1) + str(num)].value)
            else :
                break
            num += 1
    num = 2
    while True : # 文學
        index = "B" + str(num)
        if data.worksheets[3][index].value != None :
            liter.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 歷史
        index = "G" + str(num)
        if data.worksheets[3][index].value != None :
            his.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 法政
        index = "L" + str(num)
        if data.worksheets[3][index].value != None :
            law.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 社經
        index = "Q" + str(num)
        if data.worksheets[3][index].value != None :
            social.append(data.worksheets[3][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 工程
        index = "B" + str(num)
        if data.worksheets[4][index].value != None :
            engi.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    while True : # 生活科技
        index = "G" + str(num)
        if data.worksheets[4][index].value != None :
            life.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    green_start = False
    while True : # 東南亞、綠概念 同一排
        index = "L" + str(num)
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
        index = "Q" + str(num)
        if data.worksheets[4][index].value != None :
            local.append(data.worksheets[4][index].value)
        else :
            break
        num += 1
    num = 2
    return True

def ckOverseas(course_name) : # 僑生華語文可以抵國文
    if "僑外生華語文(上)" in course_name or ("中文思辨與表達一" in course_name and "科技學院" in course_name) :
        return True
    elif "僑外生華語文(下)" in course_name or ("中文思辨與表達二" in course_name and "科技學院" in course_name) :
        return True
    else :
        return False
def rest(request) :
    return render(request, 'rest.html')

def findTotalCredit(total) : # 找總學分
    total_credit = 'bug'
    for each in total :
        if '總共' in each :
            total_credit = extractFloat(each)
    return total_credit

def extractFloat(obj) : # 把小數點拿出來
    only_float = ''
    for i in obj :
        if i.isnumeric() or i == '.' :
            only_float += i
    return only_float

# 系辦登入
def rootExclusive(request) : # 選擇學年及領域頁面
    form_login = excelLogin(request.POST)
    try : # 是否是系辦登入
        if request.session['root'] == 'im' :
            is_root = True # 有登入過
    except :
        is_root = False # 沒有登入過
    if request.method == 'POST' :
        if form_login.is_valid():
            if request.POST['name'] == account and request.POST['password'] == password :
                request.session['root'] = 'im'
                is_root = True # 登入成功
                return render(request, "rootLogin.html", {"set" : True, "is_root" : is_root})
            else :
                context = {"fail" : True, "form_login" : form_login}
                return render(request, "rootLogin.html", context)
    context = {"form_login" : form_login, 'is_root' : is_root}
    return render(request, "rootLogin.html", context)

# 換浮水印
def postWater(request) :
    try :
        if request.session['root'] == 'im' :
            is_root = True # 是有登入過的
    except :
        is_root = False # 不是有登入過的
    if not is_root : # 沒有登入
        context = {"not_root" : True}
        return render(request, "postWater.html", context)
    form = waterForm(request.POST, request.FILES)
    if request.method == 'POST' :
        if form.is_valid():
            try :
                subprocess.Popen(f'rm {str(BASE_DIR)}/media/image/im_water.png', stdout=subprocess.PIPE, shell=True)
                time.sleep(1)
            except :
                print('remove water image error')
            form.save()
            return render(request, "postWater.html", {"set" : True})
    context = {"form" : form}
    return render(request, "postWater.html", context)

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
    return human_cre_sep, human_cre '''
