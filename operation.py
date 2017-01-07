#!/usr/bin/env python
# coding: utf-8

import sqlite3
import json
import logger
import os
import time
import pdb
import traceback
from wxbot import *
import datetime
import codecs
class mysqlite(object):
    """自定义sql操作类"""
    def __init__(self,name,path,logger):
        self.name = name
        self.path = path
        self.logger = logger
        self.db = os.path.join(self.path,self.name)
        try:
            self.conn = sqlite3.connect(self.db)
        except sqlite3.Error as e:
            self.logger.error(u"连接sqlite3数据库失败：%s" % e.args[0])
            return False
        self.cursor = self.conn.cursor()

    def dropTbl(self):
        '''
        删除表
        '''
        sql_del="DROP TABLE IF EXISTS USER_TABLE;"  
        try:  
            self.cursor.execute(sql_del)  
        except sqlite3.Error as e:  
            self.logger.error(u"删除表失败：%s" % e.args[0])
            return  False
        self.conn.commit()

    def createTbl(self,sql_add):
        '''
        创建表，参数为创建语句
        '''
        try:
            self.cursor.execute(sql_add)
        except sqlite3.Error as e:
            self.logger.error(u"创建表失败：%s" % e.args[0])
            return False
        self.logger.info(u"创建表成功：%s" % sql_add)
        self.conn.commit()

    def searchTbl(self,selectObj='*',tableName='USER_TABLE',condition = ''):
        '''
        查询表
        selectobj：查询对象
        tablename：查询表名
        condition：查询条件
        '''
        try:
            sql_select = 'SELECT %s FROM %s %s ;' % (selectObj,tableName,condition)
            self.logger.debug(sql_select)
            self.cursor.execute(sql_select)
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(u"查询表失败：%s" % unicode(e))
            self.logger.error(unicode(traceback.print_exc()))
            self.logger.error(u'%s \t %s \t %s' %(selectObj,tableName,condition))


    def updateData(self,sql,data):
        '''
        更新表数据，参数为语句和数据
        '''
        try:
            self.cursor.execute(sql,data)
        except sqlite3.Error as e:
            self.logger.error(u"更新数据失败：%s" % e.args[0])
            return False
        self.logger.debug(u"更新数据成功：%s,%s" % (sql,data))
        self.conn.commit()

    def insertData(self,sql,data):
        '''
        新增表数据，参数为语句和数据
        '''
        try:
            self.cursor.execute(sql,data)
        except sqlite3.Error as e:
            self.logger.error(u"添加数据失败：%s" % e.args[0])
            self.logger.error(unicode(traceback.print_exc()))
            self.logger.error(unicode(data)+unicode(sql))
            return False
        except Exception as e:
            self.logger.error(u"添加数据失败：%s" % unicode(e))
        self.logger.debug(u"添加数据成功：%s,%s" % (sql,data))
        self.conn.commit()

    def deleteData(self,sql):
        '''
        删除表数据，参数为语句
        '''
        try:
            self.cursor.execute(sql)
        except sqlite3.Error as e:
            self.logger.error(u"删除数据失败：%s" % e.args[0])
            return False
        self.logger.debug(u"删除数据成功：%s" % sql)
        self.conn.commit()

    def createUserTbl(self):        
        '''
        创建用户表
        '''
        sql_add = '''CREATE TABLE USER_TABLE(
                            ID INTEGER PRIMARY KEY, 
                            userID VARCHAR(100) ,
                            userNick VARCHAR(255),
                            userGroupNick VARCHAR(255),
                            createTime TIMESTAMP default (datetime('now', 'localtime'))  
                            );''' 
        self.createTbl(sql_add)

    def createEachDayTbl(self,tableName):
        '''
        创建每日打卡表
        '''
        sql_add = '''CREATE TABLE %s(
                                    ID INTEGER PRIMARY KEY, 
                                    FirstTime VARCHAR(32),
                                    isOff Boolean DEFAULT 0,
                                    OffReason VARCHAR(255) DEFAULT 'Null',
                                    isLate Boolean DEFAULT 0
                                    );'''% tableName
        self.createTbl(sql_add)

    def createDaysDataTbl(self):
        '''
        创建打卡统计表
        '''
        sql_add = '''CREATE TABLE DAY_TABLE(
                                    day VARCHAR(32) PRIMARY KEY, 
                                    AbsentList VARCHAR(255),
                                    OffList VARCHAR(255),
                                    LateList VARCHAR(255),
                                    NormalList VARCHAR(255)
                                    );'''
        self.createTbl(sql_add)
    def createSumAllTbl(self):
        '''
        创建连击表
        '''
        sql_add = '''CREATE TABLE SUM_TABLE( 
                                            ID INTEGER PRIMARY KEY, 
                                            weekCombo integer,
                                            MonthCombo integer,
                                            yearCombo integer,
                                            Combo integer,
                                            MaxCombo integer
                                            );'''
        self.createTbl(sql_add)


    def deleteFromTbl(self,tableName,condition = ''):
        sql_delete = 'delete FROM %s %s ;' % (tableName,condition)
        self.deleteData(sql_delete)
        
##查卡系统操作类
class RobotOperation(WXBot):
    def __init__(self,day,log):
        WXBot.__init__(self)
        self.log = log
        self.day = day
        #初始化数据库操作对象
        sqlog = logger.Logger(logname='dblog.txt', loglevel=4, logger='db').getlog()
        self.sq = mysqlite('test.db','',sqlog)
        #初始化创建表
        self.sq.createUserTbl()
        self.sq.createSumAllTbl()
        self.sq.createEachDayTbl('day%s'%self.day)
        self.sq.createDaysDataTbl()
        #初始化群用户字典和群id
        #群用户格式： group_users[用户唯一标识] = （用户昵称，群内昵称）
        self.MyGid = ''
        with codecs.open('group.txt','r',encoding = 'UTF8') as f:
            self.group_name = f.read().strip(u'\ufeff')
        self.group_users = self.getUserList()
        #初始化用户表
        self.updateUser()
        #初始化当天的迟到参数
        #1.转day为添加了-的日期
        self.today = self.day[0:4]+'-'+self.day[4:6]+'-'+self.day[6:]
        #2.开始时间为3:30
        self.startTime = '%s 03:30:00' % self.today
        #3.迟到时间为7:30
        self.endTime = '%s 07:30:59' % self.today
        
    ########## 1.用户操作相关 ##################
    def getUserList(self):
        group_users = {}
        with open(os.path.join(self.temp_pwd,'group_list.json'),'r') as f:
            group_list = json.load(f)
        for i in group_list:
            if i['NickName'] == self.group_name:
                self.MyGid = i['UserName']
                self.log.debug(u'我的群uid为：%s' % self.MyGid)
        with open(os.path.join(self.temp_pwd,'group_users.json'),'r') as f:
            data = json.load(f)
        for k,v in data.items():
            if k != i['UserName']:
                continue
            else:
                for index,user in enumerate(v):
                    ID = index
                    userID = user['UserName']
                    userNick = user['NickName']
                    userGroupNick = user['DisplayName']
                    group_users[userID] = (userNick,userGroupNick)
        return group_users

    def updateUser(self):
        '''
        更新用户，用于每天凌晨任务，及初始化对象时
        用到其他函数：updateUserTbl，delUserFromTbl，delDataFromTbl
        '''
        group_users = {}
        userdata = self.sq.searchTbl()
        #倒转群组用户dict
        func = lambda z:dict([(x, y) for y, x in z.items()])
        tmpdict = func(self.group_users)
        #pdb.set_trace()
        if userdata == []:
            ID = -1
        else:
            for (ID,userID,userNick,userGroupNick,createTime) in userdata:
                group_users[userID] = (userNick,userGroupNick)
                if self.group_users.has_key(userID):
                    if self.group_users[userID] == (userNick,userGroupNick):
                        self.log.debug(u"用户%s已存在" % userNick)
                        continue
                    else:
                        self.updateUserTbl(ID,userID,self.group_users[userID][0],self.group_users[userID][1])
                        self.log.debug('%s,%s,%s,%s' % (ID,userID,userNick,userGroupNick))
                        self.log.info(u"用户%s修改昵称，表数据已更新" % self.group_users[userID][0])
                else:

                    #判断用户是否存在
                    if tmpdict.has_key((userNick,userGroupNick)):
                        #用户已存在，更新userID
                        self.updateUserTbl(ID,tmpdict[(userNick,userGroupNick)],userNick,userGroupNick,True)
                        self.log.debug('%s,%s,%s,%s' % (ID,tmpdict[(userNick,userGroupNick)],userNick,userGroupNick))
                        self.log.info(u"用户%s的唯一标识发生变更，表数据已更新" % userNick)
                        group_users[tmpdict[(userNick,userGroupNick)]] = (userNick,userGroupNick)
                    else:
                        self.log.info(u"用户%s不在群中，删除对应表数据" % userNick)
                        self.delUserFromTbl(ID)
                        self.delDataFromTbl(ID)
        for k,v in self.group_users.items():
            if not group_users.has_key(k):
                if v[0] == u'小萌机器人':
                    continue
                self.log.info(u"用户%s不在表中，添加对应表数据" % v[0])
                self.insertUserToTbl(int(ID)+1,k,v[0],v[1])
                ID += 1


    def updateUserTbl(self,id,userID,userNick,userGroupNick,FLAG = False):
        if FLAG :
            search_result = self.sq.searchTbl('ID','USER_TABLE','''where userNick = '%s' and userGroupNick = '%s' ''' % (userNick,userGroupNick))
        else:
            search_result = self.sq.searchTbl('ID','USER_TABLE','where userID = "%s"' % userID)    
        if search_result == []:
            self.log.error(u"该用户不在表中:%s" % userID)
            self.insertUserToTbl(id,userID,userNick,userGroupNick)
        else:
            if id == search_result[0]:
                self.log.warning('查询id不一致：原id%s，表id%s' % (id,search_result[0]))
            sql_update = 'update USER_TABLE set userID = ?,userNick = ?,userGroupNick = ? where id = %d ' % id
            data = (userID,userNick,userGroupNick)
            if self.sq.updateData(sql_update,data)!= False:
                self.log.info(u"更新用户数据成功")
            else:
                self.log.error(u"更新用户数据失败")
    
    def delUserFromTbl(self,id):
        if self.sq.deleteFromTbl('USER_TABLE','where ID = %s' % id)!=False:
            self.log.info(u"删除用户表数据成功")

    def delDataFromTbl(self,id):
        if self.sq.deleteFromTbl('day%s'%self.day,'where ID = %s' % id) != False:
            self.log.info(u"删除用户%s早起数据成功" % self.day)

    def insertUserToTbl(self,id,userID,userNick,userGroupNick):
        sql_insert = 'insert into USER_TABLE(ID,userID,userNick,userGroupNick) values(?,?,?,?)'
        data = (id,userID,userNick,userGroupNick)
        if self.sq.insertData(sql_insert,data) != False:
            self.log.info(u"添加用户数据成功")
    
    ###############1.end##############
    
    ###############2.早起打卡录入相关##############
    def updateUserMorningData(self,userID,msg_time):
        self.log.info(u'更新用户%s的早起打卡数据' % userID)
        flag,clockTime = self.handleTime(userID,msg_time)
        if clockTime!='':
            if clockTime >= self.startTime and clockTime <= self.endTime:
                self.updateMorningData('day%s'%self.day,userID,clockTime,isLate = 0)
            elif clockTime < self.startTime:
                return True
            else:
                self.updateMorningData('day%s'%self.day,userID,clockTime,isLate = 1)
        else:
            return False


    def updateMorningData(self,tableName,userID,FirstTime,isOff = 0,OffReason = 'Null', isLate = 0):
        search_result = self.getMorningData(userID,tableName[3:])
        if  search_result == []:
            self.insertMorningData(tableName,userID,FirstTime,isOff,OffReason,isLate)
        else:
            if FirstTime > search_result[0][1] and isOff == 0:
                self.log.info(u"用户%s早起数据无需更新" % userID)
                return True
            if isOff == 0 and isLate == 0:
                sql_update = '''update %s set FirstTime = ? where id = (select ID from USER_TABLE where userID = '%s') ''' % (tableName,userID)
                data = (FirstTime)
            elif isLate != 0:
                sql_update = '''update %s set FirstTime = ?,isLate = ? where id = (select ID from USER_TABLE where userID = '%s') ''' % (tableName,userID)
                data = (FirstTime,isLate)
            elif isOff != 0:
                sql_update = '''update %s set isOff = ?,OffReason = ? where id = (select ID from USER_TABLE where userID = '%s') ''' % (tableName,userID)
                data = (isOff,OffReason)
            if self.sq.updateData(sql_update,data)!= False:
                self.log.info(u"更新用户早起数据成功:sql:%s,data:%s" %(unicode(sql_update),unicode(data)))

    def insertMorningData(self,tableName,userID,FirstTime,isOff = 0,OffReason = 'Null', isLate = 0):
        search_result = self.sq.searchTbl('ID','USER_TABLE','where userID = "%s"' % userID) 
        if search_result == []:
            self.log.error(u"该用户不在表中:%s" % userID)
            return False,
        else:
            ID = search_result[0][0]
        if isOff == 0 and isLate == 0:
            sql_insert = 'insert into %s(id,FirstTime) values(?,?)' % tableName
            data = (ID,FirstTime)
        elif isOff == 0:
            sql_insert = 'insert into %s(id,FirstTime,isLate) values(?,?,?)' % tableName
            data = (ID,FirstTime,isLate)
        else:
            sql_insert = 'insert into %s(id,FirstTime,isOff,OffReason) values(?,?,?,?)' % tableName
            data = (ID,FirstTime,isOff,OffReason)
        if self.sq.insertData(sql_insert,data) != False:
            self.log.info(u"添加用户早起数据成功")
    
    def getMorningData(self,userID,day):
        search_result = self.sq.searchTbl('*','day%s'%day,'where ID = (select ID from USER_TABLE where userID = "%s")' % userID)
        return search_result

    def handleTime(self,userID,msg_time):
        #pdb.set_trace()
        search_result = self.sq.searchTbl('ID,userNick,userGroupNick','USER_TABLE',' where userID = "%s"' % userID)
        if search_result == []:
            self.log.error(u"该用户不在表中:%s" % userID)
            return False,u'user is not in table'
        else:
            userGroupNick = search_result[0][2]
            if u'时差' in userGroupNick :
                try:
                    #pdb.set_trace()
                    diff = userGroupNick.split(u'时差')[1]
                    import re
                    diffTime = re.findall(r'\d+',diff)
                    if diffTime == []:
                        ChineseNumber = [u'一',u'二',u'三',u'四',u'五',u'六',u'七',u'八',u'九']
                        for i,v in enumerate(ChineseNumber):
                            if v in diff:
                                diffTime = i+1
                    else:
                        diffTime = diffTime[0]
                    if u'加' not in diff or u'早' not in diff:
                        diffTime = -int(diffTime)
                    msg_time = self.StrtimeFunc(msg_time,hour = diffTime)
                except Exception as e:
                    self.log.error(u'用户%s是没有按规则填写昵称的时差党，按正常处理啦！' % userGroupNick)
                    return True,msg_time
            return True,msg_time

    ##############2。end######################

    ##############3. 获取迟到列表#############################
    def updateDaysData(self,day,AbsentList,OffList,LateList,NormalList):
        search_result = self.sq.searchTbl('*','DAY_TABLE','where day = "%s"' % day)
        if search_result == []:
            sql_add = 'insert into DAY_TABLE values(?,?,?,?,?)'
            data = (day,unicode(AbsentList),unicode(OffList),unicode(LateList),unicode(NormalList))
            if self.sq.insertData(sql_add,data)!=False:
                self.log.info(u'新增用户每日数据成功')
        else:
            sql_update = 'update DAY_TABLE set AbsentList = ?,OffList = ?,LateList = ?,NormalList = ? where day = "%s" '% day
            data = (unicode(AbsentList),unicode(OffList),unicode(LateList),unicode(NormalList))
            if self.sq.updateData(sql_update,data)!=False:
                self.log.info(u'更新用户每日数据成功')

    def getDaysData(self,day):
        AbsentList = []
        LateList = []
        OffList = []
        NormalList = []

        AbsentIDList = []
        LateIDList = []
        OffIDList = []
        NormalIDList = []

        userlist = self.sq.searchTbl('ID,userNick,userGroupNick','USER_TABLE')
        if userlist!= []:
            try:
                for i in userlist:
                    userMorning = self.sq.searchTbl('*','day%s'%day,'where ID = %d' %i[0])
                    if  userMorning== []:
                        AbsentIDList.append(i[0])
                        AbsentList.append(i[1] if i[2] == '' else i[2])
                    elif userMorning[0][2] == 1:
                        OffIDList.append(i[0])
                        OffList.append(u'%s 原因:%s' % (i[1] if i[2] == '' else i[2],userMorning[0][3]))
                    elif userMorning[0][4] == 1:
                        LateIDList.append(i[0])
                        LateList.append(u'%s 时间:%s' % (i[1] if i[2] == '' else i[2],userMorning[0][1]))
                    else:
                        NormalIDList.append(i[0])
                        NormalList.append(u'%s 时间:%s' % (i[1] if i[2] == '' else i[2],userMorning[0][1]))
                self.updateDaysData(day,AbsentIDList,OffIDList,LateIDList,NormalIDList)
                return AbsentList,LateList,OffList,NormalList
            except Exception as e:
                self.log.error(unicode(e))
                self.log.error(traceback.print_exc())
                return False,u'没有查卡记录，查询失败'
        else:
            return False,u'用户列表为空，请排查'

    def getTwoDaysData(self,day):
        AbsentList = []
        LateList = []
        OffList = []
        NormalList = []
        #几天的结果
        result1 = self.sq.searchTbl('*','DAY_TABLE','where day = "%s"' % day)
        self.log.debug(u'下面是一天的查询结果')
        self.log.debug(result1)
        yesterday = self.StrTbltimeFunc(day,day = -1)
        result2 = self.sq.searchTbl('*','DAY_TABLE','where day = "%s"' % yesterday)
        self.log.debug(u'下面是一天的查询结果2')
        self.log.debug(result2)
        if result1!=[] and result2!=[]:
            #pdb.set_trace()
            z = lambda x:set(eval(x))
            AbsentList = list(z(result1[0][1]) & z(result2[0][1]))
            OffList = list(z(result1[0][2]) | z(result2[0][2]))
            LateList = list(z(result1[0][3]) & z(result2[0][3]) | z(result1[0][1]) & z(result2[0][3]) |z(result1[0][3]) & z(result2[0][1]))
            NormalList = list(z(result1[0][4]) | z(result2[0][4]))
            RealNormalList =list(z(result1[0][4]) & z(result2[0][4]))
            FateNormalList = list(set(NormalList) - set(RealNormalList) - set(OffList))
        else:
            return False,u'两天中有未查卡，查询失败'
        self.log.debug('AbsentList = "%s",LateList = "%s",OffList = "%s"' % (unicode(AbsentList),unicode(LateList),unicode(OffList)) )
        return AbsentList,LateList,OffList,(NormalList,RealNormalList,FateNormalList)

    def getTwoDaysResult(self,day,reply=''):
        result = self.getTwoDaysData(day)
        if result[0]!=False:
            z = lambda x:self.transferListID(i)
            result =  [z(i) for i in result[0:3]] 
            return self.FormatResult(result,reply)
        else:
            return self.FormatResult(result,reply)

    def getFourDaysData(self,day):
        tuple1 = self.getTwoDaysData(day)
        self.log.debug(u'下面是睡懒觉人的查询结果')
        self.log.debug(unicode(tuple1))
        DayBefore = self.StrTbltimeFunc(day,day = -2)
        tuple2 = self.getTwoDaysData(DayBefore)
        self.log.debug(u'下面是睡懒觉人的查询结果2')
        self.log.debug(unicode(tuple2))
        if tuple1[0] !=False and tuple2[0]!=False:
            FateList = list(set(tuple1[3][2] ) & set(tuple2[3][2]))
            self.log.debug(unicode(FateList))
        elif tuple1[0] == False:
            return False,u'前两天中有未查卡，查询失败'
        else:
            return False,u'后两天中有未查卡，查询失败'
        return True,FateList

    def getFourDaysResult(self,day,reply = ''):
        result = self.getFourDaysData(day)
        if result[0] == False:
            return reply+result[1]
        else:
            result = self.transferListID(result[1])
            reply += u'睡懒觉的人为：'
            for i,user in enumerate(result):
                reply += u'【%d】%s\n' %(i+1,user)
            if result == []:
                reply += u'没有人睡懒觉'
            return reply


    def transferListID(self,List):
        returnList = []
        for ID in List:
            search_result = self.sq.searchTbl('ID,userNick,userGroupNick','USER_TABLE','where ID = "%s"' % ID)
            if search_result!= []:
                returnList.append( search_result[0][1] if search_result[0][2] == '' else search_result[0][2])
        return returnList

    def getOnesResult(self,userID,reply = ''):
        day = []
        #pdb.set_trace()
        user = self.sq.searchTbl(condition = 'where userID = "%s" or userNick = "%s" or userGroupNick = "%s"' % (userID,userID,userID))
        (ID,userID,userNick,userGroupNick,createTime) = user[0]
        createDay = ''.join(createTime.split('-'))[0:8]
        for i in range(0,4):
            daytmp = self.StrTbltimeFunc(self.day,day = -i)[0:8]
            if daytmp <= createDay:
                break
            day.append(daytmp)
        if day == []:
            reply += u'你刚进群，不要着急哦'
        for i,v in enumerate(day):
            reply+= u'\n%s的打卡情况为:' % v
            search_result = self.sq.searchTbl('FirstTime,isOff,OffReason,isLate','day%s'%v,'where ID = "%s"'%ID)
            if search_result == []:
                reply+= u'未打卡'
            else:
                if search_result[0][1] == 1:
                    reply += u'请假，原因为%s' % search_result[0][2] 
                elif search_result[0][3] == 1:
                    reply += u'迟到，打卡时间为：%s' % search_result[0][0] 
                else:
                    reply += u'打卡时间为%s：' % search_result[0][0] 
        return reply

    def StrtimeFunc(self,t,day = 0,hour = 0):
        Strtime = t
        t = time.mktime(time.strptime(t, "%Y-%m-%d %H:%M:%S"))
        date = datetime.datetime.fromtimestamp(t)
        if day != 0:
            d1 = datetime.timedelta(days = abs(int(day)))
            Strtime = date + d1 if day >0 else date -d1
        if hour != 0:
            d1 = datetime.timedelta(hours = abs(int(hour)))
            Strtime = date + d1 if hour >0 else date -d1
        return str(Strtime)[:19]

    def StrTbltimeFunc(self,t,day = 0,hour = 0):
        t = t + ' 07:30:00'
        Strtime = t
        t = time.mktime(time.strptime(t, "%Y%m%d %H:%M:%S"))
        date = datetime.datetime.fromtimestamp(t)
        if day != 0:
            d1 = datetime.timedelta(days = abs(int(day)))
            Strtime = date + d1 if day >0 else date - d1
            Strtime = ''.join(str(Strtime)[:19].split(' ')[0].split('-'))
        if hour != 0:
            d1 = datetime.timedelta(hours = abs(int(hour)))
            Strtime = date + d1 if hour >0 else date - d1
            Strtime = ''.join(str(Strtime)[:19].split(' ')[0].split('-'))
        return Strtime
    
    def FormatResult(self,result,reply = ''):
        if result[0] == False:
            return reply + result[1]
        reply += u'未打卡人为：'
        for i,user in enumerate( result[0]):
            reply += u'【%d】%s\n' %(i+1,user)
        if result[0]==[]:
            reply += u'没有人未打卡\n'
        reply += u'迟到人为：'
        for i,user in enumerate( result[1]):
            reply += u'【%d】%s\n' %(i+1,user)
        if result[1] == []:
            reply += u'没有人迟到\n'
        reply += u'请假人为：'
        for i,user in enumerate( result[2]):
            reply += u'【%d】%s\n' %(i+1,user)
        if result[2] == []:
            reply += u'没有人请假\n'
        return reply



def testinit():
    log = logger.Logger(logname='error.txt', loglevel=4, logger='error').getlog()
    NowTime = time.strftime('%Y%m%d %H:%M:%S').split(' ')
    today = 'day%s' % NowTime[0]
    testobj = RobotOperation(today,log)

def testclock():
    log = logger.Logger(logname='error.txt', loglevel=4, logger='error').getlog()
    NowTime = time.strftime('%Y%m%d %H:%M:%S').split(' ')
    #today = 'day%s' % NowTime[0]
    today = 'day20170104'
    testobj = RobotOperation(today[3:],log)
    testobj.updateUserMorningData('@2ef4faed69cbbb57a9009c62213ef479','2017-01-04 07:20:00')
    testobj.updateUserMorningData('@ce49d1954bceaca53f44b6be038fffe0b790ced6050343db666c0b62203c2c2a','2017-01-04 07:20:00')
    testobj.updateUserMorningData('@1239d6d4f8a496e81f9ecba24b46c790','2017-01-04 03:20:00')
    testobj.updateUserMorningData('@1239d6d4f8a496e81f9ecba24b46c790','2017-01-04 09:20:00')
    result = testobj.getDaysData(today[3:])
    print testobj.FormatResult(result)
    print testobj.getOnesResult('@1239d6d4f8a496e81f9ecba24b46c790')
    print testobj.getTwoDaysResult(today[3:])
    print testobj.getFourDaysResult(today[3:])

def main():
    log = logger.Logger(logname='error.txt', loglevel=4, logger='error').getlog()
    NowTime = time.strftime('%Y%m%d %H:%M:%S').split(' ')
    today = 'day%s' % NowTime[0]
    testobj = RobotOperation(today,log)
    print testobj.handleTime('@d46fe7b24b8ca60cb3913314fe08bc23998bca7f46d905900562bb9a3c39e5d1','2016-01-29 23:30:00')

if __name__ == '__main__':
    testinit()
