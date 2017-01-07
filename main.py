#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import datetime
import codecs
import ConfigParser
import json
import random
import logger
from operation import *

class MyWXBot(WXBot):
    def __init__(self,log):
        WXBot.__init__(self)
        #是否开启机器人，可关闭
        self.robot_switch = True
        #日期标识，范围0-4（如登录时间已过打卡时间，可设置为-1，从第二天开始查卡。查卡中间若有重启，自行赋值）
        self.dayLable = 2
        #查卡员ID
        self.checker = u''
        #微信群ID，每次重新登录会刷新
        self.MyGID = ''
        #早8点推送标识，未推送为True，推送后为False,零点刷新
        self.MorningLabel = True
        #晚8点已推送标识，未推送为True，推送后为False,零点刷新
        self.resultLable = True
        #晚8点推送标识，可关闭
        self.push = True
        #日志记录
        self.log = log
        #更新标识，用于初次登录后进行用户更新
        self.updated = False
        #智能回复图灵key，访问图灵接口进行回复，从文件中读取
        self.tuling_key = "" 
        try:
            cf = ConfigParser.ConfigParser()
            cf.read('conf.ini')
            self.tuling_key = cf.get('main', 'key')
            #获取微信群名
            with codecs.open('group.txt','r',encoding = 'UTF8') as f:
                self.groupName = f.read().strip(u'\ufeff')
        except Exception as e:
            self.log.warning(e)
        print 'tuling_key:', self.tuling_key
        NowTime = time.strftime('%Y%m%d %H:%M:%S').split(' ')
        today = NowTime[0] 
        self.today = today
        self.LateTime ='%s %s' %( time.strftime('%Y-%m-%d %H:%M:%S').split(' ')[0],'07:31:00')


    def tuling_auto_reply(self, uid, msg):
        if self.tuling_key:
            url = "http://www.tuling123.com/openapi/api"
            user_id = uid.replace('@', '')[:30]
            body = {'key': self.tuling_key, 'info': msg.encode('utf8'), 'userid': user_id}
            r = requests.post(url, data=body)
            print r.text
            respond = json.loads(r.text)
            result = ''
            if respond['code'] == 100000:
                result = respond['text'].replace('<br>', '  ')
            elif respond['code'] == 200000:
                result = result + respond['text'].replace('<br>', '  ') + u"： " + respond['url']
            elif respond['code'] == 302000:
                for k in respond['list']:
                    result = result + u"【" + k['source'] + u"】 " +\
                        k['article'] + "\t" + k['detailurl'] + "\n"
            elif respond['code'] == 308000:
                for k in respond['list']:
                    result = result + u"【" + k['name'] + u"】 " +\
                        k['info'] + "\t" + k['detailurl'] + "\n"
            else:
                result = respond['text'].replace('<br>', '  ')

            print '    ROBOT:', result
            return result
        else:
            return u"知道啦"

    def auto_switch(self, msg):
        msg_data = msg['content']['data']
        stop_cmd = [u'退下', u'走开', u'关闭', u'关掉', u'休息', u'滚开']
        start_cmd = [u'出来', u'启动', u'工作']
        if self.robot_switch:
            for i in stop_cmd:
                if i == msg_data:
                    self.robot_switch = False
                    self.send_msg_by_uid(u'[Robot]' + u'机器人已关闭！', msg['to_user_id'])
        else:
            for i in start_cmd:
                if i == msg_data:
                    self.robot_switch = True
                    self.send_msg_by_uid(u'[Robot]' + u'机器人已开启！', msg['to_user_id'])

    def handle_msg_all(self, msg):
        #print msg
        if not self.robot_switch and msg['msg_type_id'] != 1:
            return
        if msg['msg_type_id'] == 1 and msg['content']['type'] == 0:  # reply to self
            self.auto_switch(msg)
        elif msg['msg_type_id'] == 4 :
            if msg['content']['type'] == 0:  # text message from contact
                self.send_msg_by_uid(self.tuling_auto_reply(msg['user']['id'], msg['content']['data']), msg['user']['id'])
            else:
                self.send_msg_by_uid(u"对不起，只认字，其他杂七杂八的我都不认识，,,Ծ‸Ծ,,",  msg['user']['id'])
        elif msg['msg_type_id'] == 99 : #新加好友功能支持
            if msg['content']['type'] == 0:  # text message from contact
                self.send_msg_by_uid(self.tuling_auto_reply(msg['user']['id'], msg['content']['data']), msg['user']['id'])
            elif msg['content']['type'] == 12:
                self.send_msg_by_uid(u'hello~我是小萌~有什么要跟我说的嘛！', msg['user']['id'])

        elif msg['msg_type_id'] == 3 :  # group message
            #print msg
            print msg['content']['type'] 
            #撤回  msg['content']['type'] == 10
            #新加群 msg['content']['type'] == 12
            is_at_me = False
            if 'detail' in msg['content']:
                #print msg
                my_names = self.get_group_member_name(self.my_account['UserName'], msg['user']['id'])
                if my_names is None:
                    my_names = {}
                if 'NickName' in self.my_account and self.my_account['NickName']:
                    my_names['nickname2'] = self.my_account['NickName']
                if 'RemarkName' in self.my_account and self.my_account['RemarkName']:
                    my_names['remark_name2'] = self.my_account['RemarkName']
  
                for detail in msg['content']['detail']:
                    if detail['type'] == 'at':
                        for k in my_names:
                            if my_names[k] and my_names[k] == detail['value']:
                                is_at_me = True
                                break
            ###是打卡群id的消息，或是测试群的消息
            if msg['user']['id'] == self.MyGID or msg['user']['name'] == u'测试':
                msg['time'] = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(msg['time']))
                if is_at_me:
                    src_name = msg['content']['user']['name']
                    reply = 'to ' + src_name + ': '
                    if msg['content']['type'] == 0:  # text message
                        userid = msg['content']['user']['id']
                    #####下面这些命令应用正则和字典进行优化- -~回头弄~~~~
                    ###请假
                        if u'请假 ' in msg['content']['desc'] :
                            try:
                                reason = msg['content']['desc'].split(u'请假 ')[1]
                                if self.op.updateMorningData('day%s'%self.today,userid,msg['time'],1,reason)!=False:
                                    reply += u'请假成功！请假原因为%s' % reason
                                else:
                                    reply += u'请假失败！请检查格式，如格式正确，请联系yny_N排查'
                            except Exception as e:
                                self.log.error(traceback.print_exc())
                    ###两天的查卡
                        elif u'两天的查卡' in msg['content']['desc']:
                            reply = self.op.getTwoDaysResult(self.today,reply)
                    ###昨天的查卡
                        elif u'昨天的查卡' in msg['content']['desc']:
                            yesterday = self.op.StrTbltimeFunc(self.today,day = -1)
                            result = self.op.getDaysData(yesterday)
                            reply = self.op.FormatResult(result,reply)
                    ###四天的查卡（只有四天中偷懒的人群）
                        elif u'四天的查卡' in msg['content']['desc']:
                            reply = self.op.getFourDaysResult(self.today,reply)
                            #self.send_msg_by_uid(FourDaysReply, self.MyGID)
                    ###某天的查卡，输入20161230格式日期，会抛出异常，可用正则修复- -  懒。
                        elif u'的查卡' in msg['content']['desc']:
                            day = msg['content']['desc'].split(u'的查卡')[0].strip()
                            result = self.op.getDaysData(day)
                            reply = self.op.FormatResult(result,reply)
                    ###查卡，当天的查卡
                        elif msg['content']['desc'] == u'查卡':
                            result = self.op.getDaysData(self.today)
                            reply = self.op.FormatResult(result)
                    ###个人查卡
                        elif msg['content']['desc'] == u'我的打卡':
                            reply += u'你最近四天的打卡情况为：\n'
                            reply = self.op.getOnesResult(userid,reply)
                    ###他人查卡
                        elif msg['content']['desc'] == u'的打卡' :
                                person = ''
                                for detail in msg['content']['detail']:
                                    if detail['type'] == 'at':
                                        if u'小萌机器人' in detail['value'] :
                                            continue
                                        else:
                                            person = detail['value']
                                            break
                                if person!= '' :
                                    reply += u'\n 他的打卡情况是：' 
                                    reply = self.op.getOnesResult(person,reply)
                                else:
                                    reply += u'你说的是谁，小萌不认识。。。'
                    ###更新群组用户昵称
                        elif msg['content']['desc'] == u'更新昵称':
                            self.batch_get_group_members()
                            self.op.group_users = self.op.getUserList()
                            self.op.updateUser()
                            reply += u'更新成功！'
                    ###非命令图灵回复
                        else:
                            reply += self.tuling_auto_reply(userid, msg['content']['desc'])
                    ###非文字型at（非文字根本at不了小萌- -）
                    else:
                        reply += u"对不起，只认字，其他杂七杂八的我都不认识，,,Ծ‸Ծ,,"
                    self.send_msg_by_uid(reply, msg['user']['id']) 
                else:
                    ###发送图片信息，更新打卡记录
                    if msg['content']['type'] == 3: # image message
                        self.op.updateUserMorningData(msg['content']['user']['id'],msg['time'])
            else:
                ###非打卡功能群聊
                if is_at_me:
                    src_name = msg['content']['user']['name']
                    reply = 'to ' + src_name + ': '
                    if msg['content']['type'] == 0:  # text message
                        reply += self.tuling_auto_reply(msg['content']['user']['id'], msg['content']['desc'])
                    else:
                        reply += u"对不起，只认字，其他杂七杂八的我都不认识，,,Ծ‸Ծ,,"
                    self.send_msg_by_uid(reply, msg['user']['id'])


    def schedule(self):
        print self.push
        if self.updated == False:
            self.op.group_users = self.op.getUserList()
            self.op.updateUser()
            self.MyGID = self.op.MyGid
            self.updated = True
        NowTime = time.strftime('%Y%m%d %H:%M:%S').split(' ')
        today = NowTime[0] 
        if today > self.today:
            self.log.info( u'开始凌晨定时工作~')
            ####关闭旧对象
            self.op.sq.conn.close()
            ####创建新的对象（以日期为名保存日志）
            log = logger.Logger(logname='%s.txt' % today, loglevel=4, logger=today).getlog()
            self.op = RobotOperation(today,log)
            #推送标识刷新
            self.MorningLabel = True
            self.resultLable = True 
            #日期刷新
            self.today = today
            #查卡天数变更
            self.dayLable = (self.dayLable +1) % 4
            #更新新的用户
            self.batch_get_group_members()
            self.op.group_users = self.op.getUserList()
            self.op.updateUser()
            self.log.info(u'凌晨定时工作结束~')
        #早安语
        MorningTime = NowTime[1]
        #print MorningTime,self.MorningLabel,self.MyGID
        if  self.MorningLabel and MorningTime >= '07:30:00' and MorningTime <='07:31:59' and  self.MyGID!='':
            self.MorningLabel = False
            with open(os.path.join(self.temp_pwd,'GoodMorning.json'), 'r') as f:
                data = json.load(f)
            Morning = random.choice(data)
            self.send_msg_by_uid(Morning, self.MyGID)
            self.log.debug(Morning)
        #查卡结果推送
        if self.push:
            NightTime = NowTime[1]
            print NightTime,self.resultLable,self.MyGID,
            if self.resultLable and NightTime >= '20:00:00' and  NightTime <= '20:10:50' and self.MyGID!='':
                self.resultLable = False
                #告知开始推送
                reply = u'hello艾瑞巴蒂，现在是北京时间8点，小萌将进行查卡结果晚间播报'
                self.send_msg_by_uid(reply, self.MyGID)
                time.sleep(10)

                #推送今天查卡结果
                reply = u'今天的打卡情况为：'
                result = self.op.getDaysData(self.today)
                reply = self.op.FormatResult(result,reply)
                self.send_msg_by_uid(reply, self.MyGID)
                time.sleep(10)

                #推送昨天查卡结果
                reply = u'昨天的打卡情况为：'
                yesterday = self.op.StrTbltimeFunc(self.today,day = -1)
                result = self.op.getDaysData(yesterday)
                reply = self.op.FormatResult(result,reply)
                self.send_msg_by_uid(reply, self.MyGID)
                time.sleep(10)

                #推送被踢人名单结果
                if self.dayLable % 2 == 0:
                    reply = u'今天是第一天哟!\n'
                else:
                    reply = u'今天是第2天该踢人啦！\n'
                reply += u'两天的打卡结果是：'
                reply = self.op.getTwoDaysResult(self.today,reply)
                self.send_msg_by_uid(reply, self.MyGID)

                #第四天综合情况
                if self.dayLable == 3:
                    reply = u'今天是第四天，偷懒的小盆友要被踢啦！'
                    FourDaysReply = self.op.getFourDaysResult(self.today,reply)
                    self.send_msg_by_uid(reply, self.MyGID)

def main():
    log = logger.Logger(logname='wxbot.txt', loglevel=4, logger='error').getlog()
    bot = MyWXBot(log)
    bot.DEBUG = True
    bot.conf['qr'] = 'png' #linux可用tty
    ####my owns####
    bot.today = time.strftime('%Y%m%d %H:%M:%S').split(' ')[0]
    log2 = logger.Logger(logname='%s.txt' %bot.today, loglevel=4, logger=bot.today).getlog()
    bot.op = RobotOperation(bot.today,log2)
    ####my owns end#####
    bot.run()

def test():
    try:
        cf = ConfigParser.ConfigParser()
        cf.read('conf.ini')
        tuling_key = cf.get('main', 'key')
        with codecs.open('group.txt','r',encoding = 'UTF8') as f:
            groupName = f.read()
        pdb.set_trace()
    except Exception as e:
        print e

if __name__ == '__main__':
    main()
