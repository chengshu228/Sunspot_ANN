
from numpy.core.fromnumeric import reshape
from numpy.lib import utils
import config
from utils import checkpoints, series_to_supervised, save_data, \
    colorsys, color, ncolors

import time
import numpy as np
import pandas as pd
import math
import matplotlib
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices('GPU')
tf.config.experimental.set_virtual_device_configuration(gpus[0],
    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4608),
    tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4608)])
from sklearn.preprocessing import MinMaxScaler
import julian
import datetime
from matplotlib.font_manager import FontProperties

blocks = config.blocks 
features = config.features
n_splits = config.n_splits
split_ratio = config.split_ratio
epochs = config.epochs
learning_rate = config.learning_rate
file_name = config.file_name
file_location = config.file_location

fontcn = config.fontcn
fontcn = FontProperties(fname=r"C:\WINDOWS\Fonts\simsun.ttc", size=14)

fonten = config.fonten
font = {'family':'serif', 'color':'darkred', 'weight':'normal', 'size':12}
colors = list(map(lambda output_data: color(tuple(output_data)), ncolors(blocks)))
markers = ['.', ',', '+', 'x', 'o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 
    'H', 'D', 'd', 'P', 'X', '1', '2', '3',]
lat_sep = config.lat_sep

start_time = time.time()

model = tf.keras.models.load_model(
    file_location+r'\model_lstm\{}.h5'.format(file_name))

sunspot = np.loadtxt(file_location+r'\RGO_NOAA1874_2021\sunspot_area_lat_one{}.txt'.\
    format(blocks), delimiter=' ')
print(sunspot.shape)
month = np.array(sunspot[:, 1], dtype=np.int)
day = np.array(sunspot[:, 2], dtype=np.int)
initial_julian = julian.to_jd(datetime.datetime(1870,1,1,0,0,0), fmt='jd')
end_julian = julian.to_jd(datetime.datetime(2030,1,1,0,0,0), fmt='jd')

jul_date = np.loadtxt(file_location+r'\RGO_NOAA1874_2021\sunspot_area_lat_jul_date_one{}.txt'.format(
    config.blocks), delimiter=' ')
jul_date = jul_date.reshape(-1, len(sunspot)).T

x_jul, x_tick_time = [], [] # 设置横轴标签
for x_tick in np.arange(1870, 2030+1, config.step): 
    t = datetime.datetime(x_tick,1,1,0,0,0)
    t_jd = julian.to_jd(t, fmt='jd')-initial_julian
    x_jul.append(t_jd)
    x_tick_time.append(x_tick)

input_data = np.array(sunspot[:,3:3+blocks*config.input_window*config.sun_epoch*12])
output_data = np.array(sunspot[:,3+blocks*config.input_window*config.sun_epoch*12:])
print('\n  input_data=', input_data.shape, 'output_data=', output_data.shape)

x_scaler = MinMaxScaler(feature_range=(0, 1))
input_data = x_scaler.fit_transform(input_data)
y_scaler = MinMaxScaler(feature_range=(0, 1)) 
output_data = y_scaler.fit_transform(output_data)

num1 = int(len(input_data) * split_ratio)
num2 = int(len(input_data) * (1-split_ratio)/2)
x_train, y_train = input_data[:num1, :], output_data[:num1, :]
x_val, y_val = input_data[num1:num1+num2, :], output_data[num1:num1+num2, :]
x_test, y_test = input_data[num1+num2:, :], output_data[num1+num2:, :]

x_train = np.expand_dims(x_train, axis=1)
x_val = np.expand_dims(x_val, axis=1)
x_test = np.expand_dims(x_test, axis=1)
print('\n\tshape: ', x_train.shape, y_train.shape,
    x_val.shape, y_val.shape, x_test.shape, y_test.shape)

y_train = y_scaler.inverse_transform(y_train)
y_train_pre = model.predict(x_train)
y_train_pre = y_scaler.inverse_transform(y_train_pre)
y_val = y_scaler.inverse_transform(y_val)
y_val_pre = model.predict(x_val)
y_val_pre = y_scaler.inverse_transform(y_val_pre)   
y_test = y_scaler.inverse_transform(y_test)
y_test_pre = model.predict(x_test)
y_test_pre = y_scaler.inverse_transform(y_test_pre)

y_train_diff = (y_train_pre-y_train).reshape(-1, blocks)
y_val_diff = (y_val_pre-y_val).reshape(-1, blocks)
y_test_diff = (y_test_pre-y_test).reshape(-1, blocks)
y_all_diff = np.concatenate((y_train_diff, y_val_diff, y_test_diff), axis=0)

y_all = np.concatenate((y_train, y_val, y_test), axis=0)
y_all_pre = np.concatenate((y_train_pre, y_val_pre, y_test_pre), axis=0)
y_train_val = np.concatenate((y_train, y_val), axis=0)
y_train_val_pre = np.concatenate((y_train_pre, y_val_pre), axis=0)

y_label = []
for key, value in enumerate(lat_sep):
    if key == 0 :
        y_label.append(r'({:.2f}S,90N]'.format(-lat_sep[1]))
    elif key == len(lat_sep)-1:
        y_label.append(r'[{:.2f}S, 90N]'.format(lat_sep[-1]))
    else:
        if value < 0:
            y_label.append(r'[{:.2f}S,{:.2f}S)'.format(-lat_sep[key+1], -lat_sep[key]))
        else:
            y_label.append(r'[{:.2f}N,{:.2f}N)'.format(lat_sep[key], lat_sep[key+1]))

y_lat = []
y_lat_all = np.empty(shape=(0, blocks))
for key, value in enumerate(lat_sep):
    y_lat.append(key-len(lat_sep)//2)

for key in np.arange(len(y_all)):
    y_lat_all = np.concatenate((y_lat_all, np.array(y_lat).reshape(1,-1)), axis=0)
# y_lat_all = np.repeat(y_lat_all, features, axis=1)

norm = matplotlib.colors.Normalize(vmin=0, vmax=100)

# for i in np.arange(blocks):
#     plt.figure(figsize=(6.5, 3.5))
#     plt.grid(True, linestyle='--', linewidth=1.0) 
#     plt.scatter(jul_date[:, 0], y_all[:,i], c='grey', 
#         marker='o', label='{}'.format('block'+str(i+1)+' observed')) 
#     plt.scatter(jul_date[:, 0], y_all_pre[:,i], c='dodgerblue', 
#         marker='*', label='{}'.format('block'+str(i+1)+' predicted'))  
#     plt.title(f'All Set', fontproperties='Arial', fontsize=20, color='red')
#     plt.xlabel('Date', fontproperties='Arial', fontsize=16)         
#     plt.ylabel('Sunspots Number', fontproperties='Arial', fontsize=16)  
#     plt.xticks(size=14)
#     plt.yticks(size=14)
#     plt.xticks(x_jul, x_tick_time, size=14, rotation=60)
#     plt.xlim(julian.to_jd(datetime.datetime(1870,1,1,0,0,0), fmt='jd')-initial_julian, 
#         julian.to_jd(datetime.datetime(2020,1,1,0,0,0), fmt='jd')-initial_julian)
#     plt.legend(prop=fonten, fontsize=9, ncol=1) 
#     ax = plt.gca()
#     ax.spines['bottom'].set_linewidth(1.5)
#     ax.spines['left'].set_linewidth(1.5)
#     ax.spines['top'].set_linewidth(1.5)
#     ax.spines['right'].set_linewidth(1.5)
#     plt.tight_layout()
#     plt.show()

fig = plt.figure(figsize=(16, 9.5))
plt.subplot(2,1,1)
plt.grid(True, axis='x', linestyle='--', linewidth=1.0) 
h1 = plt.scatter(jul_date[:num1,:].reshape(-1,), 
    y_lat_all[:num1,:].reshape(-1,), 
    c=y_train.reshape(-1,), marker='|', s=200, cmap='Wistia', norm=norm) 
plt.scatter(jul_date[num1:num1+num2,:].reshape(-1,), 
    y_lat_all[num1:num1+num2,:].reshape(-1,), 
    c=y_val.reshape(-1,), marker='|', s=200, cmap='Wistia', norm=norm) 
plt.scatter(jul_date[num1+num2:,:].reshape(-1,), 
    y_lat_all[num1+num2:,:].reshape(-1,), 
    c=y_test.reshape(-1,), marker='|', s=200, cmap='Wistia', norm=norm) 
plt.axvline(x=jul_date[num1,0], c="black", ls="--", lw=2)
plt.axvline(x=jul_date[num1+num2,0], c="black", ls="--", lw=2)
plt.colorbar(h1, extend='max')
plt.tight_layout()
plt.xlabel(u'日期', fontproperties=fontcn, fontsize=18)         
plt.ylabel(u'纬度', fontproperties=fontcn, fontsize=18)       
plt.xticks(x_jul, x_tick_time, size=14)
plt.yticks(y_lat, y_label, size=10)
plt.xlim(0, julian.to_jd(datetime.datetime(2030,1,1,0,0,0), fmt='jd')-initial_julian)
plt.ylim(-len(lat_sep)//2, len(lat_sep)//2+1)
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()
plt.subplot(2,1,2)
plt.grid(True, axis='x', linestyle='--', linewidth=1.0) 
h2 = plt.scatter(jul_date[:num1,:].reshape(-1,), 
    y_lat_all[:num1,:].reshape(-1,), 
    c=y_train_pre.reshape(-1,), marker='|', s=200, cmap='Wistia', norm=norm) 
plt.scatter(jul_date[num1:num1+num2,:].reshape(-1,), 
    y_lat_all[num1:num1+num2,:].reshape(-1,), 
    c=y_val_pre.reshape(-1,), marker='|', s=200, cmap='Wistia', norm=norm) 
plt.scatter(jul_date[num1+num2:,:].reshape(-1,), 
    y_lat_all[num1+num2:,:].reshape(-1,), 
    c=y_test_pre.reshape(-1,), marker='|', s=180, cmap='Wistia', norm=norm) 
plt.axvline(x=jul_date[num1,0], c="black", ls="--", lw=2)
plt.axvline(x=jul_date[num1+num2,0], c="black", ls="--", lw=2)
plt.colorbar(h2, extend='max')
plt.tight_layout()
plt.xlabel(u'日期', fontproperties=fontcn, fontsize=18)         
plt.ylabel(u'纬度', fontproperties=fontcn, fontsize=18)       
plt.xticks(x_jul, x_tick_time, size=14)
plt.yticks(y_lat, y_label, size=10)
plt.xlim(0, julian.to_jd(datetime.datetime(2030,1,1,0,0,0), fmt='jd')-initial_julian)
plt.ylim(-len(lat_sep)//2, len(lat_sep)//2+1)
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()
plt.show()

plt.figure(figsize=(10, 6))
plt.grid(True, linestyle='--', linewidth=1.0)
plt.plot(jul_date[:,0], np.sum(y_all, axis=1), color='grey', label=u'观测值')
plt.plot(jul_date[:len(y_train),0], np.sum(y_train_pre, axis=1),  
    color='dodgerblue', label=u'预测值 (训练集)')    
plt.plot(jul_date[len(y_train):len(y_train)+len(y_val),0], np.sum(y_val_pre, axis=1),  
    color='darkviolet', label=u'预测值 (验证集)') 
plt.plot(jul_date[-len(y_test):,0], np.sum(y_test_pre, axis=1),  
    color='indianred', label=u'预测值 (测试集)') 
plt.xlabel(u'日期', fontproperties=fontcn, fontsize=18)                
plt.ylabel(u'太阳黑子面积(纬度加总)', fontproperties=fontcn, fontsize=18)  
plt.xticks(x_jul, x_tick_time, size=14)
plt.yticks(size=14)
plt.xlim(0, end_julian-initial_julian)
plt.legend(loc='best', prop=fontcn, fontsize=16) 
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()
plt.show()

linestyles = [':', '-', '--']
labels = []
for i in np.arange(blocks):
    labels.append('block{}'.format(i+1))
colors = ['blueviolet', 'green', 'blue', 'goldenrod', 'cyan', 'grey']
markers = ['p', 'd', 'v', '^', 'x', 'o', '+', '<', '>', 's', '*', 'P']

fig = plt.figure(figsize=(6, 6))  
fig.add_subplot(1,1,1)
plt.grid(True, linestyle='--', linewidth=1.0)
plt.hist(y_test_diff.reshape(-1,), bins=11, range=(-10, 10), 
    color='dodgerblue', stacked=True)
plt.xlabel('Predicted - Observed', fontdict=fonten, fontsize=18)  
plt.ylabel('Frequency', fontdict=fonten, fontsize=18)  
plt.title(r'Absolute Error (Testing Set)', fontdict=fonten, fontsize=20) 
plt.xticks(size=14)
plt.yticks(size=14)
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()     
plt.savefig(r'.\figure\{}-Frequency-test.png'.format(file_name))
plt.show()



fig = plt.figure(figsize=(6, 6))   
plt.grid(True, linestyle='--', linewidth=1.0)
plt.scatter(y_train, y_train_pre, marker='o', c='dodgerblue', 
    label='Training Set', s=10)    
plt.scatter(y_val, y_val_pre, marker='s', c='darkviolet', 
    label='Validation Set', s=10)    
plt.scatter(y_test, y_test_pre, marker='*', c='indianred', 
    label='Testing Set', s=20) 
plt.plot(y_all, y_all, c='grey', linewidth=1.5)
plt.text(-2, -2, 'y=x', fontdict=fonten, fontsize=16)
plt.xlabel('Observed', fontproperties='Arial', fontsize=18)  
plt.ylabel('Predicted', fontproperties='Arial', fontsize=18)  
plt.xticks(size=14)
plt.yticks(size=14)
plt.legend(loc='best', prop=fonten, fontsize=15)
plt.title(r'All Set', fontdict=fonten, fontsize=20, color='red')
plt.tight_layout() 
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
ax.set_aspect(aspect='equal')
plt.savefig(r'.\figure\{}-PredictedObserved.png'.format(file_name))
plt.show()

fig = plt.figure(figsize=(10, 5))   
plt.subplot(1,1,1) 
plt.grid(True, linestyle='--', linewidth=1)
plt.scatter(jul_date[:len(y_train),:], y_train_diff, 
    label='Training Set', c='dodgerblue', marker='o', s=10)
plt.scatter(jul_date[len(y_train):len(y_train)+len(y_val),:], y_val_diff, 
    label='Validation Set', c='darkviolet', marker='o', s=10)
plt.scatter(jul_date[len(y_train_val):,:], y_test_diff, 
    label='Testing Set', c='indianred', marker='o', s=10)
plt.xlabel('Date', fontproperties='Arial', fontsize=18)  
plt.ylabel('Predicted - Observed', fontproperties='Arial', fontsize=18)  
plt.title(r'All Set', fontdict=fonten, fontsize=20, color='red')
plt.xticks(x_jul, x_tick_time, size=14)
plt.yticks(size=14)
plt.xlim(julian.to_jd(datetime.datetime(1870,1,1,0,0,0), fmt='jd')-initial_julian, 
    julian.to_jd(datetime.datetime(2020,1,1,0,0,0), fmt='jd')-initial_julian)
plt.legend(loc='best', prop=fonten, fontsize=15)
ax = plt.gca()
ax.spines['bottom'].set_linewidth(1.5)
ax.spines['left'].set_linewidth(1.5)
ax.spines['top'].set_linewidth(1.5)
ax.spines['right'].set_linewidth(1.5)
plt.tight_layout()
plt.savefig(r'.\figure\{}-DiffPredictedObserved.png'.format(file_name))
plt.show()
