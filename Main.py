# 全局headers
import datetime
import json
import re
from os.path import join
from os import path
import chnSegment
import plotWordcloud

import requests

headers = {}


# 根据BV号获取cid，考虑视频分P，返回一个cid列表
def get_cid(bv):
    cid_url = f'https://api.bilibili.com/x/player/pagelist?bvid={bv}'
    res = requests.get(cid_url)
    res_text = res.text
    res_dict = json.loads(res_text)
    part_list = res_dict['data']
    new_part_list = []
    for part in part_list:
        new_part = {
            'cid': part.get('cid'),
            'part_name': part.get('part')
        }
        new_part_list.append(new_part)
    return new_part_list


# 获取日期列表
def _get_one_month_date_list(cid, month):
    date_list_url = f'https://api.bilibili.com/x/v2/dm/history/index?type=1&oid={cid}&month={month}'
    res = requests.get(date_list_url, headers=headers)
    res_dict = json.loads(res.text)
    date_list = res_dict.get('data')
    return date_list


# 获取所有历史弹幕的日期 2016-03 datetime day+1
def get_date_history(cid_data_list):
    date_history_list = []
    for cid_item in cid_data_list:
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        while True:
            # 获取一个月的日期列表
            one_month_date_list = _get_one_month_date_list(cid_item['cid'], f'{year}-{month:>02}')
            if one_month_date_list:
                one_month_date_list.reverse()
                cid_item['date_list'] = cid_item.get('date_list', [])
                cid_item['date_list'].extend(one_month_date_list)
                this_month_first_day = datetime.date(year, month, 1)  # 4月1 减 1天  上一个月的最后一天
                pre_month_last_day = this_month_first_day - datetime.timedelta(days=1)
                year = pre_month_last_day.year
                month = pre_month_last_day.month
            else:
                break
        date_history_list.append(cid_item)
    return date_history_list


# 下载弹幕xml文件
def _get_dan_mu_xml(cid, date):
    dan_mu_url = f'https://api.bilibili.com/x/v2/dm/history?type=1&oid={cid}&date={date}'
    res = requests.get(dan_mu_url, headers=headers)
    dan_mu_xml = res.content.decode('utf8')
    return dan_mu_xml


# 解析提取弹幕文件

def _parse_dan_mu(dan_mu_xml):
    reg = re.compile('<d p="([\s\S]*?)">([\s\S]+?)</d>')
    find_result = reg.findall(dan_mu_xml)
    dan_mu_list = []
    for line in find_result:
        p, dan_mu = line
        time_stamp = int(p.split(',')[4])
        date_array = datetime.datetime.fromtimestamp(time_stamp)
        send_time = date_array.strftime('%Y-%m-%d %H:%M:%S')
        dan_mu_list.append((send_time, dan_mu))
    return dan_mu_list


# 根据日期获取当天的弹幕
def get_all_dan_mu(date_history_list, bv):
    for item in date_history_list:
        # 没有分P的视频是没有part_name的
        part_name = item.get('part_name')
        # 不确定没有分P的视频有没有分P名，所以这里先判断一下
        filename = bv
        if part_name:
            filename = f'{bv}_{part_name}'
        with open(f'doc//{filename}.txt', 'w', encoding='utf8') as f:
            for date in item['date_list']:
                dan_mu_xml = _get_dan_mu_xml(item['cid'], date)
                dan_mu_list = _parse_dan_mu(dan_mu_xml)
                # 只打印前每天的前1条，提升下用户体验
                print(dan_mu_list[0])
                for dan_mu_item in dan_mu_list:
                    # 使用 <;> 作为时间和弹幕的分隔符
                    # line = '<;>'.join(dan_mu_item[1])
                    line = join(dan_mu_item[1])
                    f.writelines(line)
                    f.write('\n')
        return filename


if __name__ == '__main__':
    bv = 'BV1wD4y1o7AS'
    # 查看历史弹幕必须先登录，需要发送cookies，请到浏览器登录B站，然后复制cookies
    cookie_str = """sid=8vd13q70; DedeUserID=352344482; DedeUserID__ckMd5=6fd10e5604fdd0f8; SESSDATA=6d229ed3%2C1605761169%2C81fa2*51; bili_jct=4bf80916780eef006feb26a006f9fa92; LIVE_BUVID=AUTO1715902091706163; rpdid=|(YuRJRJRkk0J'ulmukR|kkl; _uuid=D0210717-E454-7B0C-2119-692BF553A92302306infoc; buvid3=E147F691-0ECC-61E1-13CB-53DC1EF5EB1447081infoc; CURRENT_QUALITY=80; blackside_state=1; CURRENT_FNVAL=80; bfe_id=fdfaf33a01b88dd4692ca80f00c2de7f"""
    headers['cookie'] = cookie_str
    # 根据BV号获取cid,视频可能有分P，需考虑
    cid_data_list = get_cid(bv)
    # 获取所有历史弹幕的日期
    date_history_list = get_date_history(cid_data_list)
    # 根据日期获取当天的弹幕
    fileName = get_all_dan_mu(date_history_list, bv)

    # 以下是生成词云图片。图片样式在plotWordcloud.py配置

    # 读取文件
    d = path.dirname(__file__)
    text = open(path.join(d, f'doc//{fileName}.txt'), encoding='utf-8', errors='ignore').read()

    # 若是中文文本，则先进行分词操作
    text = chnSegment.word_segment(text)

    # 生成词云
    plotWordcloud.generate_wordcloud(text, fileName)
