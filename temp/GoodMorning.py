#!/usr/bin/env python
# coding: utf-8
import json
import os
a = [u"早！我是迟到分割线hhhhh~",u"早！看到我还没打卡的人你已经迟到了！",u'早！一日之计在于晨~！',u'早上好！太阳要晒屁股啦！']
with open('GoodMorning.json','w') as f:
    f.write(json.dumps(a))   
