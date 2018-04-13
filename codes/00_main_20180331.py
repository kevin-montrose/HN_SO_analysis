# -*- coding: utf-8 -*-
"""
Created on Tue Mar  6 22:03:26 2018

@author: kaksat
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import gc
import timeit
from functools import reduce
from itertools import chain
from datetime import datetime

os.chdir('F:\Damian\github\kaggle_hacker_news')

### Stack data
 
stack_data1 = pd.read_csv('.\\stack_data\\tags_per_day_1_20180325.csv')
stack_data2 = pd.read_csv('.\\stack_data\\tags_per_day_2_20180306.csv')
stack_data3 = pd.read_csv('.\\stack_data\\tags_per_day_3_20180306.csv')
stack_data4 = pd.read_csv('.\\stack_data\\tags_per_day_4_d3js_tensorflow_20180403.csv')

stack_data = pd.concat([stack_data1, stack_data2, stack_data3, stack_data4])

stack_data['tags'] = stack_data['tags'].str.replace('<', '').str.replace('>', '')
stack_data['post_date'] = pd.to_datetime(stack_data['post_date'])
stack_data.loc[stack_data['tags'] == 'd3js'].describe()


del stack_data1, stack_data2, stack_data3, stack_data4

stack_data.tags.replace('apache-spark', 'spark', inplace = True)
stack_data.tags.replace('d3.js', 'd3js', inplace = True)
stack_data = stack_data.rename(columns = {'score_sum': 'so_score_sum',
                                          'views': 'so_views',
                                          'answers': 'so_answers',
                                          'favorites': 'so_favorites',
                                          'comments': 'so_comments',
                                          'usage_cnt': 'so_usage_cnt'})
#%matplotlib inline      
#          
#for i in stack_data['tags'].unique():
#    plt.plot()
#    stack_plot = stack_data.loc[stack_data['tags'] == i]
#    plt.plot(stack_plot['post_date'], stack_plot['usage_cnt'])
#    plt.title(i)
#    plt.show()
    
### Kaggle data

kaggle_data_raw = pd.read_csv('.\\kaggle_data\\kaggle_data_20180405_2145.csv')
kaggle_data_raw = kaggle_data_raw[
        (kaggle_data_raw.title_match.isnull() == False) |
        (kaggle_data_raw.text_match.isnull() == False)]

# combine ttle and text

#kaggle_data_raw
#kaggle_data_raw.columns
#kaggle_data_raw.loc[:, i] = [list(set(x))
#                                for x in kaggle_data_raw[i].str.split(',')]

idx = pd.date_range('01-01-2006', '31-12-2017')

for i in ['text_match', 'title_match']:
    kaggle_data_raw.loc[:, i] = (kaggle_data_raw[i].str.replace('[', '')
    .str.replace(']', '')
    .str.replace("'", '')
    .str.replace(" ", "")
    .str.replace("\\\\n", "")
    .str.replace("\\\\t", "")
    .str.replace(".", "")
    .str.replace("?", "")
    .str.replace("!", ""))
    

kaggle_data_raw['all_match'] = (kaggle_data_raw['text_match']
    +','+ kaggle_data_raw['title_match'])
kaggle_list = []

from sklearn.preprocessing import MultiLabelBinarizer

for i in ['text_match', 'title_match', 'all_match']:
    # Removal of duplicates
    kaggle_data_raw.loc[:, i] = [list(set(x))
                                for x in kaggle_data_raw[i].str.split(',')]
    
    # Summing the scores per date and text/title match
    s = kaggle_data_raw[i].str.len()
    df = pd.DataFrame({'date': kaggle_data_raw.date.repeat(s),
                          'score': kaggle_data_raw.score.repeat(s),
            i: np.concatenate(kaggle_data_raw[i].values)})
    df = df.loc[df[i] != '']
    kaggle_data_score = pd.pivot_table(df,
                index = 'date', columns = i, values = 'score',
               aggfunc = 'sum', fill_value = 0)
    kaggle_data_score.index = pd.DatetimeIndex(
    kaggle_data_score.index)
    
    kaggle_data_score = kaggle_data_score.reindex(
            idx, fill_value = 0).stack().reset_index()
    colnames = ['date', 'tech', 'hn_' + i] # hn = Hacker News
    kaggle_data_score.columns = list(chain.from_iterable([colnames[0:2], [colnames[2] + '_score']]))
    kaggle_list.append(kaggle_data_score)
    
    # Filling the lacking dates with zeroes for counts

    mlb = MultiLabelBinarizer()
    kaggle_data_cnt = pd.DataFrame(
            mlb.fit_transform(kaggle_data_raw[i]),
            kaggle_data_raw.date, mlb.classes_).sum(level = 0)
    kaggle_data_cnt.index = pd.DatetimeIndex(kaggle_data_cnt.index)
    kaggle_data_cnt = kaggle_data_cnt.reindex(idx, fill_value = 0).stack().reset_index()
    kaggle_data_cnt.columns = list(chain.from_iterable([colnames[0:2], [colnames[2] + '_cnt']]))
    kaggle_data_cnt = kaggle_data_cnt.groupby(['date', 'tech']).sum().reset_index()
    kaggle_data_cnt = kaggle_data_cnt[kaggle_data_cnt.tech != '']
    kaggle_list.append(kaggle_data_cnt)

# Merging data into one kaggle data frame
    
kaggle_data = reduce(lambda df1, df2:
    df1.merge(df2, how = 'outer', on = ['date', 'tech']), kaggle_list)
kaggle_data.date = pd.to_datetime(kaggle_data.date)
data = (pd.merge(kaggle_data, stack_data, how = 'left',
                left_on = ['date', 'tech'], right_on = ['post_date', 'tags'])
        .drop(['post_date', 'tags'], axis = 1)
        .fillna(0))

del kaggle_list, kaggle_data_raw, kaggle_data

# Swift appeared 2nd June 2014: all the data befor this date from Hacker News
# should be dropped

data.drop(data[(data['tech'] == 'swift') & (data['date'] < '2014-06-02')].index |
        data[(data['tech'] == 'spark') & (data['date'] < '2014-05-30')].index |
        data[data['date'] < '2008-09-13'].index, # two days for differences of differences
        # 2007-02-19 - launch of StackOverflow
                inplace = True)

# Group by weekly frequency
data.date = pd.to_datetime(data.date)
data_week = (data.groupby(['tech',
                                    pd.Grouper(key = 'date', freq = 'W-MON')])
                .sum()
                .reset_index())
    
data.loc[data['tech'] == 'javascript'].describe()


#%matplotlib inline

        
todays_date = datetime.now()
if todays_date.month <10:
    month = '0'+str(todays_date.month)
else:
    month = str(todays_date.month)

if todays_date.day <10:
    day = '0'+str(todays_date.day)
else:
    day = str(todays_date.day)
    
TODAY = str(todays_date.year) + month + day


def hn_plots(data = data,
             freq = 'd',
             select_tech = ['d3js', 'javascript', 'tensorflow'],
             alpha = 0.7,
             after_date = '2017-01-01',
             output_date = TODAY,
             common_var = 'hn_all_match_score',
             common_var2 = None,
             common_var3 = None,
             common_var4 = None,
             var1 = 'so_usage_cnt',
             var2 = 'so_score_sum',
             var3 = 'so_answers',
             var4 = 'so_views'):
    
    if(freq == 'w'):
        data = (data.groupby(['tech',
                       pd.Grouper(key = 'date', freq = 'W-MON')])
                .sum()
                .reset_index())
        freq_label = 'weekly'
    elif(freq == 'd'):
        freq_label = 'daily'
    elif(freq == 'm'):
        freq_label = 'monthly'
     
    if common_var2 == None:
        common_var2 = common_var
    if common_var3 == None:
        common_var3 = common_var
    if common_var4 == None:
        common_var4 = common_var
        
    after_date_declared = after_date
        
    for i in select_tech:#data.tech.unique():
        
        fig_daily = plt.figure(figsize = (16,10))
        fig_daily.subplots_adjust(hspace = 0.3)
#        fig_daily.tight_layout()
        ax1 = plt.subplot(221)
        ax2 = ax1.twinx()
        ax3 = plt.subplot(222)
        ax4 = ax3.twinx()
        ax5 = plt.subplot(223)
        ax6 = ax5.twinx()
        ax7 = plt.subplot(224)
        ax8 = ax7.twinx()
        ax1.tick_params(axis='x', labelrotation =45)
        ax2.tick_params(axis='x', labelrotation =45)
        ax3.tick_params(axis='x', labelrotation =45)
        ax4.tick_params(axis='x', labelrotation =45)
        ax5.tick_params(axis='x', labelrotation =45)
        ax6.tick_params(axis='x', labelrotation =45)
        ax7.tick_params(axis='x', labelrotation =45)
        ax8.tick_params(axis='x', labelrotation =45)
        
        # First plot:
        after_date = max(pd.to_datetime(after_date_declared),
                        data.loc[(data['tech'] == i) &
         ((data['hn_all_match_score'] > 0) | (data['so_views']>0))].date.min()).strftime('%Y-%m-%d')
#        print(after_date)    
        data_plot = data.loc[(data['tech'] == i) & (data['date'] >= after_date)]
        ax1.plot(data_plot['date'], data_plot[common_var], 'g-', alpha = alpha)
        ax2.plot(data_plot['date'], data_plot[var1], 'b-', alpha = alpha)
    #    ax1.set_xlabel('Date')
        ax1.set_ylabel('HN', color = 'g')
        ax2.set_ylabel('SO', color = 'b')
        ax2.set_title(var1 + ' vs ' + common_var + ' for ' + i + ' since ' +
                      after_date + '; ' + freq_label)
        
        # Second plot: 
        ax3.plot(data_plot['date'], data_plot[common_var2], 'g-', alpha = alpha)
        ax4.plot(data_plot['date'], data_plot[var2], 'b-', alpha = alpha)
    #    ax3.set_xlabel('Date')
    #    ax3.set_ylabel('Score HN', color = 'g')
#        ax3.tick_params(left='off', labelleft='off')
        ax3.set_ylabel('HN', color = 'g')
        ax4.set_ylabel('SO', color = 'b')
        ax4.set_title(var2 + ' vs ' + common_var2 + ' for ' + i + ' since ' +
                      after_date + '; ' + freq_label)
    
        # Third plot: 
        ax5.plot(data_plot['date'], data_plot[common_var3], 'g-', alpha = alpha)
        ax6.plot(data_plot['date'], data_plot[var3], 'b-', alpha = alpha)
#        ax5.set_xlabel('Date')
        ax5.set_ylabel('HN', color = 'g')
        ax6.set_ylabel('SO', color = 'b')
        ax6.set_title(var3 + ' vs ' + common_var3 + ' for ' + i + ' since ' +
                      after_date + '; ' + freq_label)
        
        # Fourth plot: 
        ax7.plot(data_plot['date'], data_plot[common_var4], 'g-', alpha = alpha)
        ax8.plot(data_plot['date'], data_plot[var4], 'b-', alpha = alpha)
    #    ax7.set_xlabel('Date')
    #    ax7.set_ylabel('Score HN', color = 'g')
#        ax7.tick_params(left='off', labelleft='off')
        ax7.set_ylabel('HN', color = 'g')
        ax8.set_ylabel('SO', color = 'b')
        ax8.set_title(var4 + ' vs ' + common_var4 + ' for ' + i + ' since ' +
                      after_date + '; ' + freq_label)
        
#        fig_daily.autofmt_xdate()
        plt.xticks(rotation=90)
#        plt.setp(ax5.get_xticklabels(), visible=True)
        fig_daily.savefig(output_date + '_' + i + '_' + common_var +
                          '_'+ freq + '_since' + after_date.replace('_', '')
                          + '.png'#, bbox_inches = 'tight'
                          )


hn_plots(data = data, freq = 'w',
         output_date = TODAY,
             select_tech = ['d3js', 'javascript', 'tensorflow'],
             common_var = 'hn_all_match_score',
             after_date = '2010-01-01',
             var1 = 'so_usage_cnt',
             var2 = 'so_score_sum',
             var3 = 'so_answers',
             var4 = 'so_views')

hn_plots(data = data, freq = 'w',
         output_date = TODAY,
             select_tech = ['d3js', 'javascript', 'tensorflow'],
             common_var = 'hn_all_match_score',
             common_var3 = 'hn_all_match_cnt',
             common_var4 = 'hn_all_match_cnt',
             after_date = '2010-01-01',
             var1 = 'so_favorites',
             var2 = 'so_comments',
             var3 = 'so_favorites',
             var4 = 'so_comments')

hn_plots(data = data, freq = 'w',
         output_date = TODAY,
             select_tech = ['d3js', 'javascript', 'tensorflow'],
             common_var = 'hn_all_match_cnt',
             after_date = '2010-01-01',
             var1 = 'so_usage_cnt',
             var2 = 'so_score_sum',
             var3 = 'so_answers',
             var4 = 'so_views')

data.columns
data.loc[(data['tech'] == 'tensorflow') &
         ((data['hn_text_match_score'] > 0) | (data['so_views']>0))].date.min()

after_date = '2010-01-01'
max(pd.to_datetime(after_date),
                        data.loc[(data['tech'] == 'tensorflow') &
         ((data['hn_text_match_score'] > 0) |
                 (data['so_views']>0))].date.min()).date().strftime('%Y-%m-%d')
    
# Correlations
#corr_day = data.groupby('tech').corr().reset_index()
#corr_week = data_week.groupby('tech').corr().reset_index()
#data.columns
#data.sort_values(by = ['tech', 'date'], inplace = True)
#for i in (<columns>)
#data['diff_' + i] = data.groupby(['tech'])[i].transform(lambda x: x.diff())

'hn_all_match_cnt' == None

max(pd.to_datetime('2010-01-01'),
                        data.loc[(data['tech'] == 'd3js') &
         ((data['hn_all_match_score'] > 0) | (data['so_views']>0))].date.min()).strftime('%Y-%m-%d')