# coding=utf-8

import logging

class Logger():
    def __init__(self, logname, loglevel, logger):
        '''
           指定保存日志的文件路径，日志级别，以及调用文件
           将日志存入到指定的文件中
        '''
        #将loglevel关联到记录等级
        levelDict = {4:logging.DEBUG,3:logging.INFO,2:logging.WARNING,1:logging.ERROR}
        logLevel = levelDict[int(loglevel)]
        # 创建一个logger
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logLevel)

        # 创建一个handler，用于写入日志文件
        fh = logging.FileHandler(logname,encoding = 'utf-8')
        fh.setLevel(logging.INFO)

        # 再创建一个handler，用于输出到控制台
        ch = logging.StreamHandler()
        ch.setLevel(logLevel)
        # 定义handler的输出格式
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] [%(levelname)s] [%(threadName)s:] %(message)s',
                            datefmt='%A,%d %b %Y %H:%M:%S')
        #formatter = format_dict[int(loglevel)]
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # 给logger添加handler
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

   
    def getlog(self):
        return self.logger
